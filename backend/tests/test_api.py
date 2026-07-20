from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend import db, summarizer

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.txt"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "api.db")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("SECRET_KEY", "sk")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.org")
    with TestClient(app_module.app) as c:
        yield c


def _auth(client):
    r = client.post("/api/admin/login", json={"password": "pw"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_wrong_password(client):
    assert client.post("/api/admin/login", json={"password": "nope"}).status_code == 401


def test_admin_requires_token(client):
    assert client.get("/api/admin/articles").status_code == 401
    assert client.get("/api/admin/articles", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_publish_uses_orig_date_from_source_ref(client):
    import json as _json
    h = _auth(client)
    # 匯入文章：source_ref 帶原始日期 → 發佈時 published_at 應採用它（時間軸貼合原文）
    a = client.post(
        "/api/admin/articles",
        json={"title": "2023年聖靈故事54", "body": "x",
              "source_ref": _json.dumps({"msg_id": 1, "orig_date": "2023-12-08T15:35:00"})},
        headers=h,
    ).json()
    r = client.post(f"/api/admin/articles/{a['id']}/publish", headers=h).json()
    assert r["published_at"] == "2023-12-08T15:35:00"

    # 明確指定 published_at 時，以指定值為準
    b = client.post("/api/admin/articles", json={"title": "手動", "body": "y"}, headers=h).json()
    r = client.post(
        f"/api/admin/articles/{b['id']}/publish",
        json={"published_at": "2020-01-01T00:00:00"}, headers=h,
    ).json()
    assert r["published_at"] == "2020-01-01T00:00:00"


def test_admin_articles_search_and_pagination(client):
    h = _auth(client)
    for i in range(25):
        title = f"聖靈故事{i}" if i < 3 else f"雜項{i}"
        r = client.post("/api/admin/articles", json={"title": title, "body": "x"}, headers=h)
        if i == 0:
            client.post(f"/api/admin/articles/{r.json()['id']}/publish", headers=h)

    def g(**p):
        return client.get("/api/admin/articles", params=p, headers=h).json()

    # 分頁：回傳 {total, items}，預設每頁 20
    d = g()
    assert d["total"] == 25 and len(d["items"]) == 20
    assert len(g(offset=20)["items"]) == 5
    # 搜尋標題
    assert g(q="聖靈")["total"] == 3
    # 狀態篩選
    assert g(status="published")["total"] == 1
    assert g(status="draft")["total"] == 24
    # 搜尋 + 狀態
    assert g(q="聖靈", status="draft")["total"] == 2


def test_full_publish_flow(client, monkeypatch):
    h = _auth(client)

    # 1. 匯入 LINE
    files = {"file": ("sample_export.txt", FIXTURE.read_bytes(), "text/plain")}
    r = client.post("/api/admin/import", files=files, headers=h)
    assert r.status_code == 200 and r.json()["added"] == 12

    # 2. 搜尋訊息
    r = client.get("/api/admin/messages", params={"q": "會議記錄"}, headers=h)
    assert r.status_code == 200 and r.json()["count"] >= 1

    # 3. 產草稿（mock 掉 Gemini）
    monkeypatch.setattr(
        summarizer,
        "draft_article",
        lambda msgs, instructions=None: {
            "title": "測試文章",
            "excerpt": "一句摘要",
            "body_markdown": "# 內文\n\n段落",
            "tags": ["見證"],
        },
    )
    r = client.post("/api/admin/draft", json={"conversation": "Alice"}, headers=h)
    assert r.status_code == 200
    draft = r.json()["draft"]
    assert draft["title"] == "測試文章"

    # 4. 儲存為文章（草稿）
    r = client.post(
        "/api/admin/articles",
        json={"title": draft["title"], "body": draft["body_markdown"], "excerpt": draft["excerpt"]},
        headers=h,
    )
    assert r.status_code == 200
    art = r.json()
    aid, slug = art["id"], art["slug"]
    assert art["status"] == "draft"

    # 5. 尚未發佈 → 公開 API 看不到
    assert client.get("/api/articles/latest").status_code == 404
    assert client.get(f"/api/articles/{slug}").status_code == 404

    # 6. 發佈
    r = client.post(f"/api/admin/articles/{aid}/publish", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "published"

    # 7. 公開 API：latest / by-slug / list
    r = client.get("/api/articles/latest")
    assert r.status_code == 200
    j = r.json()
    assert j["title"] == "測試文章"
    assert j["url"] == f"https://example.org/article/{slug}"

    r = client.get(f"/api/articles/{slug}")
    assert r.status_code == 200 and r.json()["body"] == "# 內文\n\n段落"

    r = client.get("/api/articles")
    assert r.status_code == 200 and len(r.json()) == 1


def test_draft_without_api_key_returns_503(client, monkeypatch):
    h = _auth(client)
    files = {"file": ("sample_export.txt", FIXTURE.read_bytes(), "text/plain")}
    client.post("/api/admin/import", files=files, headers=h)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    r = client.post("/api/admin/draft", json={"conversation": "Alice"}, headers=h)
    assert r.status_code == 503


def test_draft_no_messages_returns_404(client):
    h = _auth(client)
    r = client.post("/api/admin/draft", json={"conversation": "不存在"}, headers=h)
    assert r.status_code == 404


def test_draft_from_text_returns_draft(client, monkeypatch):
    """複製貼上捷徑：貼一段文字直接產草稿（mock 掉 Gemini），不需匯入。"""
    h = _auth(client)
    monkeypatch.setattr(
        summarizer,
        "draft_from_text",
        lambda text, instructions=None: {
            "title": "貼上產生的文章",
            "excerpt": "摘要",
            "body_markdown": "# 內文",
            "tags": [],
        },
    )
    r = client.post(
        "/api/admin/draft-from-text",
        json={"text": "15:20\tAlice\t今天很感恩，分享一個見證"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["draft"]["title"] == "貼上產生的文章"


def test_draft_from_text_requires_token(client):
    r = client.post("/api/admin/draft-from-text", json={"text": "x"})
    assert r.status_code == 401


def test_draft_from_text_empty_returns_400(client):
    h = _auth(client)
    r = client.post("/api/admin/draft-from-text", json={"text": "   "}, headers=h)
    assert r.status_code == 400
