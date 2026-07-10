"""後台驗證：單一密碼登入 → 簽章 token（itsdangerous）。

環境變數：
- ADMIN_PASSWORD：後台密碼
- SECRET_KEY：簽 token 用的隨機字串

以函式內讀取 env 的方式取值，方便測試以 monkeypatch 覆寫。
"""

from __future__ import annotations

import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 天


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("SECRET_KEY", "dev-insecure-secret")
    return URLSafeTimedSerializer(secret, salt="hs-admin")


def check_password(password: str) -> bool:
    expected = os.environ.get("ADMIN_PASSWORD", "")
    return bool(expected) and hmac.compare_digest(password or "", expected)


def make_token() -> str:
    return _serializer().dumps({"role": "admin"})


def verify_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False
