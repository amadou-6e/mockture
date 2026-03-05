"""Scoped context manager for Mockture configuration."""

from __future__ import annotations

from typing import Any


class MocktureContext:
    """Context-scoped facade over a parent Mockture instance.

    Parameters
    ----------
    parent : Any
        Parent mock instance that registers interactions.
    context_args : dict[str, Any]
        Context values merged into each template invocation.
    """

    def __init__(self, parent: Any, context_args: dict[str, Any]) -> None:
        self._parent = parent
        self._context_args = context_args

    def __enter__(self) -> "MocktureContext":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def respond(self, target: str | dict[str, Any], **kwargs: Any) -> "MocktureContext":
        """Register responses using bound context args.

        Parameters
        ----------
        target : str | dict[str, Any]
            Template name, scenario file path, or inline scenario mapping.
        **kwargs : Any
            Explicit args for template rendering.

        Returns
        -------
        MocktureContext
            The same context for chaining.
        """
        self._parent._respond_with_context(self._context_args, target, kwargs)
        return self
