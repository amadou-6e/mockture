import httpx
import pytest

from mockture import use_mockture


@pytest.mark.mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    scenario="tests/configs/fixtures/test_orders.flows.yml",
)
def test_marker_enables_mockture_fixture(mockture):  # type: ignore[no-untyped-def]
    response = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert response.status_code in (201, 409)
    assert mockture.calls_for("/orders", "POST").count == 1


@use_mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    strict=False,
)
def test_imported_decorator_alias_works(mockture):  # type: ignore[no-untyped-def]
    mockture.respond("create_order_success", order_id="ord-decorator", status="queued")

    response = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "", "quantity": 0},
        timeout=5.0,
    )
    assert response.status_code == 201
    assert response.json()["order_id"] == "ord-decorator"


@pytest.mark.mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    flow="order_previous_call_flow",
    flows_path="tests/configs/fixtures/test_named.flows.yml",
)
def test_named_flow_registration_works(mockture):  # type: ignore[no-untyped-def]
    first = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    second = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert {first.status_code, second.status_code}.issubset({201, 409})
    assert mockture.calls_for("/orders", "POST").count == 2


@pytest.mark.mockture("order_previous_call_flow")
def test_named_flow_registration_via_positional_arg(mockture):  # type: ignore[no-untyped-def]
    first = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    second = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert {first.status_code, second.status_code}.issubset({201, 409})
    assert mockture.calls_for("/orders", "POST").count == 2


@pytest.mark.mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    sequence=["create_order_success", "create_order_bad_response"],
    strict=False,
)
def test_inline_sequence_registration_works(mockture):  # type: ignore[no-untyped-def]
    first = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    second = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert mockture.calls_for("/orders", "POST").count == 2


@pytest.mark.mockture(["create_order_success", "create_order_bad_response"], strict=False)
def test_inline_sequence_registration_via_positional_arg(mockture):  # type: ignore[no-untyped-def]
    first = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    second = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert mockture.calls_for("/orders", "POST").count == 2


_MODULE_SCOPE_INSTANCE_ID: int | None = None


@pytest.mark.mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    scope="module",
)
def test_module_scope_reuses_same_instance_first(mockture):  # type: ignore[no-untyped-def]
    global _MODULE_SCOPE_INSTANCE_ID
    _MODULE_SCOPE_INSTANCE_ID = id(mockture)


@pytest.mark.mockture(
    contract="tests/configs/fixtures/test_openapi.yml",
    templates="tests/configs/fixtures/test_orders.templates.yml",
    scope="module",
)
def test_module_scope_reuses_same_instance_second(mockture):  # type: ignore[no-untyped-def]
    assert _MODULE_SCOPE_INSTANCE_ID is not None
    assert id(mockture) == _MODULE_SCOPE_INSTANCE_ID
