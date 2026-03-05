"""08_multi_api â€” Auth API tests.

mockture.ini in this directory points at configs/auth/.
Completely independent from tests_orders/ â€” different contract,
different templates, different Mockture instance.
"""

import httpx
import pytest


@pytest.mark.mockture
def test_login_success(mockture) -> None:
    """Test login success."""
    mockture.respond("login_success", access_token="tok-abc123")

    r = httpx.post(
        mockture.url_for("/auth/token"),
        json={"username": "alice", "password": "secret"},
        timeout=5.0,
    )

    assert r.status_code == 200
    assert r.json()["access_token"] == "tok-abc123"
    assert r.json()["token_type"] == "bearer"
    mockture.assert_no_contract_violations()


@pytest.mark.mockture
def test_login_unauthorized(mockture) -> None:
    """Test login unauthorized."""
    mockture.respond("login_unauthorized")

    r = httpx.post(
        mockture.url_for("/auth/token"),
        json={"username": "bad", "password": "wrong"},
        timeout=5.0,
    )

    assert r.status_code == 401
    assert "Invalid credentials" in r.json()["message"]


@pytest.mark.mockture
def test_get_me(mockture) -> None:
    """Test get me."""
    mockture.respond("get_me", user_id="usr-001", username="alice")

    r = httpx.get(mockture.url_for("/auth/me"), timeout=5.0)

    assert r.status_code == 200
    assert r.json() == {"user_id": "usr-001", "username": "alice"}
    mockture.assert_called(path="/auth/me", method="GET", times=1)
    mockture.assert_no_contract_violations()
