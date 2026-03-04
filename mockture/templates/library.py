"""Template loading and rendering."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from mockture.templates.directives import expand_body_directives
from mockture.errors import ScenarioFormatError
from mockture.errors import TemplateArgsError
from mockture.errors import TemplateNotFoundError


class TemplateLibrary:
    """In-memory template collection parsed from templates.yml."""

    def __init__(self, templates_path: str) -> None:
        self._templates_path = Path(templates_path)
        self._templates = self._load_templates()

    def has_template(self, name: str) -> bool:
        return name in self._templates

    def render(
        self,
        template_name: str,
        context_args: dict[str, Any] | None,
        explicit_args: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if template_name not in self._templates:
            raise TemplateNotFoundError(
                f"Template '{template_name}' not found in '{self._templates_path}'. "
                "Hint: verify template name and templates file."
            )

        template = self._templates[template_name]
        defaults = deepcopy(template["args"])
        merged = self._merge_args(defaults, context_args or {}, explicit_args or {})
        self._validate_required_args(template_name, defaults, merged)

        interaction = deepcopy(template["interaction"])
        rendered = self._interpolate(interaction, merged, template_name)

        response = rendered.get("response", {})
        if "body" in response:
            response["body"] = expand_body_directives(response["body"], merged, rendered["path"])
        if "status" in response:
            response["status"] = int(response["status"])

        return rendered

    @staticmethod
    def normalize_scenario_payload(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        if not isinstance(payload, dict):
            raise ScenarioFormatError(
                "Scenario payload must be a mapping of template->args. "
                "Hint: use {template_name: {arg: value}} format."
            )

        invocations: list[tuple[str, dict[str, Any]]] = []
        for template_name, args_value in payload.items():
            if isinstance(args_value, list):
                for entry in args_value:
                    if not isinstance(entry, dict):
                        raise ScenarioFormatError(
                            f"Scenario entry for '{template_name}' must be a mapping. "
                            "Hint: list entries must be objects."
                        )
                    invocations.append((template_name, entry))
                continue

            if args_value is None:
                invocations.append((template_name, {}))
                continue

            if not isinstance(args_value, dict):
                raise ScenarioFormatError(
                    f"Scenario entry for '{template_name}' must be a mapping or list. "
                    "Hint: use {} for defaults-only template invocation."
                )
            invocations.append((template_name, args_value))

        return invocations

    def _load_templates(self) -> dict[str, dict[str, Any]]:
        if not self._templates_path.exists():
            raise TemplateNotFoundError(
                f"Templates file '{self._templates_path}' does not exist. "
                "Hint: pass a valid templates_path."
            )

        raw = yaml.safe_load(self._templates_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "templates" not in raw:
            raise ScenarioFormatError(
                f"Invalid templates file '{self._templates_path}'. "
                "Hint: top-level key must be 'templates'."
            )

        templates = raw["templates"]
        if not isinstance(templates, dict):
            raise ScenarioFormatError(
                f"Invalid templates file '{self._templates_path}'. "
                "Hint: 'templates' must map names to template objects."
            )

        normalized: dict[str, dict[str, Any]] = {}
        for name, template in templates.items():
            if not isinstance(template, dict):
                raise ScenarioFormatError(
                    f"Template '{name}' must be a mapping. "
                    "Hint: include 'args' and 'interaction' keys."
                )
            args = template.get("args", {})
            interaction = template.get("interaction")
            if not isinstance(args, dict) or not isinstance(interaction, dict):
                raise ScenarioFormatError(
                    f"Template '{name}' has invalid structure. "
                    "Hint: 'args' and 'interaction' must be mappings."
                )
            normalized[name] = {"args": args, "interaction": interaction}
        return normalized

    @staticmethod
    def _merge_args(
        defaults: dict[str, Any],
        context_args: dict[str, Any],
        explicit_args: dict[str, Any],
    ) -> dict[str, Any]:
        merged = deepcopy(defaults)
        merged.update(context_args)
        merged.update(explicit_args)
        return merged

    @staticmethod
    def _validate_required_args(
        template_name: str,
        defaults: dict[str, Any],
        merged: dict[str, Any],
    ) -> None:
        missing: list[str] = []
        for key, default in defaults.items():
            if default is None and merged.get(key) is None:
                missing.append(key)

        if missing:
            joined = ", ".join(missing)
            raise TemplateArgsError(
                f"Template '{template_name}' missing required args: {joined}. "
                "Hint: provide values in context or respond(...)."
            )

    def _interpolate(self, value: Any, args: dict[str, Any], template_name: str) -> Any:
        if isinstance(value, str):
            try:
                return value.format_map(args)
            except KeyError as exc:
                missing = str(exc).strip("'")
                raise TemplateArgsError(
                    f"Template '{template_name}' missing interpolation arg '{missing}'. "
                    "Hint: provide all placeholders used by interaction."
                ) from exc
        if isinstance(value, list):
            return [self._interpolate(item, args, template_name) for item in value]
        if isinstance(value, dict):
            return {
                key: self._interpolate(item, args, template_name)
                for key, item in value.items()
            }
        return value
