from pathlib import Path

import pytest
import yaml

from mockture.errors import ScenarioFormatError
from mockture.errors import TemplateArgsError
from mockture.errors import TemplateNotFoundError
from mockture.templates import TemplateLibrary


def test_loads_valid_templates(templates_path: Path) -> None:
    library = TemplateLibrary(str(templates_path))
    assert library.has_template("create_order_success")


def test_rejects_templates_missing_root(tmp_path: Path) -> None:
    bad_file = Path(tmp_path, "bad_templates.yml")
    bad_file.write_text("not_templates: {}", encoding="utf-8")

    with pytest.raises(ScenarioFormatError):
        TemplateLibrary(str(bad_file))


def test_missing_templates_file_raises(tmp_path: Path) -> None:
    missing_file = Path(tmp_path, "missing.yml")

    with pytest.raises(TemplateNotFoundError):
        TemplateLibrary(str(missing_file))


def test_render_applies_defaults_and_interpolation(templates_path: Path) -> None:
    library = TemplateLibrary(str(templates_path))

    interaction = library.render(
        template_name="create_order_success",
        context_args={},
        explicit_args={"order_id": "ord-777"},
    )

    response = interaction["response"]
    assert interaction["method"] == "POST"
    assert interaction["path"] == "/orders"
    assert response["status"] == 201
    assert response["body"]["order_id"] == "ord-777"
    assert response["body"]["status"] == "created"


def test_render_raises_when_required_arg_missing(templates_path: Path) -> None:
    library = TemplateLibrary(str(templates_path))

    with pytest.raises(TemplateArgsError):
        library.render(
            template_name="patch_incident",
            context_args={},
            explicit_args={},
        )


def test_context_and_explicit_override_defaults(templates_path: Path) -> None:
    library = TemplateLibrary(str(templates_path))

    interaction = library.render(
        template_name="create_order_success",
        context_args={"order_status": "pending"},
        explicit_args={"order_status": "shipped"},
    )

    assert interaction["response"]["body"]["status"] == "shipped"


def test_normalize_scenario_payload_with_list_entries() -> None:
    payload = {
        "create_order_success": {"order_id": "ord-1"},
        "create_order_conflict": [
            {"message": "m1"},
            {"message": "m2"},
        ],
    }

    invocations = TemplateLibrary.normalize_scenario_payload(payload)

    assert invocations == [
        ("create_order_success", {"order_id": "ord-1"}),
        ("create_order_conflict", {"message": "m1"}),
        ("create_order_conflict", {"message": "m2"}),
    ]


def test_normalize_scenario_payload_invalid_shape_raises() -> None:
    payload = {"create_order_success": "bad"}

    with pytest.raises(ScenarioFormatError):
        TemplateLibrary.normalize_scenario_payload(payload)


def test_generate_and_thread_directives_expand(templates_path: Path) -> None:
    library = TemplateLibrary(str(templates_path))

    index_interaction = library.render(
        template_name="patch_incident",
        context_args={"incident_id": "INC-123", "thread_count": 2},
        explicit_args={},
    )
    items = index_interaction["response"]["body"]["items"]
    assert len(items) == 2
    assert items[0]["href"].endswith("/incidents/INC-123/threads/1")

    thread_interaction = library.render(
        template_name="get_thread",
        context_args={"incident_id": "INC-123"},
        explicit_args={"thread_id": 5, "entry_type": "staff"},
    )
    body = thread_interaction["response"]["body"]
    assert body["id"] == 5
    assert body["entryType"]["lookupName"] == "Staff Account"


def test_template_file_can_be_round_tripped(templates_path: Path, tmp_path: Path) -> None:
    raw = yaml.safe_load(Path(templates_path).read_text(encoding="utf-8"))
    copied = Path(tmp_path, "copied.yml")
    copied.write_text(yaml.safe_dump(raw), encoding="utf-8")

    library = TemplateLibrary(str(copied))
    assert library.has_template("create_order_conflict")
