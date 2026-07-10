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


def public_article(row: dict, full: bool = False) -> dict:
    """整理成對外（公開 API / widget）用的欄位。"""
    slug = row.get("slug")
    out = {
        "slug": slug,
        "title": row.get("title"),
        "excerpt": row.get("excerpt"),
        "cover_url": row.get("cover_url"),
        "published_at": row.get("published_at"),
        "url": f"{_base_url()}/article/{slug}" if slug else None,
    }
    if full:
        out["body"] = row.get("body")
        out["tags"] = row.get("tags")
    return out
