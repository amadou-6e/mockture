"""Assertion helpers and call views for Mockture."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class CallRecord:
    """Captured request call."""

    method: str
    path: str
    json_body: Any
    headers: dict[str, str]
    status_code: int


@dataclass
class CallView:
    """Filtered call view returned by calls_for."""

    records: list[CallRecord] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.records)
