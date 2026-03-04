from pathlib import Path

import httpx
import pytest

from mockture.errors import ContractConfigError
from mockture.errors import TemplateArgsError
from mockture.server import Mockture


def _build_mock(contract_path: Path, templates_path: Path, strict: bool = True) -> Mockture:
    return Mockture(
        contract_path=str(contract_path),
        templates_path=str(templates_path),
        strict=strict,
    )


def test_strict_valid_request_response_flow(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)
    mock.respond("create_order_success", order_id="ord-abc", order_status="queued")
    mock.start()

    try:
        response = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 2},
            timeout=5.0,
        )
        assert response.status_code == 201
        assert response.json() == {"order_id": "ord-abc", "status": "queued"}

        assert mock.calls_for("/orders", "POST").count == 1
        mock.assert_called("/orders", "POST", times=1)
        mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_config_time_contract_validation_failure(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)

    with pytest.raises(ContractConfigError):
        mock.respond("wrong_path")


def test_strict_runtime_request_violation_returns_500(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)
    mock.respond("create_order_success")
    mock.start()

    try:
        response = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},
            timeout=5.0,
        )
        assert response.status_code == 500

        with pytest.raises(AssertionError):
            mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_non_strict_runtime_request_violation_is_recorded_but_response_served(
    contract_path: Path,
    templates_path: Path,
) -> None:
    mock = _build_mock(contract_path, templates_path, strict=False)
    mock.respond("create_order_success", order_id="ord-loose")
    mock.start()

    try:
        response = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},
            timeout=5.0,
        )
        assert response.status_code == 201
        assert response.json()["order_id"] == "ord-loose"

        with pytest.raises(AssertionError):
            mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_runtime_response_violation_in_strict_mode_returns_500(
    contract_path: Path,
    templates_path: Path,
) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)
    mock.respond("create_order_success", order_id="ord-good")
    assert mock._configured
    mock._configured[0].body = {"bad": "payload"}
    mock.start()

    try:
        response = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 5},
            timeout=5.0,
        )
        assert response.status_code == 500

        with pytest.raises(AssertionError):
            mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_respond_bulk_dict_and_scenario_file(contract_path: Path, templates_path: Path, scenario_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)

    mock.respond({"create_order_success": {"order_id": "ord-from-dict"}})
    mock.respond(str(scenario_path))
    mock.start()

    try:
        first = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 1},
            timeout=5.0,
        )
        second = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-2", "quantity": 1},
            timeout=5.0,
        )

        assert first.status_code in (201, 409)
        assert second.status_code in (201, 409)
        assert mock.calls_for("/orders", "POST").count == 2
    finally:
        mock.stop()


def test_context_injects_incident_and_explicit_can_override(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)

    with mock.for_context(incident_id="INC-1", thread_count=2) as scoped:
        scoped.respond("patch_incident")
        scoped.respond("get_thread", thread_id=3, text="hello")

    with mock.for_context(incident_id="INC-2") as scoped:
        scoped.respond("get_thread", thread_id=4, text="override", incident_id="INC-9")

    mock.start()

    try:
        index = httpx.get(mock.url_for("/incidents/INC-1/threads"), timeout=5.0)
        thread = httpx.get(mock.url_for("/incidents/INC-1/threads/3"), timeout=5.0)
        override = httpx.get(mock.url_for("/incidents/INC-9/threads/4"), timeout=5.0)

        assert index.status_code == 200
        assert len(index.json()["items"]) == 2
        assert thread.status_code == 200
        assert thread.json()["id"] == 3
        assert override.status_code == 200
        assert override.json()["id"] == 4
    finally:
        mock.stop()


def test_context_does_not_leak_outside_with_block(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)

    with mock.for_context(incident_id="INC-1") as scoped:
        scoped.respond("get_thread", thread_id=1)

    with pytest.raises(TemplateArgsError):
        mock.respond("get_thread", thread_id=2)


def test_assert_called_failure_message(contract_path: Path, templates_path: Path) -> None:
    mock = _build_mock(contract_path, templates_path, strict=True)
    mock.respond("create_order_success")
    mock.start()

    try:
        with pytest.raises(AssertionError):
            mock.assert_called("/orders", "POST", times=1)
    finally:
        mock.stop()
