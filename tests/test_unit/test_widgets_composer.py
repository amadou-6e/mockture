from __future__ import annotations

from pathlib import Path

import pytest


def test_loads_single_existing_flow_on_init(tmp_path: Path) -> None:
    pytest.importorskip("ipywidgets")
    pytest.importorskip("IPython")

    templates_path = Path(tmp_path, "templates.yml")
    templates_path.write_text(
        "\n".join(
            [
                "templates:",
                "  create_order_success:",
                "    args:",
                "      status_code: 201",
                "      order_id: ord-default",
                "      status: created",
                "    interaction:",
                "      method: POST",
                "      path: /orders",
                "      response:",
                "        status: \"{status_code}\"",
                "        body:",
                "          order_id: \"{order_id}\"",
                "          status: \"{status}\"",
                "  get_order:",
                "    args:",
                "      order_id:",
                "      status_code: 200",
                "      status: created",
                "    interaction:",
                "      method: GET",
                "      path: /orders/{order_id}",
                "      response:",
                "        status: \"{status_code}\"",
                "        body:",
                "          order_id: \"{order_id}\"",
                "          status: \"{status}\"",
            ]
        ),
        encoding="utf-8",
    )

    flows_path = Path(tmp_path, "flows.yml")
    flows_path.write_text(
        "\n".join(
            [
                "flows:",
                "  create_and_fetch:",
                "  - template: create_order_success",
                "    args:",
                "      status_code: '201'",
                "      order_id: ord-001",
                "      status: queued",
                "  - template: get_order",
                "    args:",
                "      order_id: ord-001",
                "      status_code: '200'",
                "      status: queued",
            ]
        ),
        encoding="utf-8",
    )

    from mockture.widgets import FlowComposer

    composer = FlowComposer(
        templates_path=str(templates_path),
        flows_path=str(flows_path),
    )

    assert composer._name_input.value == "create_and_fetch"
    assert [step["template_name"] for step in composer._steps] == [
        "create_order_success",
        "get_order",
    ]


def test_mermaid_html_handles_multiline_diagram_source() -> None:
    from mockture.widgets.mermaid import mermaid_html

    diagram = "\n".join(
        [
            "sequenceDiagram",
            "    participant Test",
            "    participant API",
            "    Test->>API: GET /orders/ord-001",
            "    API-->>Test: 200 OK {order_id, status}",
        ]
    )

    html = mermaid_html(diagram)

    assert "<img " in html
    assert "https://mermaid.ink/svg/" in html
    assert "Show Mermaid source" in html
