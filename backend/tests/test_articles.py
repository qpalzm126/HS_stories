import pytest

from backend import articles, db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_slugify_handles_chinese_and_punctuation():
    assert articles.slugify("神的恩典 太奇妙了！") == "神的恩典-太奇妙了"
    assert articles.slugify("   ") == "story"


def test_unique_slug_increments(tmp_db):
    db.create_article(slug="恩典", title="恩典")
    assert articles.unique_slug("恩典") == "恩典-2"


def test_create_update_publish_latest(tmp_db):
    aid = db.create_article(slug="a", title="第一篇", body="內容", excerpt="摘要")
    assert db.get_article_by_id(aid)["status"] == "draft"
    # 草稿不應出現在公開列表 / latest
    assert db.get_latest_article() is None
    assert db.list_articles(published_only=True) == []

    db.update_article(aid, title="第一篇（改）")
    assert db.get_article_by_id(aid)["title"] == "第一篇（改）"

    db.publish_article(aid)
    latest = db.get_latest_article()
    assert latest and latest["id"] == aid
    assert latest["published_at"]

    # 公開 by slug 只回已發佈
    assert db.get_article_by_slug("a", published_only=True)["id"] == aid


def test_latest_is_most_recent_published(tmp_db):
    a1 = db.create_article(slug="a1", title="一")
    a2 = db.create_article(slug="a2", title="二")
    db.publish_article(a1)
    db.publish_article(a2)
    assert db.get_latest_article()["id"] == a2


def test_public_article_shape(tmp_db, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.org")
    aid = db.create_article(slug="hello", title="標題", excerpt="摘要", body="全文")
    db.publish_article(aid)
    row = db.get_article_by_id(aid)
    pub = articles.public_article(row, full=True)
    assert pub["url"] == "https://example.org/article/hello"
    assert pub["body"] == "全文"
    # 列表形式不含 body
    assert "body" not in articles.public_article(row)
