"""用 Google Gemini 由一段內容產生「文章草稿」。

- 內文（body_markdown）＝使用者提供的原始內容，原封不動、不經模型改寫。
- 只用 Gemini 產生 title / excerpt / tags（結構化 JSON，response_schema 保證欄位齊全）。
  → 需要「編輯」的只有標題；摘要與標籤是給列表/桌面小工具顯示用的擷取，不動內文。
- map-reduce：內容過長時先分段濃縮，只是給模型「讀懂內容以擬標題」，不影響內文。
- 只有後台選取／貼上的內容會送到 Gemini API。
- 需環境變數 GEMINI_API_KEY（Google AI Studio 免費金鑰；也接受 GOOGLE_API_KEY）。
"""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel

# 預設用 gemini-flash-latest：Google 維護的別名，永遠指向當前的 Flash 版本，
# 不會像固定版號（如 gemini-2.5-flash）被淘汰後回 404。後台仍可即時改選其他模型，
# 也可用環境變數覆寫。
MAP_MODEL = os.environ.get("HS_DRAFT_MAP_MODEL", "gemini-flash-latest")
DRAFT_MODEL = os.environ.get("HS_DRAFT_MODEL", "gemini-flash-latest")

CHUNK_CHARS = 12000

# 列出可用 model 時，排除非「文字改寫」用途者（語音、影像、機器人等），只留 Gemini/Gemma 對話模型。
_MODEL_EXCLUDE = (
    "tts", "image", "audio", "embedding", "robotics", "computer-use",
    "lyria", "nano-banana", "deep-research", "antigravity", "omni", "aqa", "vision",
)


class SummarizerError(Exception):
    pass


class ArticleMeta(BaseModel):
    """AI 只需回傳的欄位；內文不由模型產生，故不含 body。作為 response_schema。"""

    title: str
    excerpt: str
    tags: list[str] = []


_META_SYSTEM = (
    "你是『聖靈故事』網站的編輯。下面是使用者提供的一段見證分享的原始內容。\n"
    "重要：**不要改寫、不要濃縮、也不要重寫內文**——文章內文會原封不動使用這段原始內容，"
    "你看不到、也不需要輸出內文。你只需根據內容產生標題與摘要，且必須忠於原意、"
    "不杜撰未提到的事、不加入原文沒有的資訊。全部用繁體中文。\n"
    "title＝一個具體、精煉、吸引人的標題（這是唯一需要你『編輯』的地方；"
    "即使原文已有標題，也請重新擬得更貼切好讀）。\n"
    "excerpt＝1～2 句重點摘錄，供文章列表與桌面小工具顯示（擷取自原文重點即可）。\n"
    "tags＝2～4 個主題標籤。"
)

_MAP_SYSTEM = (
    "你是資料整理助理。用繁體中文濃縮以下內容片段，"
    "盡量保留人名、時間、事件經過與見證細節（之後只用來擬標題與摘要）。只輸出濃縮後的文字。"
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


def _generate_meta(client: genai.Client, source: str, instructions: str | None, model: str) -> dict:
    """讀原始內容，只請 Gemini 產生 {title, excerpt, tags}（不改寫內文）。"""
    user = source
    if instructions:
        user = f"（編輯要求：{instructions}）\n\n{source}"

    try:
        resp = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=_META_SYSTEM,
                temperature=0.7,
                max_output_tokens=1024,
                response_mime_type="application/json",
                response_schema=ArticleMeta,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception as e:  # 網路 / 金鑰 / 配額等
        raise SummarizerError(f"Gemini 產生標題失敗：{e}")

    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, ArticleMeta):
        return parsed.model_dump()
    # 後備：自行解析 JSON 文字
    try:
        data = json.loads(resp.text or "")
    except Exception:
        raise SummarizerError("模型未回傳有效的標題與摘要。")
    data.setdefault("excerpt", "")
    data.setdefault("tags", [])
    return data


def _draft(client: genai.Client, body: str, instructions: str | None, model: str | None) -> dict:
    """共用：內文用 body 原文，另用 Gemini 產標題/摘要，回傳 {title, excerpt, body_markdown, tags}。"""
    draft_model = model or DRAFT_MODEL
    map_model = model or MAP_MODEL
    meta = _generate_meta(client, _condense(client, body, map_model), instructions, draft_model)
    return {
        "title": meta["title"],
        "excerpt": meta.get("excerpt", ""),
        "body_markdown": body,  # 原文照登，不經模型改寫
        "tags": meta.get("tags", []),
    }


def draft_article(messages: list[dict], instructions: str | None = None, model: str | None = None) -> dict:
    """把選取的訊息產成文章草稿；內文＝訊息原文，AI 只產標題/摘要。

    model：後台選定的 Gemini 模型；未指定時用環境變數預設值。
    """
    if not messages:
        raise SummarizerError("沒有可用來產生草稿的訊息。")
    client = _client()
    return _draft(client, format_messages(messages), instructions, model)


def draft_from_text(text: str, instructions: str | None = None, model: str | None = None) -> dict:
    """把貼上的一段內容產成文章草稿；內文＝貼上的原文，AI 只產標題/摘要。

    與 draft_article 的差別：不經過資料庫與訊息挑選，直接吃使用者貼上的原始文字，
    供「複製貼上即產草稿」的捷徑使用。model 同 draft_article。
    """
    text = (text or "").strip()
    if not text:
        raise SummarizerError("沒有可用來產生草稿的內容。")
    client = _client()
    return _draft(client, text, instructions, model)
