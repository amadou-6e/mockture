"""02_plugin_explicit — pytest plugin with explicit paths on every marker.

Every marker carries contract= and templates= directly.
No mockture.ini needed — good for one-off tests or when you want
the paths to be visible in the test file itself.
"""

from pathlib import Path

import httpx
import pytest

from mockture import use_mockture


_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = str(_ROOT / "configs" / "basic_api.openapi.yml")
_TEMPLATES = str(_ROOT / "configs" / "basic_api.templates.yml")


@pytest.mark.mockture(contract=_CONTRACT, templates=_TEMPLATES, strict=True)
def test_create_order_with_explicit_paths(mockture) -> None:
    mockture.respond("create_order_success", order_id="ord-explicit-1", status="queued")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 201
    assert r.json() == {"order_id": "ord-explicit-1", "status": "queued"}
    mockture.assert_called(path="/orders", method="POST", times=1)
    mockture.assert_no_contract_violations()


@use_mockture(contract=_CONTRACT, templates=_TEMPLATES, strict=False)
def test_use_mockture_alias(mockture) -> None:
    """use_mockture is an import alias for pytest.mark.mockture."""
    mockture.respond("create_order_success", order_id="ord-alias")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-2", "quantity": 2},
        timeout=5.0,
    )

    assert r.status_code == 201
    assert r.json()["order_id"] == "ord-alias"


@pytest.mark.mockture(contract=_CONTRACT, templates=_TEMPLATES, strict=True)
def test_fetch_order_by_id(mockture) -> None:
    mockture.respond("get_order", order_id="ord-fetch-1", status="processing")

    r = httpx.get(mockture.url_for("/orders/ord-fetch-1"), timeout=5.0)

    assert r.status_code == 200
    assert r.json() == {"order_id": "ord-fetch-1", "status": "processing"}


@pytest.mark.mockture(contract=_CONTRACT, templates=_TEMPLATES, strict=True)
def test_conflict_explicit(mockture) -> None:
    mockture.respond("create_order_conflict")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-3", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 409
    assert r.json()["message"] == "Item is unavailable"


@pytest.mark.mockture(contract=_CONTRACT, templates=_TEMPLATES, strict=True)
def test_inline_scenario_dict(mockture) -> None:
    """respond() accepts a dict mapping template names to args."""
    mockture.respond({
        "create_order_success": {"order_id": "ord-s1", "status": "created"},
        "get_order": {"order_id": "ord-s1", "status": "created"},
    })

    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-4", "quantity": 1},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-s1"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_get.status_code == 200
