"""06_strict_modes â€” strict=True vs strict=False.

strict=True (default):
  - Config-time: respond() raises ContractConfigError for schema-invalid bodies.
  - Runtime: a request that violates the schema returns HTTP 500 instead of
    the configured response.

strict=False:
  - Config-time: respond() silently records violations (no raise).
  - Runtime: the configured response is returned even on schema violations.
  - All violations accumulate and can be inspected via assert_no_contract_violations().
"""

from pathlib import Path

import httpx
import pytest

from mockture.errors import ContractConfigError
from mockture.server import Mockture


_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = str(_ROOT / "configs" / "basic_api.openapi.yml")
_TEMPLATES = str(_ROOT / "configs" / "basic_api.templates.yml")


def _mock(**kwargs) -> Mockture:
    return Mockture(contract_path=_CONTRACT, templates_path=_TEMPLATES, **kwargs)


# ---------------------------------------------------------------------------
# Config-time validation (respond() phase)
# ---------------------------------------------------------------------------

def test_strict_raises_on_invalid_template_body() -> None:
    """With strict=True, respond() raises immediately for a body that violates the schema."""
    mock = _mock(strict=True)
    with pytest.raises(ContractConfigError):
        mock.respond("invalid_success_shape")


def test_non_strict_does_not_raise_on_invalid_template_body() -> None:
    """With strict=False, respond() accepts the invalid template without raising."""
    mock = _mock(strict=False)
    # Does not raise â€” violation is recorded internally.
    mock.respond("invalid_success_shape")


# ---------------------------------------------------------------------------
# Runtime validation (request phase)
# ---------------------------------------------------------------------------

def test_strict_returns_500_on_bad_request() -> None:
    """With strict=True, a request that violates the schema aborts with HTTP 500."""
    mock = _mock(strict=True)
    mock.respond("create_order_success")
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},  # violates minLength and minimum
            timeout=5.0,
        )
        assert r.status_code == 500
        body = r.json()
        assert body["error"] == "contract_violation"
    finally:
        mock.stop()


def test_non_strict_returns_configured_response_on_bad_request() -> None:
    """With strict=False, a violating request still gets the configured response."""
    mock = _mock(strict=False)
    mock.respond("create_order_success", order_id="ord-ns-1")
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},  # violates schema
            timeout=5.0,
        )
        assert r.status_code == 201
        assert r.json()["order_id"] == "ord-ns-1"
    finally:
        mock.stop()


def test_non_strict_violations_accumulate() -> None:
    """Violations accumulate in non-strict mode and can be checked at the end."""
    mock = _mock(strict=False)
    mock.respond("create_order_success", order_id="ord-ns-2")
    mock.start()

    try:
        # Send a bad request.
        httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "", "quantity": 0},
            timeout=5.0,
        )

        with pytest.raises(AssertionError, match="contract"):
            mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_strict_valid_request_has_no_violations() -> None:
    """A well-formed request in strict mode records no violations."""
    mock = _mock(strict=True)
    mock.respond("create_order_success", order_id="ord-valid")
    mock.start()

    try:
        r = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 2},
            timeout=5.0,
        )
        assert r.status_code == 201
        mock.assert_no_contract_violations()
    finally:
        mock.stop()
