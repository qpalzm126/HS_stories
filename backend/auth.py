"""驗證：用外部論壇（HeavensBride / TCGM）帳密代理登入 → 簽章 token（itsdangerous）。

改造重點（見 docs/login-plan.md）：
- 移除單一 ADMIN_PASSWORD 密碼登入，改為代理登入外部站驗證身分。
- admin 身分由環境變數白名單 ADMIN_USERS 決定，格式 `server:username`
  （避免兩站同名衝突），例：`ADMIN_USERS=heavensbride:alice,tcgm:bob`。
- token payload 改存使用者身分 `{"u": username, "s": server, "a": is_admin}`。

安全底線：**絕不儲存使用者的論壇密碼**（DB、log、token 都不放）。
密碼只在登入當下轉發給外部站驗證，用完即棄。

環境變數：
- ADMIN_USERS：admin 白名單（逗號分隔的 `server:username`）。
- SECRET_KEY：簽 token 用的隨機字串。

以函式內讀取 env 的方式取值，方便測試以 monkeypatch 覆寫。
"""

from __future__ import annotations

import hashlib
import os
import re

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 天

# 支援的外部登入來源
SERVERS = ("heavensbride", "tcgm")

# 代理登入逾時（秒）；外部站掛掉時不要卡死。
HTTP_TIMEOUT = 15.0

# 外部站「成功判斷字串」集中成常數，日後對方改版好改（見 login-plan §8）。
TCGM_BASE = "https://ms.tcgm.tw"
TCGM_LOGIN_SUCCESS_MARK = "/welcome/logout"

HB_BASE = "https://heavensbride.org"
HB_LOGIN_FAIL_MARK = "Password incorrect"

# SMF 隱藏欄位：value 為 32 字元 hex 的 sessionId；name 為隨機 CSRF 欄位名。
# 排除 name 為 hash_passwrd 的欄位（那是密碼雜湊，不是 sessionId）。
_HB_HIDDEN_INPUT = re.compile(
    r'<input\b[^>]*\btype="hidden"[^>]*>', re.IGNORECASE
)
_HB_ATTR_NAME = re.compile(r'\bname="([^"]+)"', re.IGNORECASE)
_HB_ATTR_VALUE = re.compile(r'\bvalue="([0-9a-fA-F]{32})"', re.IGNORECASE)


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("SECRET_KEY", "dev-insecure-secret")
    return URLSafeTimedSerializer(secret, salt="hs-admin")


# ---- admin 白名單 -------------------------------------------------------------


def _admin_users() -> set[str]:
    raw = os.environ.get("ADMIN_USERS", "")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def is_admin_user(server: str, username: str) -> bool:
    return f"{server}:{username}".strip().lower() in _admin_users()


# ---- token ------------------------------------------------------------------


def make_token(username: str, server: str, is_admin: bool) -> str:
    return _serializer().dumps({"u": username, "s": server, "a": bool(is_admin)})


def verify_token(token: str | None) -> dict | None:
    """回傳 payload dict（{"u","s","a"}）或 None。"""
    if not token:
        return None
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# ---- 外部站代理登入 -----------------------------------------------------------


def _calculate_hb_hash(username: str, password: str, session_id: str) -> str:
    """SMF 標準密碼雜湊（見 login-plan §3b 步驟 3）。"""
    inner = hashlib.sha1((username.lower() + password).encode("utf-8")).hexdigest()
    return hashlib.sha1((inner + session_id).encode("utf-8")).hexdigest()


def _parse_hb_session_token(html: str) -> tuple[str, str] | None:
    """從 SMF 登入頁 HTML 解析 (CSRF 欄位名, sessionId)。

    找所有 <input type="hidden">，取 value 為 32 hex 的那個，排除 name=hash_passwrd。
    回 (name, value) 或 None。
    """
    for tag in _HB_HIDDEN_INPUT.findall(html):
        name_m = _HB_ATTR_NAME.search(tag)
        value_m = _HB_ATTR_VALUE.search(tag)
        if not name_m or not value_m:
            continue
        name = name_m.group(1)
        if name == "hash_passwrd":
            continue
        return name, value_m.group(1)
    return None


def login_tcgm(username: str, password: str) -> bool:
    """TCGM 表單式登入（見 login-plan §3a）。成功回 True，帳密錯回 False。"""
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        # 1) 取初始 cookie
        client.get(f"{TCGM_BASE}/")
        # 2) 送出登入表單（明文密碼是該站協定）
        client.post(
            f"{TCGM_BASE}/welcome/login",
            data={"account": username, "pwd": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # 3) 驗證：登入後首頁應含登出連結
        home = client.get(f"{TCGM_BASE}/home/")
        return home.status_code == 200 and TCGM_LOGIN_SUCCESS_MARK in home.text


def login_heavensbride(username: str, password: str) -> bool:
    """HeavensBride（SMF）SHA1 挑戰式登入（見 login-plan §3b）。"""
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        # 1) 取登入頁 HTML + cookie
        page = client.get(f"{HB_BASE}/index.php?action=login")
        parsed = _parse_hb_session_token(page.text)
        if not parsed:
            return False
        csrf_name, session_id = parsed
        # 3) 算密碼雜湊（明文密碼不送）
        hash_passwrd = _calculate_hb_hash(username, password, session_id)
        # 4) 送出登入
        resp = client.post(
            f"{HB_BASE}/index.php?action=login2",
            data={
                "user": username,
                "passwrd": "",
                "cookielength": "-1",
                "hash_passwrd": hash_passwrd,
                csrf_name: session_id,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # 5) SMF 失敗仍回 200，body 會含 Password incorrect
        return HB_LOGIN_FAIL_MARK not in resp.text


def proxy_login(server: str, username: str, password: str) -> bool:
    if server == "tcgm":
        return login_tcgm(username, password)
    if server == "heavensbride":
        return login_heavensbride(username, password)
    return False
