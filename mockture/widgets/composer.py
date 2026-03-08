"""Jupyter widget for composing and saving mockture flows visually."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mockture.templates.library import TemplateLibrary
from mockture.widgets.mermaid import flow_to_mermaid, mermaid_html


class FlowComposer:
    """Interactive Jupyter widget for building and saving mockture flows.

    Displays a template picker, an editable ordered list of interactions,
    a live Mermaid sequence diagram, and a save control that writes the
    composed flow to a flows YAML file.

    Parameters
    ----------
    templates_path : str
        Path to the templates YAML file.
    flows_path : str, optional
        Path to the flows YAML file. If provided, flows can be saved into it.

    Examples
    --------
    ::

        from mockture.widgets import FlowComposer

        composer = FlowComposer(
            templates_path="configs/api.templates.yml",
            flows_path="configs/api.flows.yml",
        )
        composer.show()
    """

    def __init__(
        self,
        templates_path: str,
        flows_path: str | None = None,
    ) -> None:
        try:
            import ipywidgets as widgets
            from IPython.display import HTML, display
        except ImportError as exc:
            raise ImportError(
                "FlowComposer requires ipywidgets and IPython. "
                "Install with: pip install 'mockture[widgets]'"
            ) from exc

        self._w = widgets
        self._display = display
        self._HTML = HTML

        self._library = TemplateLibrary(templates_path=templates_path)
        self._flows_path = Path(flows_path) if flows_path else None
        self._steps: list[dict[str, Any]] = []
        self._busy = False

        self._root = self._build_ui()
        self._load_initial_flow()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        """Render the composer widget in the current Jupyter cell."""
        self._display(self._root)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> Any:
        w = self._w
        template_names = sorted(self._library._templates.keys())

        self._template_dropdown = w.Dropdown(
            options=template_names,
            description="Template:",
            layout=w.Layout(width="360px"),
        )
        self._add_btn = w.Button(
            description="Add",
            button_style="primary",
            icon="plus",
            layout=w.Layout(width="80px"),
        )
        self._add_btn.on_click(self._on_add)

        self._flow_box = w.VBox([], layout=w.Layout(padding="4px 0"))

        self._diagram_out = w.Output(
            layout=w.Layout(
                border="1px solid #e0e0e0",
                border_radius="6px",
                padding="8px",
                min_height="120px",
            )
        )

        self._name_input = w.Text(
            placeholder="my_flow_name",
            description="Flow name:",
            layout=w.Layout(width="320px"),
        )
        self._save_btn = w.Button(
            description="Save",
            button_style="success",
            icon="save",
            disabled=self._flows_path is None,
            layout=w.Layout(width="80px"),
        )
        self._save_btn.on_click(self._on_save)
        self._status_lbl = w.Label(
            "", layout=w.Layout(margin="0 0 0 8px")
        )

        return w.VBox([
            w.HTML("<b>Add interaction</b>"),
            w.HBox([self._template_dropdown, self._add_btn]),
            w.HTML("<b style='margin-top:12px'>Flow steps</b>"),
            self._flow_box,
            w.HTML("<b style='margin-top:12px'>Sequence diagram</b>"),
            self._diagram_out,
            w.HTML("<b style='margin-top:12px'>Save flow</b>"),
            w.HBox([self._name_input, self._save_btn, self._status_lbl]),
        ], layout=w.Layout(padding="8px"))

    # ------------------------------------------------------------------
    # Step row construction
    # ------------------------------------------------------------------

    def _build_step_row(self, idx: int) -> Any:
        w = self._w
        step = self._steps[idx]
        name = step["template_name"]
        interaction = self._library._templates[name]["interaction"]
        method = str(interaction.get("method", "?")).upper()
        path = str(interaction.get("path", "?"))
        defaults = self._library._templates[name]["args"]

        header = w.HTML(
            f"<b style='color:#444'>{idx + 1}. {method} {path}</b>"
            f"&nbsp;<span style='color:#aaa;font-size:0.85em'>({name})</span>"
        )

        up_btn = w.Button(icon="arrow-up", layout=w.Layout(width="34px", height="28px"))
        dn_btn = w.Button(icon="arrow-down", layout=w.Layout(width="34px", height="28px"))
        rm_btn = w.Button(icon="trash", button_style="danger", layout=w.Layout(width="34px", height="28px"))

        up_btn.on_click(self._make_up_handler(idx))
        dn_btn.on_click(self._make_down_handler(idx))
        rm_btn.on_click(self._make_remove_handler(idx))

        arg_rows = []
        for key, default_val in defaults.items():
            required = default_val is None
            lbl = w.Label(
                f"{key}{'*' if required else ''}:",
                layout=w.Layout(width="130px"),
            )
            txt = w.Text(
                value=str(step["args"].get(key, "") or ""),
                layout=w.Layout(width="200px"),
            )
            txt.observe(self._make_arg_updater(idx, key), names="value")
            arg_rows.append(w.HBox([lbl, txt]))

        return w.VBox(
            [
                w.HBox([header, w.HBox([up_btn, dn_btn, rm_btn])]),
                w.VBox(arg_rows),
            ],
            layout=w.Layout(
                border="1px solid #e0e0e0",
                border_radius="6px",
                padding="8px",
                margin="4px 0",
            ),
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_add(self, _btn: Any) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            name = self._template_dropdown.value
            defaults = self._library._templates[name]["args"]
            args = {k: ("" if v is None else str(v)) for k, v in defaults.items()}
            self._steps.append({"template_name": name, "args": args})
            self._refresh()
        finally:
            self._busy = False

    def _on_save(self, _btn: Any) -> None:
        name = self._name_input.value.strip()
        if not name:
            self._status_lbl.value = "Flow name required."
            return

        flow_steps = [
            {
                "template": step["template_name"],
                "args": {k: v for k, v in step["args"].items() if v != ""},
            }
            for step in self._steps
        ]

        existing: dict[str, Any] = {}
        if self._flows_path is not None and self._flows_path.exists():
            existing = yaml.safe_load(
                self._flows_path.read_text(encoding="utf-8")
            ) or {}

        existing.setdefault("flows", {})[name] = flow_steps

        if self._flows_path is not None:
            self._flows_path.write_text(
                yaml.dump(existing, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        self._status_lbl.value = f"Saved '{name}'."

    def _load_initial_flow(self) -> None:
        if self._flows_path is None or not self._flows_path.exists():
            return

        payload = yaml.safe_load(self._flows_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            return

        flows = payload.get("flows")
        if not isinstance(flows, dict):
            return

        # Auto-load when exactly one flow exists to avoid ambiguous selection.
        if len(flows) != 1:
            return

        flow_name, flow_steps = next(iter(flows.items()))
        if not isinstance(flow_steps, list):
            return

        loaded_steps: list[dict[str, Any]] = []
        for step in flow_steps:
            if not isinstance(step, dict):
                continue
            template_name = step.get("template")
            if not isinstance(template_name, str):
                continue
            if template_name not in self._library._templates:
                continue
            args = step.get("args", {})
            if not isinstance(args, dict):
                args = {}
            loaded_steps.append(
                {
                    "template_name": template_name,
                    "args": {str(k): str(v) for k, v in args.items()},
                }
            )

        self._steps = loaded_steps
        self._name_input.value = str(flow_name)
        self._refresh()

    def _make_remove_handler(self, idx: int):
        def _remove(_btn: Any) -> None:
            self._steps.pop(idx)
            self._refresh()
        return _remove

    def _make_up_handler(self, idx: int):
        def _up(_btn: Any) -> None:
            if idx > 0:
                self._steps[idx - 1], self._steps[idx] = (
                    self._steps[idx],
                    self._steps[idx - 1],
                )
                self._refresh()
        return _up

    def _make_down_handler(self, idx: int):
        def _dn(_btn: Any) -> None:
            if idx < len(self._steps) - 1:
                self._steps[idx], self._steps[idx + 1] = (
                    self._steps[idx + 1],
                    self._steps[idx],
                )
                self._refresh()
        return _dn

    def _make_arg_updater(self, idx: int, key: str):
        def _update(change: Any) -> None:
            self._steps[idx]["args"][key] = change["new"]
            self._render_diagram()
        return _update

    # ------------------------------------------------------------------
    # Diagram rendering
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._flow_box.children = tuple(
            self._build_step_row(i) for i in range(len(self._steps))
        )
        self._render_diagram()

    def _render_diagram(self) -> None:
        rendered = self._resolve_rendered()
        diagram = flow_to_mermaid(rendered)
        html_content = mermaid_html(diagram)
        self._diagram_out.outputs = (
            {
                "output_type": "display_data",
                "data": {"text/html": html_content, "text/plain": diagram},
                "metadata": {},
            },
        )

    def _resolve_rendered(self) -> list[dict[str, Any]]:
        results = []
        for step in self._steps:
            args = {k: (v if v != "" else None) for k, v in step["args"].items()}
            try:
                rendered = self._library.render(
                    template_name=step["template_name"],
                    context_args={},
                    explicit_args=args,
                )
            except Exception:
                template = self._library._templates[step["template_name"]]
                rendered = {
                    "method": template["interaction"].get("method", "?"),
                    "path": template["interaction"].get("path", "?"),
                    "response": {"status": "?", "body": None},
                }
            results.append(rendered)
        return results
