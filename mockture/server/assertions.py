"""Assertion helpers and call views for Mockture."""

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

class CallRecord(BaseModel):
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

    model_config = ConfigDict(frozen=True)

    method: str
    path: str
    json_body: Any
    headers: dict[str, str]
    status_code: int


class CallView(BaseModel):
    """Filtered call view returned by ``calls_for``.

    Parameters
    ----------
    records : list[CallRecord], default=[]
        Captured records that match a filter.
    """

    records: list[CallRecord] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.records)
