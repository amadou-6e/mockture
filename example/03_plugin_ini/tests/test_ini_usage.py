"""03_plugin_ini — mockture.ini + configs_dir + api= on the marker.

The ini file in this directory points configs_dir at ../../configs.
With api="basic_api", the plugin resolves:
  - configs/basic_api.openapi.yml   → contract
  - configs/basic_api.templates.yml → templates
  - configs/basic_api.flows.yml     → flows (optional)

Markers only need to say what to do, not where files live.
"""

import httpx
import pytest


@pytest.mark.mockture(api="basic_api", strict=True)
def test_create_order_via_ini(mockture) -> None:
    """Minimal marker — all paths come from mockture.ini."""
    mockture.respond("create_order_success", order_id="ord-ini-1")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )

    assert r.status_code == 201
    assert r.json()["order_id"] == "ord-ini-1"
    mockture.assert_called(path="/orders", method="POST", times=1)
    mockture.assert_no_contract_violations()


@pytest.mark.mockture(api="basic_api", strict=True)
def test_fetch_order_via_ini(mockture) -> None:
    mockture.respond("get_order", order_id="ord-ini-2", status="processing")

    r = httpx.get(mockture.url_for("/orders/ord-ini-2"), timeout=5.0)

    assert r.status_code == 200
    assert r.json() == {"order_id": "ord-ini-2", "status": "processing"}


@pytest.mark.mockture(api="basic_api", strict=True)
def test_scenario_dict_via_ini(mockture) -> None:
    """Inline scenario dict — respond() with a dict."""
    mockture.respond({
        "create_order_success": {"order_id": "ord-ini-3", "status": "queued"},
        "get_order": {"order_id": "ord-ini-3", "status": "queued"},
    })

    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-2", "quantity": 2},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-ini-3"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_get.status_code == 200


@pytest.mark.mockture(api="basic_api", flow="create_and_fetch")
def test_named_flow_via_ini(mockture) -> None:
    """Pre-registered named flow from basic_api.flows.yml."""
    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-3", "quantity": 1},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-flow-001"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_get.status_code == 200


@pytest.mark.mockture(flow="basic_api:conflict_only")
def test_shorthand_flow_syntax(mockture) -> None:
    """'api:flow_name' shorthand — equivalent to api='basic_api', flow='conflict_only'."""
    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-4", "quantity": 1},
        timeout=5.0,
    )
    assert r.status_code == 409


@pytest.mark.mockture(api="basic_api", strict=False, scope="module")
def test_module_scope_first(mockture) -> None:
    """Module-scoped instance — shared with test_module_scope_second below."""
    mockture.respond("create_order_success", order_id="ord-mod-1")

    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-5", "quantity": 1},
        timeout=5.0,
    )
    assert r.status_code == 201


@pytest.mark.mockture(api="basic_api", strict=False, scope="module")
def test_module_scope_second(mockture) -> None:
    """Same module-scoped instance — interactions from test_module_scope_first are still registered."""
    mockture.respond("get_order", order_id="ord-mod-1", status="created")

    r = httpx.get(mockture.url_for("/orders/ord-mod-1"), timeout=5.0)
    assert r.status_code == 200
    # Both the POST (from first test) and GET (from this test) have been called.
    mockture.assert_called(path="/orders", method="POST", times=1)
    mockture.assert_called(path="/orders/{order_id}", method="GET", times=1)
