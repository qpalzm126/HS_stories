"""文章相關輔助：slug 產生、對外輸出整形。"""

from __future__ import annotations

import os
import re

from backend import db


def slugify(title: str) -> str:
    # Python re 的 \w 預設含 CJK 等 unicode 文字，故標點/空白轉為 '-'，中文與英數保留
    s = re.sub(r"[^\w]+", "-", (title or "").strip(), flags=re.UNICODE)
    s = s.strip("-").lower()
    return s[:80] or "story"


def unique_slug(title: str) -> str:
    base = slugify(title)
    slug = base
    i = 2
    while db.slug_exists(slug):
        slug = f"{base}-{i}"
        i += 1
    return slug


def _base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")


def _preview_from_body(body: str | None, limit: int = 100) -> str:
    """從 Markdown 內文截一段純文字，作為列表預覽（excerpt 未填時的備援）。"""
    if not body:
        return ""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)          # 圖片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # 連結→留文字
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)  # 標題符號
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.M)   # 清單符號
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.M)       # 引言符號
    text = text.replace("*", "").replace("`", "").replace("_", "")
    text = re.sub(r"\s+", " ", text).strip()                   # 收合空白/換行
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def public_article(row: dict, full: bool = False) -> dict:
    """整理成對外（公開 API / widget）用的欄位。"""
    slug = row.get("slug")
    # excerpt 優先用人工摘錄；沒填就用內文開頭當預覽（app/web/widget 共用）。
    excerpt = (row.get("excerpt") or "").strip()
    if not excerpt:
        excerpt = _preview_from_body(row.get("body"))
    out = {
        "slug": slug,
        "title": row.get("title"),
        "excerpt": excerpt or None,
        "cover_url": row.get("cover_url"),
        "published_at": row.get("published_at"),
        "url": f"{_base_url()}/article/{slug}" if slug else None,
    }
    if full:
        out["body"] = row.get("body")
        out["tags"] = row.get("tags")
    return out
