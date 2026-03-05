"""Prototype provenance registration for pytest plugin usage.

This file shows one way to centralize where each API definition lives
(python service + contract/templates/flows files) and expose defaults
at different pytest scopes.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parent

# "basic_api" is the named provenance bundle.
MOCKTURE_PROVENANCE = {
    "basic_api": {
        "service_module": "example.basic_api:app",
        "contract": str(Path(_ROOT, "configs", "basic_api.openapi.yml")),
        "templates": str(Path(_ROOT, "configs", "basic_api.templates.yml")),
        "flows": str(Path(_ROOT, "configs", "orders.flows.example.yml")),
    }
}


@pytest.fixture(scope="session")
def mockture_session_defaults() -> dict[str, str]:
    """Session-wide default provenance for shorthand marker usage."""
    bundle = MOCKTURE_PROVENANCE["basic_api"]
    return {
        "contract": bundle["contract"],
        "templates": bundle["templates"],
        "flows_path": bundle["flows"],
    }


@pytest.fixture(scope="module")
def mockture_module_defaults(mockture_session_defaults: dict[str, str]) -> dict[str, str]:
    """Module-level override point if a module targets a different API."""
    return dict(mockture_session_defaults)

