from pathlib import Path

import httpx
import pytest

from mockture import use_mockture


def _example_paths() -> tuple[str, str]:
    root = Path(__file__).resolve().parents[1]
    contract_path = Path(root, "configs", "basic_api.openapi.yml")
    templates_path = Path(root, "configs", "basic_api.templates.yml")
    return str(contract_path), str(templates_path)


_CONTRACT_PATH, _TEMPLATES_PATH = _example_paths()


@pytest.mark.mockture(
    contract=_CONTRACT_PATH,
    templates=_TEMPLATES_PATH,
    strict=True,
)
def test_marker_decorator_enables_mockture(mockture):  # type: ignore[no-untyped-def]
    """Test marker decorator enables mockture."""
    mockture.respond("create_order_success", order_id="ord-plugin-1", status="queued")
    response = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "SKU-1", "quantity": 1},
        timeout=5.0,
    )
    assert response.status_code == 201


@use_mockture(
    contract=_CONTRACT_PATH,
    templates=_TEMPLATES_PATH,
    strict=False,
)
def test_import_alias_decorator_enables_mockture(mockture):  # type: ignore[no-untyped-def]
    """Test import alias decorator enables mockture."""
    mockture.respond("create_order_success", order_id="ord-plugin-2")
    response = httpx.post(
        mockture.url_for("/orders"),
        json={"item_id": "", "quantity": 0},
        timeout=5.0,
    )
    assert response.status_code == 201
