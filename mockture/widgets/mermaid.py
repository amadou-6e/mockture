"""Mermaid sequence diagram rendering for mockture flows."""

from __future__ import annotations

from typing import Any


def flow_to_mermaid(
    steps: list[dict[str, Any]],
    client: str = "Test",
    server: str = "API",
) -> str:
    """Convert a list of rendered interaction dicts to a Mermaid sequence diagram.

    Parameters
    ----------
    steps : list[dict[str, Any]]
        Rendered interaction dicts from TemplateLibrary.render(), each containing
        ``method``, ``path``, and ``response`` keys.
    client : str
        Label for the caller actor.
    server : str
        Label for the API actor.

    Returns
    -------
    str
        A Mermaid ``sequenceDiagram`` string.
    """
    lines = [
        "sequenceDiagram",
        f"    participant {client}",
        f"    participant {server}",
    ]

    for step in steps:
        method = str(step.get("method", "?")).upper()
        path = str(step.get("path", "/"))
        response = step.get("response", {})
        status = response.get("status", "?")
        body = response.get("body")

        req_label = f"{method} {path}"
        resp_label = f"{status} {_status_text(status)}"

        if body and isinstance(body, dict):
            keys = list(body.keys())
            preview_keys = keys[:3]
            suffix = ", ..." if len(keys) > 3 else ""
            resp_label += " {" + ", ".join(preview_keys) + suffix + "}"

        lines.append(f"    {client}->>{server}: {req_label}")
        lines.append(f"    {server}-->>{client}: {resp_label}")

    return "\n".join(lines)


def mermaid_html(diagram: str) -> str:
    """Wrap a Mermaid diagram string in self-contained HTML for Jupyter rendering.

    Uses Mermaid Ink to render SVG via an image URL, which works in notebook
    environments that sanitize inline scripts.

    Parameters
    ----------
    diagram : str
        A Mermaid diagram string (e.g. from :func:`flow_to_mermaid`).

    Returns
    -------
    str
        HTML string that renders the diagram using the Mermaid CDN.
    """
    import base64
    import html

    uid = _uid()
    encoded = base64.urlsafe_b64encode(diagram.encode("utf-8")).decode("ascii")
    img_url = f"https://mermaid.ink/svg/{encoded}?bgColor=!white"
    diagram_html = html.escape(diagram)
    return f"""
<div id="mermaid-wrap-{uid}" style="background:#f9f9f9;border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin:4px 0;">
  <img src="{img_url}" alt="Mermaid diagram" style="max-width:100%;height:auto;display:block;" />
  <details style="margin-top:8px;">
    <summary style="cursor:pointer;color:#666;">Show Mermaid source</summary>
    <pre style="font-family:monospace;font-size:12px;white-space:pre;overflow-x:auto;margin:8px 0 0 0;">{diagram_html}</pre>
  </details>
</div>
"""


def _status_text(status: int | str) -> str:
    _MAP = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
    }
    try:
        return _MAP.get(int(status), "")
    except (ValueError, TypeError):
        return ""


def _uid() -> str:
    import random
    import string
    return "".join(random.choices(string.ascii_lowercase, k=8))
