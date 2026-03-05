"""Prototype usage examples for the Mockture pytest plugin.

Assumes provenance is configured elsewhere (for example in pyproject.toml):
- mockture_contract
- mockture_templates
- mockture_flows

Or centrally in `example/conftest.py` as a named bundle like "basic_api".
"""

from __future__ import annotations

import pytest

from mockture import use_mockture


@pytest.mark.mockture("basic_api:order_previous_call_flow")
def test_named_flow_short_form(mockture):  # type: ignore[no-untyped-def]
    """Test named flow short form."""
    # "basic_api" provenance resolves to contract/templates/flows.
    # "order_previous_call_flow" resolves inside that flows registry.
    pass


@pytest.mark.mockture("basic_api:[create_order_success,invalid_success_shape]")
def test_inline_sequence_short_form(mockture):  # type: ignore[no-untyped-def]
    """Test inline sequence short form."""
    # Same idea, but inline sequence on top of the "basic_api" bundle.
    pass


@pytest.mark.mockture("basic_api:order_previous_call_flow", scope="module")
def test_module_scope(mockture):  # type: ignore[no-untyped-def]
    """Test module scope."""
    # Same Mockture instance can be reused by tests in this module.
    pass


@use_mockture("basic_api:order_previous_call_flow", scope="session")
def test_session_scope_with_alias(mockture):  # type: ignore[no-untyped-def]
    """Test session scope with alias."""
    # Same Mockture instance can be reused across the session.
    pass
