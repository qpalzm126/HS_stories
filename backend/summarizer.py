"""用 Google Gemini 把一段 LINE 對話改寫成「文章草稿」。

- 結構化 JSON 輸出（response_schema）強制回傳：title / excerpt / body_markdown / tags。
- map-reduce：內容多時先分段濃縮（保留敘事細節），再改寫成完整文章。
- 只有後台選取的訊息會送到 Gemini API。
- 需環境變數 GEMINI_API_KEY（Google AI Studio 免費金鑰；也接受 GOOGLE_API_KEY）。
"""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel

# 預設用 Gemini 2.5 Flash（免費額度內，對這類改寫綽綽有餘）；可用環境變數覆寫。
MAP_MODEL = os.environ.get("HS_DRAFT_MAP_MODEL", "gemini-2.5-flash")
DRAFT_MODEL = os.environ.get("HS_DRAFT_MODEL", "gemini-2.5-flash")

CHUNK_CHARS = 12000

# 列出可用 model 時，排除非「文字改寫」用途者（語音、影像、機器人等），只留 Gemini/Gemma 對話模型。
_MODEL_EXCLUDE = (
    "tts", "image", "audio", "embedding", "robotics", "computer-use",
    "lyria", "nano-banana", "deep-research", "antigravity", "omni", "aqa", "vision",
)


class SummarizerError(Exception):
    pass


class ArticleDraft(BaseModel):
    """草稿結構；作為 Gemini 的 response_schema，保證欄位齊全。"""

    title: str
    excerpt: str
    body_markdown: str
    tags: list[str] = []


_DRAFT_SYSTEM = (
    "你是編輯。請把使用者提供的 LINE 對話（或其分段摘要）裡的見證與分享，"
    "整理改寫成一篇適合公開閱讀的『聖靈故事』文章。"
    "務必忠於原意與真實細節、不杜撰未提及的事件；語氣溫暖得體，"
    "可適度分段、加小標，使閱讀順暢。用繁體中文。"
    "title=具體吸引人的標題；excerpt=1-2 句摘錄（供列表與桌面小工具）；"
    "body_markdown=文章全文（Markdown，段落清楚、可加小標）；tags=主題標籤。"
)

_MAP_SYSTEM = (
    "你是資料整理助理。用繁體中文濃縮以下 LINE 對話片段，"
    "盡量保留人名、時間、事件經過與見證細節（之後會用來寫成文章）。只輸出濃縮後的文字。"
)


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SummarizerError("未設定 GEMINI_API_KEY 環境變數，無法產生文章草稿。")
    return genai.Client(api_key=key)


def _is_text_model(short_name: str) -> bool:
    n = short_name.lower()
    if not (n.startswith("gemini") or n.startswith("gemma")):
        return False
    return not any(bad in n for bad in _MODEL_EXCLUDE)


def list_generate_models() -> dict:
    """向 Gemini API 即時查詢目前可用、且支援 generateContent 的文字模型清單。

    回傳 {"models": [{"name", "label"}...], "default": DRAFT_MODEL}。
    供後台在產生草稿前更新「可選 model」用（模型會隨時間新增/淘汰）。
    """
    client = _client()
    try:
        raw = list(client.models.list())
    except Exception as e:  # 網路 / 金鑰 / 配額等
        raise SummarizerError(f"取得可用模型清單失敗：{e}")

    models = []
    for m in raw:
        if "generateContent" not in (m.supported_actions or []):
            continue
        short = (m.name or "").rsplit("/", 1)[-1]
        if not short or not _is_text_model(short):
            continue
        models.append({"name": short, "label": m.display_name or short})
    return {"models": models, "default": DRAFT_MODEL}


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


def _map_chunk(client: genai.Client, chunk: str, model: str) -> str:
    resp = client.models.generate_content(
        model=model,
        contents=chunk,
        config=types.GenerateContentConfig(
            system_instruction=_MAP_SYSTEM,
            temperature=0.3,
            max_output_tokens=2000,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return (resp.text or "").strip()


def _condense(client: genai.Client, text: str, model: str) -> str:
    """把來源文字整理成適合改寫的來源：短則原樣、長則分段濃縮（map-reduce）。"""
    if len(text) <= CHUNK_CHARS:
        return text
    parts = [_map_chunk(client, c, model) for c in _chunk(text)]
    return "以下是對話各段的濃縮：\n\n" + "\n\n".join(f"[片段 {i + 1}]\n{p}" for i, p in enumerate(parts))


def _generate_draft(client: genai.Client, source: str, instructions: str | None, model: str) -> dict:
    """把整理好的來源文字送 Gemini 改寫成文章草稿，回傳 {title, excerpt, body_markdown, tags}。"""
    user = source
    if instructions:
        user = f"（編輯要求：{instructions}）\n\n{source}"

    try:
        resp = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=_DRAFT_SYSTEM,
                temperature=0.7,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=ArticleDraft,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception as e:  # 網路 / 金鑰 / 配額等
        raise SummarizerError(f"Gemini 產生草稿失敗：{e}")

    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, ArticleDraft):
        return parsed.model_dump()
    # 後備：自行解析 JSON 文字
    try:
        data = json.loads(resp.text or "")
    except Exception:
        raise SummarizerError("模型未回傳有效的文章草稿。")
    data.setdefault("tags", [])
    return data


def draft_article(messages: list[dict], instructions: str | None = None, model: str | None = None) -> dict:
    """把選取的訊息改寫成文章草稿，回傳 {title, excerpt, body_markdown, tags}。

    model：後台選定的 Gemini 模型；未指定時用環境變數預設值。
    """
    if not messages:
        raise SummarizerError("沒有可用來產生草稿的訊息。")
    client = _client()
    draft_model = model or DRAFT_MODEL
    map_model = model or MAP_MODEL
    source = _condense(client, format_messages(messages), map_model)
    return _generate_draft(client, source, instructions, draft_model)


def draft_from_text(text: str, instructions: str | None = None, model: str | None = None) -> dict:
    """把貼上的一段對話（純文字）直接改寫成文章草稿，回傳 {title, excerpt, body_markdown, tags}。

    與 draft_article 的差別：不經過資料庫與訊息挑選，直接吃使用者貼上的原始文字，
    供「複製貼上即產草稿」的捷徑使用。model 同 draft_article。
    """
    text = (text or "").strip()
    if not text:
        raise SummarizerError("沒有可用來產生草稿的內容。")
    client = _client()
    draft_model = model or DRAFT_MODEL
    map_model = model or MAP_MODEL
    source = _condense(client, text, map_model)
    return _generate_draft(client, source, instructions, draft_model)
