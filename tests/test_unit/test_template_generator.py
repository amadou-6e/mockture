from pathlib import Path

import pytest
import yaml

from mockture.errors import ContractConfigError
from mockture.templates import TemplateGenerator


def _example_contract() -> str:
    return str(Path("example", "configs", "basic_api.openapi.yml"))


def test_builds_templates_via_response_method() -> None:
    generator = TemplateGenerator(_example_contract())

    (
        generator.path("/orders")
        .method("post")
        .response("create_order_success", 201)
        .to_template()
    )
    (
        generator.path("/orders")
        .method("post")
        .response("create_order_conflict", 409)
        .to_template()
    )
    (
        generator.path("/orders")
        .method("post")
        .custom("invalid_response_shape", 201, body={"bad_field": "oops"})
        .to_template()
    )

    templates = generator.templates()

    # Bug fix: field names used as-is (no rename: status stays 'status', not 'order_status')
    success = templates["create_order_success"]
    assert success["args"]["status_code"] == 201
    assert success["args"]["order_id"] == ""   # type-based fallback (string), no hardcoded default
    assert success["args"]["status"] == ""     # field name unchanged, no hardcoded 'created'
    assert success["interaction"]["response"]["body"]["order_id"] == "{order_id}"
    assert success["interaction"]["response"]["body"]["status"] == "{status}"

    # Bug fix: no hardcoded 'Item is unavailable' default
    conflict = templates["create_order_conflict"]
    assert conflict["args"]["status_code"] == 409
    assert conflict["args"]["message"] == ""   # type-based fallback (string)
    assert conflict["interaction"]["response"]["body"]["message"] == "{message}"

    invalid = templates["invalid_response_shape"]
    assert invalid["args"] == {"status_code": 201}
    assert invalid["interaction"]["response"]["body"] == {"bad_field": "oops"}


def test_params_override_inferred_defaults() -> None:
    generator = TemplateGenerator(_example_contract())
    (
        generator.path("/orders")
        .method("post")
        .params(order_id="ord-explicit", status="queued")
        .response("create_order_success", 201)
        .to_template()
    )

    template = generator.templates()["create_order_success"]
    assert template["args"]["order_id"] == "ord-explicit"
    assert template["args"]["status"] == "queued"


def test_method_all_generates_per_response_code() -> None:
    generator = TemplateGenerator(_example_contract())
    generator.path("/orders").method("post").all().to_templates()

    templates = generator.templates()
    assert "post_orders_success_201" in templates
    assert "post_orders_failure_409" in templates


def test_generator_all_generates_templates_for_spec() -> None:
    generator = TemplateGenerator(_example_contract())
    generator.all().to_templates()

    templates = generator.templates()
    assert "post_orders_success_201" in templates
    assert "post_orders_failure_409" in templates


def test_save_writes_yaml(tmp_path: Path) -> None:
    output = Path(tmp_path, "generated.templates.yml")
    generator = TemplateGenerator(_example_contract())
    generator.path("/orders").method("post").response("create_order_success", 201).to_template()
    generator.save(str(output))

    saved = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert "templates" in saved
    assert "create_order_success" in saved["templates"]


def test_raises_for_unknown_path() -> None:
    generator = TemplateGenerator(_example_contract())
    with pytest.raises(ContractConfigError):
        generator.path("/missing").method("post").response("missing", 201).to_template()


def test_duplicate_name_raises() -> None:
    generator = TemplateGenerator(_example_contract())
    generator.path("/orders").method("post").response("create_order_success", 201).to_template()
    with pytest.raises(ContractConfigError, match="Duplicate template name"):
        generator.path("/orders").method("post").response("create_order_success", 201).to_template()
