from pathlib import Path

import httpx

from mockture.errors import ContractConfigError
from mockture.server import Mockture


def _example_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    contract_path = Path(root, "configs", "basic_api.openapi.yml")
    templates_path = Path(root, "configs", "basic_api.templates.yml")
    return contract_path, templates_path


def test_happy_path_with_strict_mockture() -> None:
    """Test happy path with strict mockture."""
    contract_path, templates_path = _example_paths()

    mock = Mockture(
        contract_path=str(contract_path),
        templates_path=str(templates_path),
        strict=True,
    )
    mock.respond("create_order_success", order_id="ord-test-123", status="queued")
    mock.start()

    try:
        response = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 2},
            timeout=5.0,
        )
        assert response.status_code == 201
        assert response.json() == {"order_id": "ord-test-123", "status": "queued"}

        mock.assert_called(path="/orders", method="POST", times=1)
        mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_request_violation_strict_vs_non_strict() -> None:
    """Test request violation strict vs non strict."""
    contract_path, templates_path = _example_paths()

    strict_mock = Mockture(
        contract_path=str(contract_path),
        templates_path=str(templates_path),
        strict=True,
    )
    strict_mock.respond("create_order_success")
    strict_mock.start()

    try:
        strict_response = httpx.post(
            strict_mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},
            timeout=5.0,
        )
        assert strict_response.status_code == 500
    finally:
        strict_mock.stop()

    non_strict_mock = Mockture(
        contract_path=str(contract_path),
        templates_path=str(templates_path),
        strict=False,
    )
    non_strict_mock.respond("create_order_success", order_id="ord-non-strict")
    non_strict_mock.start()

    try:
        non_strict_response = httpx.post(
            non_strict_mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},
            timeout=5.0,
        )
        assert non_strict_response.status_code == 201
        assert non_strict_response.json()["order_id"] == "ord-non-strict"
    finally:
        non_strict_mock.stop()


def test_config_time_validation_blocks_invalid_template() -> None:
    """Test config time validation blocks invalid template."""
    contract_path, templates_path = _example_paths()

    mock = Mockture(
        contract_path=str(contract_path),
        templates_path=str(templates_path),
        strict=True,
    )

    try:
        mock.respond("invalid_success_shape")
        raise AssertionError("Expected ContractConfigError was not raised")
    except ContractConfigError:
        pass

