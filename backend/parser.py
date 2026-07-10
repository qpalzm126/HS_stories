"""解析 LINE 匯出的聊天記錄 .txt 檔。

LINE App「匯出聊天記錄」產生的純文字格式（繁體中文行動版）大致如下：

    [LINE] 與Alice的聊天記錄
    儲存日期：2024/01/15 15:30

    2024/01/15（週一）
    15:20\tAlice\t你好嗎？
    15:21\t我\t還不錯，最近在忙專案
    15:22\tAlice\t照片
    15:23\tAlice\t[貼圖]
    15:24\tAlice\t這個連結給你
    https://example.com/very/long
    15:25\t我\t收到

規則：
- 前兩行是檔頭（`[LINE] ...` 與 `儲存日期：...`），略過。
- 「日期分隔行」單獨一行，如 `2024/01/15（週一）` 或 `2024.01.15 星期一`，
  用來設定「目前日期」。
- 「訊息行」為 `時間<TAB>發送者<TAB>內容`，時間為 24 小時制 `HH:MM`，
  也支援 `上午/下午 HH:MM`。
- 訊息內容可能跨多行（例如貼上長網址或換行文字），在下一個時間戳出現前，
  後續各行都併入上一則訊息內容。
- 媒體與系統訊息（照片、貼圖、影片、收回訊息…）以 msg_type 標記。

不同平台（iOS / Android / PC）與語言的匯出格式略有差異，本解析器盡量寬容處理。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---- 資料結構 -----------------------------------------------------------------


@dataclass
class ParsedMessage:
    sent_at: str          # ISO 8601，例如 "2024-01-15T15:20:00"（若無日期則僅時間）
    sender: str
    content: str
    msg_type: str         # text / sticker / image / video / audio / file / location / call / system


@dataclass
class ParsedExport:
    conversation: str
    messages: list[ParsedMessage] = field(default_factory=list)


# ---- 正規表達式 ---------------------------------------------------------------

# 日期分隔行：2024/01/15、2024.01.15、2024-01-15，後面可帶星期。
_DATE_RE = re.compile(
    r"^\s*(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})\s*"
    r"(?:[（(]?\s*(?:週|星期|周)?[一二三四五六日天]?\s*[)）]?|[A-Za-z]{3,9})?\s*$"
)

# 訊息行：時間<TAB>發送者<TAB>內容。內容允許為空。
# 時間支援 "15:20"、"上午 9:05"、"下午 3:20"、"AM 9:05"。
_MSG_RE = re.compile(
    r"^(?P<ampm>上午|下午|AM|PM|am|pm)?\s*"
    r"(?P<h>\d{1,2}):(?P<m>\d{2})\t"
    r"(?P<sender>[^\t]*)\t"
    r"(?P<content>.*)$"
)

# 檔頭首行：取出對話名稱。 例：「[LINE] 與Alice的聊天記錄」→ Alice
_HEADER_RE = re.compile(r"^\[LINE\]\s*(?:與|和)?\s*(?P<name>.+?)\s*(?:的)?聊天記錄\s*$")


# 媒體 / 系統訊息內容對照（去除方括號後比對）
_MEDIA_MAP = {
    "貼圖": "sticker",
    "照片": "image",
    "圖片": "image",
    "相片": "image",
    "影片": "video",
    "video": "video",
    "語音訊息": "audio",
    "語音留言": "audio",
    "檔案": "file",
    "位置": "location",
    "位置資訊": "location",
    "禮物": "gift",
}


def _classify(content: str) -> str:
    """依內容判斷訊息型別。"""
    stripped = content.strip()
    if not stripped:
        return "text"

    # 收回 / 通話等系統訊息
    if "收回訊息" in stripped or "已收回" in stripped:
        return "system"
    if stripped.startswith("☎") or "通話時間" in stripped or "未接來電" in stripped or "取消通話" in stripped:
        return "call"

    # 去除外層方括號後比對媒體字典
    key = stripped
    if key.startswith("[") and key.endswith("]"):
        key = key[1:-1].strip()
    return _MEDIA_MAP.get(key, "text")


def _norm_time(ampm: str | None, hour: int, minute: int) -> str:
    """把 12/24 小時制正規化成 HH:MM。"""
    if ampm in ("下午", "PM", "pm") and hour < 12:
        hour += 12
    elif ampm in ("上午", "AM", "am") and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def _conversation_from_header(line: str) -> str | None:
    m = _HEADER_RE.match(line.strip())
    if m:
        name = m.group("name").strip()
        return name or None
    return None


# ---- 主解析函式 ---------------------------------------------------------------


def parse_export(text: str, default_conversation: str | None = None) -> ParsedExport:
    """把整份匯出檔內容解析成 ParsedExport。

    default_conversation：當檔頭無法解析出對話名稱時的後備名稱（通常是檔名）。
    """
    # 去除 BOM 並統一換行
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    conversation: str | None = None
    current_date: str | None = None            # "YYYY-MM-DD"
    messages: list[ParsedMessage] = []

    for idx, raw in enumerate(lines):
        line = raw.rstrip("\n")

        # 檔頭首行嘗試取對話名稱
        if conversation is None and line.startswith("[LINE]"):
            conversation = _conversation_from_header(line)
            continue
        # 儲存日期行略過
        if line.startswith("儲存日期") or line.startswith("Saved on"):
            continue

        # 日期分隔行
        dm = _DATE_RE.match(line)
        if dm:
            y, mo, d = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
            current_date = f"{y:04d}-{mo:02d}-{d:02d}"
            continue

        # 訊息行
        mm = _MSG_RE.match(line)
        if mm:
            hhmm = _norm_time(mm.group("ampm"), int(mm.group("h")), int(mm.group("m")))
            sent_at = f"{current_date}T{hhmm}:00" if current_date else f"{hhmm}:00"
            content = mm.group("content")
            messages.append(
                ParsedMessage(
                    sent_at=sent_at,
                    sender=mm.group("sender").strip(),
                    content=content,
                    msg_type=_classify(content),
                )
            )
            continue

        # 空行：若緊接在訊息之後，視為訊息內容的一部分（保留一個換行）
        if line == "":
            continue

        # 其他非時間戳開頭的行 → 併入上一則訊息（多行訊息續行）
        if messages:
            prev = messages[-1]
            prev.content = (prev.content + "\n" + line) if prev.content else line
            # 併入後重新判斷型別（原本可能被判為 media 但其實是多行文字）
            prev.msg_type = _classify(prev.content)
        # 若還沒有任何訊息就出現雜訊行，直接忽略

    if not conversation:
        conversation = default_conversation or "未命名對話"

    return ParsedExport(conversation=conversation, messages=messages)
