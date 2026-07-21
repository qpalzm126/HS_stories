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


def test_admin_list_sort_by_published(client):
    """後台列表可依發佈時間排序（未發佈排最後）。"""
    h = _auth(client)
    made = {}
    for title, date in [("甲", "2024-01-01T00:00:00"), ("乙", "2026-06-01T00:00:00"), ("丙", "2025-03-01T00:00:00")]:
        a = client.post("/api/admin/articles", json={"title": title, "body": "x"}, headers=h).json()
        client.post(f"/api/admin/articles/{a['id']}/publish", json={"published_at": date}, headers=h)
        made[title] = a["id"]
    # 一篇草稿（未發佈）
    client.post("/api/admin/articles", json={"title": "丁草稿", "body": "x"}, headers=h)

    def titles(sort):
        d = client.get("/api/admin/articles", params={"sort": sort}, headers=h).json()
        return [it["title"] for it in d["items"]]

    asc = titles("published_asc")
    assert asc[:3] == ["甲", "丙", "乙"]  # 舊→新
    assert asc[-1] == "丁草稿"            # 未發佈排最後
    assert titles("published_desc")[:3] == ["乙", "丙", "甲"]  # 新→舊


def test_can_change_publish_time_of_published_article(client):
    """已發佈文章可再帶新的 published_at 覆蓋（後台『更新發佈時間』）。"""
    h = _auth(client)
    a = client.post("/api/admin/articles", json={"title": "改時間", "body": "x"}, headers=h).json()
    # 先發佈（無指定 → 現在時間）
    p1 = client.post(f"/api/admin/articles/{a['id']}/publish", headers=h).json()
    assert p1["status"] == "published"
    # 已發佈狀態下，再帶明確時間 → 覆蓋
    p2 = client.post(
        f"/api/admin/articles/{a['id']}/publish",
        json={"published_at": "2025-05-05T09:00:00"}, headers=h,
    ).json()
    assert p2["status"] == "published"
    assert p2["published_at"] == "2025-05-05T09:00:00"


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

    # 3. 產草稿（mock 掉解析，聚焦發佈流程）
    monkeypatch.setattr(
        summarizer,
        "draft_article",
        lambda msgs: {
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


def test_draft_no_messages_returns_404(client):
    h = _auth(client)
    r = client.post("/api/admin/draft", json={"conversation": "不存在"}, headers=h)
    assert r.status_code == 404


def test_draft_from_text_parses_title_body_excerpt(client):
    """複製貼上捷徑（純規則）：標題取自夾帶編號、日期轉 orig_date、內文去掉標題與日期。"""
    h = _auth(client)
    text = "2026年聖靈故事126(20260721) 大家辛苦了。 今天要分享一個見證，願榮耀歸於神。"
    r = client.post("/api/admin/draft-from-text", json={"text": text}, headers=h)
    assert r.status_code == 200
    d = r.json()["draft"]
    assert d["title"] == "2026年聖靈故事126"
    assert d["orig_date"] == "2026-07-21T00:00:00"
    assert "聖靈故事" not in d["body_markdown"] and "20260721" not in d["body_markdown"]
    assert d["body_markdown"].startswith("大家辛苦了。")
    assert d["excerpt"].startswith("大家辛苦了。")


def test_paste_publish_uses_orig_date_from_content(client):
    """整條鏈路：貼上帶日期的內容 → 存成文章（source_ref 帶 orig_date）→ 發佈時間貼合原文。"""
    import json as _json
    h = _auth(client)
    text = "2026年聖靈故事126(20260721) 大家辛苦了。今天分享見證。"
    d = client.post("/api/admin/draft-from-text", json={"text": text}, headers=h).json()["draft"]
    a = client.post(
        "/api/admin/articles",
        json={"title": d["title"], "body": d["body_markdown"], "excerpt": d["excerpt"],
              "source_ref": _json.dumps({"orig_date": d["orig_date"], "from": "paste"})},
        headers=h,
    ).json()
    r = client.post(f"/api/admin/articles/{a['id']}/publish", headers=h).json()
    assert r["published_at"] == "2026-07-21T00:00:00"


def test_draft_from_text_requires_token(client):
    r = client.post("/api/admin/draft-from-text", json={"text": "x"})
    assert r.status_code == 401


def test_draft_from_text_empty_returns_400(client):
    h = _auth(client)
    r = client.post("/api/admin/draft-from-text", json={"text": "   "}, headers=h)
    assert r.status_code == 400


# ---- summarizer 純規則解析 -----------------------------------------------------


def test_parse_extracts_title_date_and_inline_body():
    # 標題、日期、正文同一行：只移除「標題＋日期」，正文保留
    d = summarizer.parse_story_post("2026年聖靈故事7(20260315) 正文第一句。第二句。")
    assert d["title"] == "2026年聖靈故事7"
    assert d["orig_date"] == "2026-03-15T00:00:00"
    assert d["body_markdown"] == "正文第一句。第二句。"


def test_parse_pads_are_stripped_and_year_optional():
    # 補零去掉、缺年份時用當年、沒帶日期則 orig_date 為空
    d = summarizer.parse_story_post("聖靈故事 第08\n內容。")
    assert d["title"].endswith("年聖靈故事8")
    assert d["orig_date"] == ""
    assert d["body_markdown"] == "內容。"


def test_parse_without_number_leaves_title_empty():
    d = summarizer.parse_story_post("這段沒有編號，只有內容。第二句。")
    assert d["title"] == ""
    assert d["orig_date"] == ""
    assert d["body_markdown"] == "這段沒有編號，只有內容。第二句。"


def test_parse_invalid_date_ignored():
    d = summarizer.parse_story_post("2026年聖靈故事9(20261340) 內容。")
    assert d["title"] == "2026年聖靈故事9"
    assert d["orig_date"] == ""  # 無效日期不採用
    assert d["body_markdown"] == "內容。"


def test_parse_excerpt_takes_first_sentences():
    body = "。".join([f"第{i}句" for i in range(1, 40)]) + "。"
    d = summarizer.parse_story_post("2026年聖靈故事1\n" + body)
    assert d["excerpt"].startswith("第1句。 第2句。")  # 句子間以空白相接
    assert len(d["excerpt"]) <= 101  # 約 100 字上限（含結尾…）
