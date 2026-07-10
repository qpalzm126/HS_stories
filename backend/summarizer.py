"""用 Anthropic Claude 把一段 LINE 對話改寫成「文章草稿」。

- tool（function calling）強制結構化輸出：title / excerpt / body_markdown / tags。
- map-reduce：內容多時先分段濃縮（保留敘事細節），再改寫成完整文章。
- 只有後台選取的訊息會送到 Anthropic API。
"""

from __future__ import annotations

import os

import anthropic

MAP_MODEL = os.environ.get("HS_DRAFT_MAP_MODEL", "claude-haiku-4-5-20251001")
DRAFT_MODEL = os.environ.get("HS_DRAFT_MODEL", "claude-opus-4-8")

CHUNK_CHARS = 12000


class SummarizerError(Exception):
    pass


_ARTICLE_TOOL = {
    "name": "record_article",
    "description": "把一段 LINE 對話改寫成一篇可公開閱讀的聖靈見證／故事文章。",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "文章標題，繁體中文，具體且吸引人。"},
            "excerpt": {"type": "string", "description": "1-2 句摘錄，供列表與桌面小工具顯示。"},
            "body_markdown": {
                "type": "string",
                "description": "文章全文，Markdown 格式，段落清楚、可加小標；忠實保留見證的真實細節。",
            },
            "tags": {"type": "array", "items": {"type": "string"}, "description": "主題標籤。"},
        },
        "required": ["title", "excerpt", "body_markdown"],
    },
}

_DRAFT_SYSTEM = (
    "你是編輯。請把使用者提供的 LINE 對話（或其分段摘要）裡的見證與分享，"
    "整理改寫成一篇適合公開閱讀的『聖靈故事』文章。"
    "務必忠於原意與真實細節、不杜撰未提及的事件；語氣溫暖得體，"
    "可適度分段、加小標，使閱讀順暢。用繁體中文，並呼叫 record_article 工具回傳。"
)

_MAP_SYSTEM = (
    "你是資料整理助理。用繁體中文濃縮以下 LINE 對話片段，"
    "盡量保留人名、時間、事件經過與見證細節（之後會用來寫成文章）。只輸出濃縮後的文字。"
)


def _client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SummarizerError("未設定 ANTHROPIC_API_KEY 環境變數，無法產生文章草稿。")
    return anthropic.Anthropic(api_key=key)


def format_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        content = (m.get("content") or f"[{m.get('msg_type', 'text')}]").replace("\n", " ").strip()
        lines.append(f"[{m.get('sent_at', '')}] {m.get('sender', '')}: {content}")
    return "\n".join(lines)


def _chunk(text: str, budget: int = CHUNK_CHARS) -> list[str]:
    chunks, cur, size = [], [], 0
    for ln in text.split("\n"):
        if size + len(ln) + 1 > budget and cur:
            chunks.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def _map_chunk(client, chunk: str) -> str:
    resp = client.messages.create(
        model=MAP_MODEL,
        max_tokens=1500,
        system=_MAP_SYSTEM,
        messages=[{"role": "user", "content": chunk}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _prepare_source(client, messages: list[dict]) -> str:
    text = format_messages(messages)
    if len(text) <= CHUNK_CHARS:
        return text
    parts = [_map_chunk(client, c) for c in _chunk(text)]
    return "以下是對話各段的濃縮：\n\n" + "\n\n".join(f"[片段 {i + 1}]\n{p}" for i, p in enumerate(parts))


def draft_article(messages: list[dict], instructions: str | None = None) -> dict:
    """把選取的訊息改寫成文章草稿，回傳 {title, excerpt, body_markdown, tags}。"""
    if not messages:
        raise SummarizerError("沒有可用來產生草稿的訊息。")
    client = _client()
    source = _prepare_source(client, messages)
    user = source
    if instructions:
        user = f"（編輯要求：{instructions}）\n\n{source}"

    resp = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=4096,
        system=_DRAFT_SYSTEM,
        tools=[_ARTICLE_TOOL],
        tool_choice={"type": "tool", "name": _ARTICLE_TOOL["name"]},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            data = block.input
            data.setdefault("tags", [])
            return data
    raise SummarizerError("模型未回傳文章草稿。")
