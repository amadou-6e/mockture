"""respond(...) normalization utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mockture.errors import ScenarioFormatError
from mockture.templates.library import TemplateLibrary


def normalize_respond_input(
    first_arg: str | dict[str, Any],
    kwargs: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(first_arg, dict):
        if kwargs:
            raise ScenarioFormatError(
                "respond(dict) does not accept extra keyword arguments. "
                "Hint: include all args inside the dict payload."
            )
        return TemplateLibrary.normalize_scenario_payload(first_arg)

    scenario_path = Path(first_arg)
    if scenario_path.exists() and scenario_path.is_file():
        if kwargs:
            raise ScenarioFormatError(
                "respond(path) does not accept extra keyword arguments. "
                "Hint: put all values in the scenario file."
            )
        raw = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        if raw is None:
            raw = {}
        return TemplateLibrary.normalize_scenario_payload(raw)

    return [(first_arg, kwargs)]
