"""Directive expansion for template response bodies."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

from mockture.errors import TemplateArgsError


def expand_body_directives(body: Any, args: dict[str, Any], path: str) -> Any:
    """Expand built-in directives in a response body payload."""
    cloned = deepcopy(body)
    return _expand_node(cloned, args, path)


def _expand_node(node: Any, args: dict[str, Any], path: str) -> Any:
    if isinstance(node, dict):
        if "$thread" in node and len(node) == 1:
            return _build_thread_payload(node["$thread"])
        if "$generate" in node and len(node) == 1:
            return _generate_value(node["$generate"], args, path)
        return {key: _expand_node(value, args, path) for key, value in node.items()}
    if isinstance(node, list):
        return [_expand_node(item, args, path) for item in node]
    return node


def _generate_value(name: Any, args: dict[str, Any], path: str) -> Any:
    generator = str(name)
    if generator == "thread_links":
        return _generate_thread_links(args, path)
    raise TemplateArgsError(
        f"Unknown $generate directive '{generator}' in path '{path}'. "
        "Hint: use one of the built-in generators."
    )


def _generate_thread_links(args: dict[str, Any], path: str) -> list[dict[str, str]]:
    try:
        incident_id = str(args["incident_id"])
    except KeyError as exc:
        raise TemplateArgsError(
            "Missing required 'incident_id' for thread_links generator. "
            "Hint: provide it via context or respond(...)."
        ) from exc

    thread_count = int(args.get("thread_count", 1))
    base_url = str(args.get("base_url", "http://localhost:8888"))
    return [
        {
            "rel": "self",
            "href": (
                f"{base_url}/services/rest/connect/v1.4/incidents/"
                f"{incident_id}/threads/{index}"
            ),
        }
        for index in range(1, thread_count + 1)
    ]


def _build_thread_payload(thread_args: dict[str, Any]) -> dict[str, Any]:
    try:
        thread_id = int(thread_args["id"])
        text = str(thread_args["text"])
        entry_type = str(thread_args.get("entry_type", "customer")).lower()
        channel = str(thread_args.get("channel", "EMAIL"))
        incident_id = str(thread_args["incident_id"])
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise TemplateArgsError(
            f"Missing thread field '{missing}' in $thread directive. "
            "Hint: provide all required thread values."
        ) from exc

    if entry_type == "staff":
        entry = {"id": 2, "lookupName": "Staff Account"}
    else:
        entry = {"id": 3, "lookupName": "Customer"}

    timestamp = datetime.now(UTC) + timedelta(minutes=max(thread_id, 1) * 5)
    iso_time = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    href = (
        "https://msh--tst.custhelp.com/services/rest/connect/v1.4/incidents/"
        f"{incident_id}/threads/{thread_id}"
    )

    return {
        "id": thread_id,
        "text": text,
        "createdTime": iso_time,
        "displayOrder": thread_id,
        "entryType": entry,
        "contentType": {"id": 1, "lookupName": "text/plain"},
        "account": None,
        "contact": None,
        "channel": {"id": 1, "lookupName": channel},
        "mailHeader": None,
        "links": [
            {"rel": "self", "href": href},
            {"rel": "canonical", "href": href},
            {
                "rel": "describedby",
                "href": (
                    "https://msh--tst.custhelp.com/services/rest/connect/v1.4/"
                    "metadata-catalog/incidents/threads"
                ),
                "mediaType": "application/schema+json",
            },
        ],
    }
