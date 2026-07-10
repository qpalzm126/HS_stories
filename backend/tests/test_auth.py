from backend import auth


def test_check_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    assert auth.check_password("secret123")
    assert not auth.check_password("wrong")
    assert not auth.check_password("")


def test_empty_admin_password_rejects_all(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert not auth.check_password("")
    assert not auth.check_password("anything")


def test_token_roundtrip(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    token = auth.make_token()
    assert auth.verify_token(token)
    assert not auth.verify_token("garbage")
    assert not auth.verify_token(None)


def test_token_rejected_with_different_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret-a")
    token = auth.make_token()
    monkeypatch.setenv("SECRET_KEY", "secret-b")
    assert not auth.verify_token(token)
