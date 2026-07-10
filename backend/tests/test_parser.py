from pathlib import Path

from backend.parser import parse_export

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.txt"


def _parse():
    return parse_export(FIXTURE.read_text(encoding="utf-8"), default_conversation="fallback")


def test_conversation_name_from_header():
    result = _parse()
    assert result.conversation == "Alice"


def test_message_count():
    result = _parse()
    # 12 則訊息（多行訊息合併為一則）
    assert len(result.messages) == 12


def test_first_message_fields():
    m = _parse().messages[0]
    assert m.sent_at == "2024-01-15T09:05:00"
    assert m.sender == "Alice"
    assert m.content == "早安，今天要開會嗎？"
    assert m.msg_type == "text"


def test_media_types():
    msgs = _parse().messages
    assert msgs[2].msg_type == "image"      # 照片
    assert msgs[3].msg_type == "sticker"    # [貼圖]
    assert msgs[8].msg_type == "video"      # [影片]


def test_system_unsent_message():
    msgs = _parse().messages
    assert msgs[9].msg_type == "system"     # 已收回訊息
    assert "收回訊息" in msgs[9].content


def test_multiline_message_merged():
    m = _parse().messages[4]                # 10:20 帶長網址的多行訊息
    assert m.sent_at == "2024-01-15T10:20:00"
    assert m.content.startswith("這個連結給你參考")
    assert "https://example.com/some/very/long/path" in m.content
    assert "記得看第二段" in m.content
    assert "\n" in m.content


def test_am_pm_time_conversion():
    msgs = _parse().messages
    assert msgs[6].sent_at == "2024-01-16T08:30:00"   # 上午 8:30
    assert msgs[7].sent_at == "2024-01-16T14:15:00"   # 下午 2:15


def test_date_rolls_over_to_next_day():
    msgs = _parse().messages
    assert msgs[5].sent_at.startswith("2024-01-15")
    assert msgs[6].sent_at.startswith("2024-01-16")


def test_fallback_conversation_when_no_header():
    result = parse_export("2024/01/15（週一）\n10:00\tBob\t哈囉", default_conversation="myfile")
    assert result.conversation == "myfile"
    assert result.messages[0].sender == "Bob"
