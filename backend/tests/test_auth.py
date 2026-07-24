import httpx
import pytest

from backend import auth


# ---- admin 白名單 -------------------------------------------------------------


def test_is_admin_user(monkeypatch):
    monkeypatch.setenv("ADMIN_USERS", "heavensbride:alice, tcgm:Bob")
    assert auth.is_admin_user("heavensbride", "alice")
    assert auth.is_admin_user("tcgm", "bob")  # 大小寫不敏感
    assert auth.is_admin_user("TCGM", "BOB")
    assert not auth.is_admin_user("tcgm", "alice")  # 不同站同名不算
    assert not auth.is_admin_user("heavensbride", "carol")


def test_admin_users_empty(monkeypatch):
    monkeypatch.delenv("ADMIN_USERS", raising=False)
    assert not auth.is_admin_user("heavensbride", "anyone")


# ---- token ------------------------------------------------------------------


def test_token_roundtrip(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    token = auth.make_token("alice", "heavensbride", True)
    payload = auth.verify_token(token)
    assert payload == {"u": "alice", "s": "heavensbride", "a": True}
    assert auth.verify_token("garbage") is None
    assert auth.verify_token(None) is None


def test_token_rejected_with_different_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret-a")
    token = auth.make_token("bob", "tcgm", False)
    monkeypatch.setenv("SECRET_KEY", "secret-b")
    assert auth.verify_token(token) is None


# ---- HeavensBride SMF 雜湊與解析 ---------------------------------------------


def test_calculate_hb_hash_known_values():
    # 與 login-plan §3b 演算法對照的已知答案（username 先轉小寫）。
    sid = "0123456789abcdef0123456789abcdef"
    assert auth._calculate_hb_hash("Alice", "secret", sid) == (
        "dbca7fc7c74d2f974c735c692ff819e6c93edb95"
    )


def test_parse_hb_session_token():
    html = (
        '<form>'
        '<input type="hidden" name="hash_passwrd" value="">'
        '<input type="hidden" name="a1b2c3d4e5f6" '
        'value="00112233445566778899aabbccddeeff">'
        '</form>'
    )
    assert auth._parse_hb_session_token(html) == (
        "a1b2c3d4e5f6",
        "00112233445566778899aabbccddeeff",
    )


def test_parse_hb_session_token_none():
    assert auth._parse_hb_session_token("<form>no hidden fields</form>") is None


# ---- 代理登入（mock httpx）---------------------------------------------------


def _mock_client(monkeypatch, handler):
    """把 httpx.Client 換成用 MockTransport 的版本。"""
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs.pop("follow_redirects", None)
        return real_client(transport=httpx.MockTransport(handler), follow_redirects=True)

    monkeypatch.setattr(auth.httpx, "Client", factory)


def test_login_tcgm_success(monkeypatch):
    def handler(request):
        if request.url.path == "/home/":
            return httpx.Response(200, text="歡迎 <a href='/welcome/logout'>登出</a>")
        return httpx.Response(200, text="ok")

    _mock_client(monkeypatch, handler)
    assert auth.login_tcgm("alice", "pw") is True


def test_login_tcgm_failure(monkeypatch):
    def handler(request):
        if request.url.path == "/home/":
            return httpx.Response(200, text="請先登入")
        return httpx.Response(200, text="ok")

    _mock_client(monkeypatch, handler)
    assert auth.login_tcgm("alice", "wrong") is False


def test_login_heavensbride_success(monkeypatch):
    login_html = (
        '<input type="hidden" name="csrf" '
        'value="00112233445566778899aabbccddeeff">'
    )

    def handler(request):
        if "action=login2" in str(request.url):
            return httpx.Response(200, text="登入成功，歡迎回來")
        return httpx.Response(200, text=login_html)

    _mock_client(monkeypatch, handler)
    assert auth.login_heavensbride("alice", "pw") is True


def test_login_heavensbride_failure(monkeypatch):
    login_html = (
        '<input type="hidden" name="csrf" '
        'value="00112233445566778899aabbccddeeff">'
    )

    def handler(request):
        if "action=login2" in str(request.url):
            return httpx.Response(200, text="Password incorrect")
        return httpx.Response(200, text=login_html)

    _mock_client(monkeypatch, handler)
    assert auth.login_heavensbride("alice", "wrong") is False


def test_proxy_login_unknown_server():
    assert auth.proxy_login("unknown", "a", "b") is False
