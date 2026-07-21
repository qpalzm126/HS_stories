"""SQLite 儲存層：
- messages + FTS5(trigram)：後台從 LINE 匯入的訊息，供搜尋挑選內容（沿用自 LINE 工具）。
- articles：發佈用的文章（草稿 / 已發佈）。

優先使用 pysqlite3（若安裝），否則標準函式庫 sqlite3；啟動時偵測 FTS5 trigram，
不支援時搜尋自動退回 LIKE。
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    import pysqlite3 as sqlite3  # type: ignore
except ImportError:
    import sqlite3  # type: ignore


DB_PATH = Path(os.environ.get("HS_DB_PATH", Path(__file__).parent / "data" / "hs.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_fts_trigram() -> bool:
    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE _probe USING fts5(x, tokenize='trigram')")
        con.close()
        return True
    except Exception:
        return False


FTS_ENABLED = _detect_fts_trigram()


def get_conn() -> "sqlite3.Connection":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


@contextmanager
def connection():
    con = get_conn()
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ---- Schema -------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation TEXT NOT NULL,
    sent_at      TEXT,
    sender       TEXT,
    content      TEXT,
    msg_type     TEXT,
    source_file  TEXT,
    content_hash TEXT NOT NULL,
    UNIQUE(conversation, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation);
CREATE INDEX IF NOT EXISTS idx_messages_sent ON messages(sent_at);

CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    slug         TEXT UNIQUE,
    title        TEXT NOT NULL,
    body         TEXT,
    excerpt      TEXT,
    cover_url    TEXT,
    status       TEXT DEFAULT 'draft',   -- draft / published
    source_ref   TEXT,
    created_at   TEXT,
    updated_at   TEXT,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, sender, conversation,
    content='messages', content_rowid='id',
    tokenize='trigram'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, sender, conversation)
    VALUES (new.id, new.content, new.sender, new.conversation);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, sender, conversation)
    VALUES ('delete', old.id, old.content, old.sender, old.conversation);
END;
CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, sender, conversation)
    VALUES ('delete', old.id, old.content, old.sender, old.conversation);
    INSERT INTO messages_fts(rowid, content, sender, conversation)
    VALUES (new.id, new.content, new.sender, new.conversation);
END;
"""


def init_db() -> None:
    with connection() as con:
        con.executescript(_SCHEMA)
        if FTS_ENABLED:
            con.executescript(_FTS_SCHEMA)


# ---- messages：寫入與查詢（供後台挑內容）-------------------------------------


def insert_messages(con: "sqlite3.Connection", rows: list[dict]) -> tuple[int, int]:
    before = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    con.executemany(
        """INSERT OR IGNORE INTO messages
               (conversation, sent_at, sender, content, msg_type, source_file, content_hash)
           VALUES (:conversation, :sent_at, :sender, :content, :msg_type, :source_file, :content_hash)""",
        rows,
    )
    after = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    added = after - before
    return added, len(rows) - added


def _fts_usable(q: str | None) -> bool:
    return bool(q) and FTS_ENABLED and len(q.strip()) >= 3


def _build_filters(conversation, sender, date_from, date_to):
    clauses, params = [], {}
    if conversation:
        clauses.append("m.conversation = :conversation")
        params["conversation"] = conversation
    if sender:
        clauses.append("m.sender = :sender")
        params["sender"] = sender
    if date_from:
        clauses.append("m.sent_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("m.sent_at <= :date_to")
        params["date_to"] = date_to
    return clauses, params


def _msg_row(r) -> dict:
    return {
        "id": r["id"],
        "conversation": r["conversation"],
        "sent_at": r["sent_at"],
        "sender": r["sender"],
        "content": r["content"],
        "msg_type": r["msg_type"],
    }


def query_messages(
    q=None, conversation=None, sender=None, date_from=None, date_to=None, limit=200, offset=0
) -> list[dict]:
    clauses, params = _build_filters(conversation, sender, date_from, date_to)
    params["limit"] = limit
    params["offset"] = offset
    with connection() as con:
        if _fts_usable(q):
            params["q"] = '"' + q.strip().replace('"', '""') + '"'
            where = " AND ".join(["messages_fts MATCH :q"] + clauses)
            sql = f"""
                SELECT m.id, m.conversation, m.sent_at, m.sender, m.content, m.msg_type
                FROM messages_fts JOIN messages m ON m.id = messages_fts.rowid
                WHERE {where} ORDER BY m.sent_at LIMIT :limit OFFSET :offset
            """
        else:
            if q:
                clauses.append("m.content LIKE :like")
                params["like"] = f"%{q.strip()}%"
            where = " AND ".join(clauses) if clauses else "1=1"
            sql = f"""
                SELECT m.id, m.conversation, m.sent_at, m.sender, m.content, m.msg_type
                FROM messages m WHERE {where} ORDER BY m.sent_at LIMIT :limit OFFSET :offset
            """
        return [_msg_row(r) for r in con.execute(sql, params)]


def get_messages_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with connection() as con:
        rows = con.execute(
            f"SELECT id, conversation, sent_at, sender, content, msg_type "
            f"FROM messages WHERE id IN ({placeholders}) ORDER BY sent_at",
            ids,
        )
        return [_msg_row(r) for r in rows]


def list_conversations() -> list[dict]:
    with connection() as con:
        rows = con.execute(
            """SELECT conversation, COUNT(*) AS count,
                      MIN(sent_at) AS first_at, MAX(sent_at) AS last_at
               FROM messages GROUP BY conversation ORDER BY count DESC"""
        )
        return [dict(r) for r in rows]


def list_senders(conversation: str | None = None) -> list[str]:
    with connection() as con:
        if conversation:
            rows = con.execute(
                "SELECT DISTINCT sender FROM messages WHERE conversation = ? ORDER BY sender",
                (conversation,),
            )
        else:
            rows = con.execute("SELECT DISTINCT sender FROM messages ORDER BY sender")
        return [r["sender"] for r in rows if r["sender"]]


# ---- articles：文章 CRUD / 發佈 / 查詢 ----------------------------------------

_ARTICLE_COLS = ("slug", "title", "body", "excerpt", "cover_url", "status", "source_ref")


def _article_row(r) -> dict | None:
    return dict(r) if r else None


def slug_exists(slug: str) -> bool:
    with connection() as con:
        return con.execute("SELECT 1 FROM articles WHERE slug = ?", (slug,)).fetchone() is not None


def create_article(
    slug, title, body="", excerpt="", cover_url="", source_ref="", status="draft"
) -> int:
    with connection() as con:
        cur = con.execute(
            """INSERT INTO articles
                   (slug, title, body, excerpt, cover_url, status, source_ref, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, title, body, excerpt, cover_url, status, source_ref, _now(), _now()),
        )
        return cur.lastrowid


def update_article(article_id: int, **fields) -> None:
    cols = [k for k in fields if k in _ARTICLE_COLS]
    if not cols:
        return
    sets = ", ".join(f"{c} = :{c}" for c in cols) + ", updated_at = :updated_at"
    params = {c: fields[c] for c in cols}
    params["updated_at"] = _now()
    params["id"] = article_id
    with connection() as con:
        con.execute(f"UPDATE articles SET {sets} WHERE id = :id", params)


def publish_article(article_id: int, published_at: str | None = None) -> None:
    """發佈文章並決定 published_at（決定公開站的排序與顯示日期），優先序：
    1) 明確傳入的 published_at；2) 該文已有的 published_at；
    3) source_ref 內的 orig_date（匯入文章的原始日期，讓時間軸貼合原文）；4) 現在時間。"""
    with connection() as con:
        row = con.execute(
            "SELECT published_at, source_ref FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        pub = published_at or (row["published_at"] if row and row["published_at"] else None)
        if not pub and row and row["source_ref"]:
            try:
                pub = (json.loads(row["source_ref"]) or {}).get("orig_date")
            except (ValueError, TypeError):
                pass
        pub = pub or _now()
        con.execute(
            "UPDATE articles SET status='published', published_at=?, updated_at=? WHERE id=?",
            (pub, _now(), article_id),
        )


def unpublish_article(article_id: int) -> None:
    with connection() as con:
        con.execute(
            "UPDATE articles SET status='draft', updated_at=? WHERE id=?", (_now(), article_id)
        )


def delete_article(article_id: int) -> None:
    with connection() as con:
        con.execute("DELETE FROM articles WHERE id = ?", (article_id,))


def get_article_by_id(article_id: int) -> dict | None:
    with connection() as con:
        return _article_row(con.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone())


def get_article_by_slug(slug: str, published_only: bool = True) -> dict | None:
    sql = "SELECT * FROM articles WHERE slug = ?"
    if published_only:
        sql += " AND status = 'published'"
    with connection() as con:
        return _article_row(con.execute(sql, (slug,)).fetchone())


def get_latest_article() -> dict | None:
    with connection() as con:
        return _article_row(
            con.execute(
                "SELECT * FROM articles WHERE status='published' "
                "ORDER BY published_at DESC LIMIT 1"
            ).fetchone()
        )


def list_articles(published_only: bool = True, limit: int = 50, offset: int = 0,
                  q: str | None = None) -> list[dict]:
    clauses, params = [], {}
    if published_only:
        clauses.append("status = 'published'")
    if q and q.strip():                       # 關鍵字：標題或內文含關鍵字
        clauses.append("(title LIKE :q OR body LIKE :q)")
        params["q"] = f"%{q.strip()}%"
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    order = "published_at DESC" if published_only else "COALESCE(updated_at, created_at) DESC"
    params["limit"], params["offset"] = limit, offset
    sql = f"SELECT * FROM articles{where} ORDER BY {order} LIMIT :limit OFFSET :offset"
    with connection() as con:
        return [dict(r) for r in con.execute(sql, params)]


def _admin_article_where(q: str | None, status: str | None):
    """後台文章清單的篩選條件：status（draft/published）+ q（標題模糊比對）。"""
    clauses, params = [], {}
    if status in ("draft", "published"):
        clauses.append("status = :status")
        params["status"] = status
    if q and q.strip():
        clauses.append("title LIKE :q")
        params["q"] = f"%{q.strip()}%"
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# 後台列表可選排序（白名單，避免 SQL 注入）；發佈時間排序時把未發佈（NULL）排最後。
_ADMIN_SORTS = {
    "updated_desc": "COALESCE(updated_at, created_at) DESC",
    "published_desc": "published_at IS NULL, published_at DESC",
    "published_asc": "published_at IS NULL, published_at ASC",
}
DEFAULT_ADMIN_SORT = "updated_desc"


def list_articles_admin(q=None, status=None, limit=20, offset=0, sort=None) -> list[dict]:
    where, params = _admin_article_where(q, status)
    params["limit"], params["offset"] = limit, offset
    order = _ADMIN_SORTS.get(sort or DEFAULT_ADMIN_SORT, _ADMIN_SORTS[DEFAULT_ADMIN_SORT])
    sql = f"SELECT * FROM articles{where} ORDER BY {order} LIMIT :limit OFFSET :offset"
    with connection() as con:
        return [dict(r) for r in con.execute(sql, params)]


def count_articles_admin(q=None, status=None) -> int:
    where, params = _admin_article_where(q, status)
    with connection() as con:
        return con.execute(f"SELECT COUNT(*) FROM articles{where}", params).fetchone()[0]
