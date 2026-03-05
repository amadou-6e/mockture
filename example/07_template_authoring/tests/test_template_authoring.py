"""07_template_authoring â€” x-mockture annotations + two-file layout.

The OpenAPI spec carries x-mockture-template / x-mockture-defaults /
x-mockture-required annotations. Running:

    mockture generate configs/basic_api.openapi.yml

produces configs/basic_api.templates.auto.yml (safe to overwrite).

Hand-authored templates that cannot be expressed as annotations
(e.g., intentional violations) live in configs/basic_api.templates.yml.

The mockture.ini in this directory points at basic_api.templates.auto.yml
as the primary templates file. Tests that need the hand-authored templates
load the extra file explicitly via a second respond() or by merging.
"""

import httpx
import pytest


# ---------------------------------------------------------------------------
# Tests using the auto-generated templates (from x-mockture annotations)
# ---------------------------------------------------------------------------

@pytest.mark.mockture(api="basic_api")
def test_auto_generated_create_order(mockture) -> None:
    """Template created by mockture generate from x-mockture-defaults."""
    mockture.respond("create_order_success", order_id="ord-gen-1")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 201
    assert r.json()["order_id"] == "ord-gen-1"
    mockture.assert_no_contract_violations()


@pytest.mark.mockture(api="basic_api")
def test_auto_generated_get_order(mockture) -> None:
    """get_order has order_id as required (x-mockture-required)."""
    mockture.respond("get_order", order_id="ord-gen-2", status="processing")

    r = httpx.get(mockture.url_for("/orders/ord-gen-2"), timeout=5.0)

    assert r.status_code == 200
    assert r.json() == {"order_id": "ord-gen-2", "status": "processing"}
    mockture.assert_no_contract_violations()


@pytest.mark.mockture(api="basic_api")
def test_auto_generated_conflict(mockture) -> None:
    """Conflict template â€” default message comes from x-mockture-defaults."""
    mockture.respond("create_order_conflict")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-2", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 409
    assert r.json()["message"] == "Item is unavailable"


@pytest.mark.mockture(api="basic_api")
def test_required_arg_must_be_supplied(mockture) -> None:
    """get_order requires order_id â€” omitting it raises TemplateArgsError."""
    from mockture.errors import TemplateArgsError

    with pytest.raises(TemplateArgsError):
        mockture.respond("get_order")  # missing required order_id


# ---------------------------------------------------------------------------
# Two-file layout: auto-generated + hand-authored together
# ---------------------------------------------------------------------------
# For tests that need templates from the hand-authored file alongside
# auto-generated ones, load the hand-authored file via an explicit templates=
# override on the marker (or load both files separately).

@pytest.mark.mockture(
    contract="../configs/basic_api.openapi.yml",
    templates="../configs/basic_api.templates.yml",
    strict=False,
)
def test_hand_authored_invalid_template(mockture) -> None:
    """Hand-authored template that intentionally violates the contract schema.

    Using strict=False so respond() does not raise at config-time â€” the
    test verifies the response shape, not contract compliance.
    """
    mockture.respond("invalid_success_shape")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-3", "quantity": 1},
        timeout=5.0,
    )

    # The mock returns the invalid body; the violation is recorded.
    assert r.status_code == 201
    assert "bad_field" in r.json()
