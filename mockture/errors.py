"""Typed exceptions for Mockture."""


class MocktureError(Exception):
    """Base class for all library exceptions."""


class TemplateNotFoundError(MocktureError):
    """Raised when a template reference cannot be resolved."""


class TemplateArgsError(MocktureError):
    """Raised when template arguments are missing or invalid."""


class ScenarioFormatError(MocktureError):
    """Raised when a scenario file/dict has an unsupported shape."""


class ContractConfigError(MocktureError):
    """Raised during config-time contract validation."""


class ContractRuntimeError(MocktureError):
    """Raised during request-time or response-time contract validation."""

