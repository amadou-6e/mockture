"""01_basic â€” Raw Mockture object, no pytest plugin.

Shows the full lifecycle: construct â†’ respond â†’ start â†’ assert â†’ stop.
No fixtures, no ini files. Good starting point for understanding
what the plugin automates.
"""

from pathlib import Path

import httpx
import pytest

from mockture import MocktureError
from mockture.errors import ContractConfigError
from mockture.server import Mockture


_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = str(_ROOT / "configs" / "basic_api.openapi.yml")
_TEMPLATES = str(_ROOT / "configs" / "basic_api.templates.yml")


def _mock(**kwargs) -> Mockture:
    return Mockture(contract_path=_CONTRACT, templates_path=_TEMPLATES, **kwargs)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_create_order_returns_201() -> None:
    """Test create order returns 201."""
    mock = _mock(strict=True)
    mock.respond("create_order_success", order_id="ord-123", status="queued")
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 2},
            timeout=5.0,
        )
        assert r.status_code == 201
        assert r.json() == {"order_id": "ord-123", "status": "queued"}

        mock.assert_called(path="/orders", method="POST", times=1)
        mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_fetch_order_returns_200() -> None:
    """Test fetch order returns 200."""
    mock = _mock(strict=True)
    mock.respond("get_order", order_id="ord-456", status="processing")
    mock.start()

    try:
        r = httpx.get(mock.url_for("/orders/ord-456"), timeout=5.0)
        assert r.status_code == 200
        assert r.json() == {"order_id": "ord-456", "status": "processing"}

        mock.assert_called(path="/orders/{order_id}", method="GET", times=1)
        mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_conflict_returns_409() -> None:
    """Test conflict returns 409."""
    mock = _mock(strict=True)
    mock.respond("create_order_conflict", message="Duplicate item")
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-2", "quantity": 1},
            timeout=5.0,
        )
        assert r.status_code == 409
        assert r.json()["message"] == "Duplicate item"
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# respond() chaining
# ---------------------------------------------------------------------------

def test_respond_chaining_registers_multiple_interactions() -> None:
    """Test respond chaining registers multiple interactions."""
    mock = _mock(strict=True)
    (
        mock
        .respond("create_order_success", order_id="ord-chain-1")
        .respond("get_order", order_id="ord-chain-1", status="created")
    )
    mock.start()

    try:
        httpx.post(mock.url_for("/orders"), json={"item_id": "A", "quantity": 1}, timeout=5.0)
        httpx.get(mock.url_for("/orders/ord-chain-1"), timeout=5.0)

        mock.assert_called(path="/orders", method="POST", times=1)
        mock.assert_called(path="/orders/{order_id}", method="GET", times=1)
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# respond() before start()
# ---------------------------------------------------------------------------

def test_respond_before_start_queues_interaction() -> None:
    """Test respond before start queues interaction."""
    mock = _mock(strict=True)
    mock.respond("create_order_success", order_id="ord-prequeue")
    # Interaction is registered before the server is running.
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "B", "quantity": 1},
            timeout=5.0,
        )
        assert r.status_code == 201
        assert r.json()["order_id"] == "ord-prequeue"
    finally:
        mock.stop()


# ---------------------------------------------------------------------------
# Config-time validation
# ---------------------------------------------------------------------------

def test_invalid_template_raises_at_respond_time() -> None:
    """Test invalid template raises at respond time."""
    mock = _mock(strict=True)
    with pytest.raises(ContractConfigError):
        mock.respond("invalid_success_shape")


# ---------------------------------------------------------------------------
# calls_for() inspection
# ---------------------------------------------------------------------------

def test_calls_for_returns_recorded_requests() -> None:
    """Test calls for returns recorded requests."""
    mock = _mock(strict=False)
    mock.respond("create_order_success")
    mock.start()

    try:
        httpx.post(mock.url_for("/orders"), json={"item_id": "C", "quantity": 3}, timeout=5.0)
        httpx.post(mock.url_for("/orders"), json={"item_id": "D", "quantity": 1}, timeout=5.0)

        view = mock.calls_for("/orders", "POST")
        assert view.count == 2
        bodies = [rec.json_body for rec in view.records]
        assert {"item_id": "C", "quantity": 3} in bodies
        assert {"item_id": "D", "quantity": 1} in bodies
    finally:
        mock.stop()
