"""匯入 LINE 匯出檔到資料庫，支援去重與增量匯入。

去重鍵為 (conversation, content_hash)，content_hash = sha256(sent_at | sender | content)。
因此重覆匯入同一檔、或未來重新匯出同一對話（含新訊息）時，舊訊息會被略過，
只寫入新的部分。
"""

from __future__ import annotations

import hashlib

from backend import db
from backend.parser import parse_export


def content_hash(sent_at: str | None, sender: str | None, content: str | None) -> str:
    h = hashlib.sha256()
    h.update((sent_at or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((sender or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((content or "").encode("utf-8"))
    return h.hexdigest()


def decode_bytes(raw: bytes) -> str:
    """LINE 匯出檔通常是 UTF-8（可能含 BOM）；舊檔可能是 Big5，逐一嘗試。"""
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def import_text(text: str, source_file: str, default_conversation: str | None = None) -> dict:
    export = parse_export(text, default_conversation=default_conversation)
    rows = [
        {
            "conversation": export.conversation,
            "sent_at": m.sent_at,
            "sender": m.sender,
            "content": m.content,
            "msg_type": m.msg_type,
            "source_file": source_file,
            "content_hash": content_hash(m.sent_at, m.sender, m.content),
        }
        for m in export.messages
    ]
    added, skipped = 0, 0
    if rows:
        with db.connection() as con:
            added, skipped = db.insert_messages(con, rows)
    return {
        "conversation": export.conversation,
        "added": added,
        "skipped": skipped,
        "total": len(rows),
    }


def import_bytes(raw: bytes, source_file: str, default_conversation: str | None = None) -> dict:
    return import_text(decode_bytes(raw), source_file, default_conversation)
