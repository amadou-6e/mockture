from pathlib import Path

import pytest
import yaml

from mockture.errors import ScenarioFormatError
from mockture.templates import normalize_respond_input


def test_respond_single_template_input() -> None:
    invocations = normalize_respond_input("create_order_success", {"order_id": "ord-1"})
    assert invocations == [("create_order_success", {"order_id": "ord-1"})]


def test_respond_dict_payload_input() -> None:
    payload = {
        "create_order_success": {"order_id": "ord-1"},
        "create_order_conflict": [{"message": "a"}, {"message": "b"}],
    }

    invocations = normalize_respond_input(payload, {})

    assert len(invocations) == 3
    assert invocations[0][0] == "create_order_success"


def test_respond_path_payload_input(tmp_path: Path) -> None:
    scenario = Path(tmp_path, "scenario.yml")
    scenario.write_text(
        yaml.safe_dump({"create_order_success": {"order_id": "ord-path"}}),
        encoding="utf-8",
    )

    invocations = normalize_respond_input(str(scenario), {})

    assert invocations == [("create_order_success", {"order_id": "ord-path"})]


def test_respond_dict_rejects_kwargs() -> None:
    with pytest.raises(ScenarioFormatError):
        normalize_respond_input({"create_order_success": {}}, {"unexpected": 1})


def test_respond_path_rejects_kwargs(tmp_path: Path) -> None:
    scenario = Path(tmp_path, "scenario.yml")
    scenario.write_text("create_order_success: {}", encoding="utf-8")

    with pytest.raises(ScenarioFormatError):
        normalize_respond_input(str(scenario), {"unexpected": 1})

