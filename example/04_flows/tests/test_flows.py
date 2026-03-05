"""04_flows â€” Named flows, sequences, and scenario files.

Covers all the formats supported by the flows engine:
  - sequence (list of template names / {template, args} dicts)
  - single-template shorthand string
  - scenario dict (keys = template names)
  - scenario YAML file loaded via file path
  - inline sequence on the marker (sequence=)
  - inline scenario on the marker (scenario=)
"""

from pathlib import Path

import httpx
import pytest


_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# ---------------------------------------------------------------------------
# Named flows from flows.yml (loaded via api= + mockture.ini)
# ---------------------------------------------------------------------------

@pytest.mark.mockture(api="basic_api", flow="create_and_fetch")
def test_named_sequence_flow(mockture) -> None:
    """create_and_fetch: POST /orders then GET /orders/{order_id}."""
    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-flow-001"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_post.json()["order_id"] == "ord-flow-001"
    assert r_get.status_code == 200


@pytest.mark.mockture(api="basic_api", flow="conflict_only")
def test_named_single_template_flow(mockture) -> None:
    """conflict_only: single template name as string value in flows.yml."""
    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-2", "quantity": 1},
        timeout=5.0,
    )
    assert r.status_code == 409


@pytest.mark.mockture(api="basic_api", flow="happy_path_scenario")
def test_named_scenario_dict_flow(mockture) -> None:
    """happy_path_scenario: scenario dict in flows.yml."""
    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-3", "quantity": 2},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-happy-001"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_get.status_code == 200
    assert r_get.json()["order_id"] == "ord-happy-001"


# ---------------------------------------------------------------------------
# Inline sequence on the marker
# ---------------------------------------------------------------------------

@pytest.mark.mockture(
    api="basic_api",
    sequence=[
        "create_order_success",                          # template name only â€” uses defaults
        {"template": "get_order", "args": {"order_id": "ord-seq-1", "status": "created"}},
    ],
)
def test_inline_sequence_on_marker(mockture) -> None:
    """Test inline sequence on marker."""
    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-4", "quantity": 1},
        timeout=5.0,
    )
    r_get = httpx.get(mockture.url_for("/orders/ord-seq-1"), timeout=5.0)

    assert r_post.status_code == 201
    assert r_get.status_code == 200


# ---------------------------------------------------------------------------
# Inline scenario on the marker
# ---------------------------------------------------------------------------

@pytest.mark.mockture(
    api="basic_api",
    scenario={
        "create_order_success": {"order_id": "ord-scen-1", "status": "queued"},
        "create_order_conflict": None,
    },
)
def test_inline_scenario_on_marker(mockture) -> None:
    """Test inline scenario on marker."""
    r = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-5", "quantity": 1},
        timeout=5.0,
    )
    assert r.status_code in (201, 409)


# ---------------------------------------------------------------------------
# Scenario YAML file loaded via file path
# ---------------------------------------------------------------------------

@pytest.mark.mockture(api="basic_api")
def test_scenario_yaml_file(mockture) -> None:
    """Pass a file path to respond() â€” loads a scenario YAML."""
    scenario_path = str(_SCENARIOS_DIR / "reorder_scenario.yml")
    mockture.respond(scenario_path)

    r_post = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-6", "quantity": 1},
        timeout=5.0,
    )
    assert r_post.status_code == 201
    assert r_post.json()["order_id"] == "ord-reorder-001"

    r_get = httpx.get(mockture.url_for("/orders/ord-reorder-001"), timeout=5.0)
    assert r_get.status_code == 200


# ---------------------------------------------------------------------------
# Multiple invocations of same template (list value in scenario)
# ---------------------------------------------------------------------------

@pytest.mark.mockture(api="basic_api")
def test_multiple_invocations_same_template(mockture) -> None:
    """Scenario dict with a list value registers multiple interactions."""
    mockture.respond({
        "create_order_success": [
            {"order_id": "ord-multi-1", "status": "created"},
            {"order_id": "ord-multi-2", "status": "queued"},
        ]
    })

    r1 = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "A", "quantity": 1},
        timeout=5.0,
    )
    r2 = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "B", "quantity": 1},
        timeout=5.0,
    )

    assert r1.status_code == 201
    assert r2.status_code == 201
    mockture.assert_called(path="/orders", method="POST", times=2)
