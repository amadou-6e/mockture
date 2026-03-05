"""08_multi_api â€” Orders API tests.

mockture.ini in this directory points at configs/orders/.
Markers use no api= â€” the ini provides contract and templates directly.
"""

import httpx
import pytest


@pytest.mark.mockture
def test_create_order(mockture) -> None:
    """Test create order."""
    mockture.respond("create_order_success", order_id="ord-multi-1")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 2},
        timeout=5.0,
    )

    assert r.status_code == 201
    assert r.json()["order_id"] == "ord-multi-1"
    mockture.assert_no_contract_violations()


@pytest.mark.mockture
def test_create_order_conflict(mockture) -> None:
    """Test create order conflict."""
    mockture.respond("create_order_conflict")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-2", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 409


@pytest.mark.mockture
def test_fetch_order(mockture) -> None:
    """Test fetch order."""
    mockture.respond("get_order", order_id="ord-multi-2", status="processing")

    r = httpx.get(mockture.url_for("/orders/ord-multi-2"), timeout=5.0)

    assert r.status_code == 200
    assert r.json() == {"order_id": "ord-multi-2", "status": "processing"}
