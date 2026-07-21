"""由貼上／選取的內容產生「文章草稿」——純規則、不經 AI。

規則（依後台實際慣例）：
- 標題＝內容裡本來就夾帶的編號，正規化成「{西元年}年聖靈故事{編號}」（例：2026年聖靈故事120）。
- 內文（body_markdown）＝原文照登，但移除標題所在那一行（內文不重複出現標題）。
- 摘要（excerpt）＝內文開頭前幾句，供文章列表與桌面小工具當預覽。

過去用 Gemini 改寫的版本已移除：既不需金鑰、也不會有模型失效問題。
"""

from __future__ import annotations

import re
from datetime import datetime

# 標題（＋原始發佈日期）格式：例「2026年聖靈故事126(20260721) 正文…」。
# 年份可有可無（少數複製時只帶「聖靈故事N」），「年」「第」「0 前綴」都容忍；
# 編號後可選帶 (YYYYMMDD) 原始發佈日期（全形/半形括號皆可）。整段（標題＋日期）
# 會從內文移除，日期則轉成 orig_date 供發佈時間使用。
_HEADER_RE = re.compile(
    r"(?:(\d{4})\s*年?\s*)?聖靈故事\s*第?\s*0*(\d+)"
    r"\s*(?:[（(]\s*(\d{8})\s*[）)])?"
)

# 斷句用（句末標點）。
_SENT_END = "。！？!?"


class SummarizerError(Exception):
    pass


def format_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        content = (m.get("content") or f"[{m.get('msg_type', 'text')}]").replace("\n", " ").strip()
        lines.append(f"[{m.get('sent_at', '')}] {m.get('sender', '')}: {content}")
    return "\n".join(lines)


def _parse_header(text: str) -> tuple[str, str, re.Match | None]:
    """抓出標題與原始發佈日期；回傳 (title, orig_date, match)。找不到回傳 ("", "", None)。

    orig_date 為 ISO 字串（如 2026-07-21T00:00:00）；沒帶日期或日期無效時為 ""。
    """
    m = _HEADER_RE.search(text)
    if not m:
        return "", "", None
    year = m.group(1) or str(datetime.now().year)
    num = int(m.group(2))
    title = f"{year}年聖靈故事{num}"
    orig_date = ""
    if m.group(3):
        try:
            orig_date = datetime.strptime(m.group(3), "%Y%m%d").strftime("%Y-%m-%dT00:00:00")
        except ValueError:
            orig_date = ""  # 日期無效（如 20261332）就當作沒帶
    return title, orig_date, m


def _first_sentences(body: str, limit: int = 100) -> str:
    """取內文開頭前幾句（以句末標點斷句），總長約 limit 字，作為預覽摘要。"""
    text = re.sub(r"\s+", " ", (body or "")).strip()
    if not text:
        return ""
    out = ""
    for seg in re.split(rf"(?<=[{_SENT_END}])", text):
        seg = seg.strip()
        if not seg:
            continue
        if out and len(out) + 1 + len(seg) > limit:
            break
        out = f"{out} {seg}".strip() if out else seg
    if not out:  # 整段沒有句末標點
        out = text
    if len(out) > limit:
        out = out[:limit].rstrip() + "…"
    return out


def parse_story_post(text: str) -> dict:
    """把一段原文解析成 {title, body_markdown, excerpt, orig_date, tags}（純規則、不改寫內文）。"""
    text = (text or "").strip()
    if not text:
        raise SummarizerError("沒有可用來產生草稿的內容。")
    title, orig_date, m = _parse_header(text)
    # 只移除「標題＋日期」那一段（可能與正文同一行），其餘照原文；再清掉開頭殘留空白。
    body = (text[:m.start()] + text[m.end():]).strip() if m else text
    return {
        "title": title,            # 抓不到編號時為空字串，讓後台自行補標題
        "body_markdown": body,      # 原文照登，僅去掉標題與日期
        "excerpt": _first_sentences(body),
        "orig_date": orig_date,     # 供發佈時間；沒抓到日期為 ""（發佈時退回現在時間）
        "tags": [],
    }


def draft_article(messages: list[dict]) -> dict:
    """把選取的訊息產成文章草稿；內文＝訊息原文，標題取自內容夾帶的編號。"""
    if not messages:
        raise SummarizerError("沒有可用來產生草稿的訊息。")
    return parse_story_post(format_messages(messages))


def draft_from_text(text: str) -> dict:
    """把貼上的一段內容產成文章草稿；內文＝貼上的原文，標題取自內容夾帶的編號。

    供「複製貼上即產草稿」的捷徑使用（複製時會夾帶編號）。
    """
    return parse_story_post(text)
