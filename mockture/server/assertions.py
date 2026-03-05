"""Assertion helpers and call views for Mockture."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class CallRecord:
    """Captured request call.

    Parameters
    ----------
    method : str
        Request HTTP method.
    path : str
        Request path.
    json_body : Any
        Parsed JSON payload captured from the request.
    headers : dict[str, str]
        Captured request headers.
    status_code : int
        Status code served by the mock response.
    """

    method: str
    path: str
    json_body: Any
    headers: dict[str, str]
    status_code: int


@dataclass
class CallView:
    """Filtered call view returned by ``calls_for``.

    Parameters
    ----------
    records : list[CallRecord], default=[]
        Captured records that match a filter.
    """

    records: list[CallRecord] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.records)
