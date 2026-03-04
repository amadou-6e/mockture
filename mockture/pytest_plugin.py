"""Pytest plugin for marker-driven Mockture setup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from mockture.server import Mockture


def use_mockture(*args: Any, **kwargs: Any) -> pytest.MarkDecorator:
    """Alias for pytest.mark.mockture(...)."""
    return pytest.mark.mockture(*args, **kwargs)


_VALID_SCOPES = {"function", "module", "session"}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "mockture_contract",
        "Default OpenAPI contract path for @pytest.mark.mockture",
        default="",
    )
    parser.addini(
        "mockture_templates",
        "Default template library path for @pytest.mark.mockture",
        default="",
    )
    parser.addini(
        "mockture_flows",
        "Default named flow registry path for @pytest.mark.mockture",
        default="",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        (
            "mockture([flow_name|sequence|scenario], contract=None, templates=None, "
            "scenario=None, sequence=None, flow=None, "
            "flows_path=None, scope='function', strict=True, host='127.0.0.1', "
            "port=0, auto_start=True): configure and start Mockture for the test."
        ),
    )


@pytest.fixture(scope="module")
def _mockture_module_pool() -> Any:
    pool: dict[tuple[str, str, bool, str, int], Mockture] = {}
    try:
        yield pool
    finally:
        for mock in pool.values():
            mock.stop()


@pytest.fixture(scope="session")
def _mockture_session_pool() -> Any:
    pool: dict[tuple[str, str, bool, str, int], Mockture] = {}
    try:
        yield pool
    finally:
        for mock in pool.values():
            mock.stop()


@pytest.fixture(autouse=True)
def _mockture_autouse(
    request: pytest.FixtureRequest,
    _mockture_module_pool: dict[tuple[str, str, bool, str, int], Mockture],
    _mockture_session_pool: dict[tuple[str, str, bool, str, int], Mockture],
) -> Any:
    marker = request.node.get_closest_marker("mockture")
    if marker is None:
        request.node._mockture_instance = None
        yield
        return

    config = _build_marker_config(request=request, marker=marker)
    mock, owned = _resolve_mock_instance(
        request=request,
        config=config,
        module_pool=_mockture_module_pool,
        session_pool=_mockture_session_pool,
    )
    _register_marker_behavior(mock=mock, config=config)

    request.node._mockture_instance = mock
    try:
        yield
    finally:
        request.node._mockture_instance = None
        if owned:
            mock.stop()


@pytest.fixture
def mockture(request: pytest.FixtureRequest) -> Mockture:
    instance = getattr(request.node, "_mockture_instance", None)
    if instance is None:
        raise pytest.UsageError(
            "Fixture 'mockture' requires @pytest.mark.mockture(...) on the test."
        )
    return instance


def _build_marker_config(
    request: pytest.FixtureRequest,
    marker: pytest.Mark,
) -> dict[str, Any]:
    positional = _parse_marker_positional(marker=marker)
    kwargs = dict(marker.kwargs)

    contract = kwargs.get("contract") or request.config.getini("mockture_contract")
    templates = kwargs.get("templates") or request.config.getini("mockture_templates")
    if not isinstance(contract, str) or not contract:
        raise pytest.UsageError(
            "@pytest.mark.mockture requires 'contract' or [tool.pytest.ini_options].mockture_contract."
        )
    if not isinstance(templates, str) or not templates:
        raise pytest.UsageError(
            "@pytest.mark.mockture requires 'templates' or [tool.pytest.ini_options].mockture_templates."
        )

    scope = str(kwargs.get("scope", "function"))
    if scope not in _VALID_SCOPES:
        raise pytest.UsageError(
            "@pytest.mark.mockture 'scope' must be one of function, module, session."
        )

    strict = bool(kwargs.get("strict", True))
    host = str(kwargs.get("host", "127.0.0.1"))
    port = int(kwargs.get("port", 0))
    auto_start = bool(kwargs.get("auto_start", True))

    scenario = kwargs.get("scenario", positional.get("scenario"))
    if isinstance(scenario, str):
        scenario = str(_resolve_path(request=request, raw_path=scenario))

    flows_path = kwargs.get("flows_path") or request.config.getini("mockture_flows")
    if isinstance(flows_path, str):
        if flows_path:
            flows_path = str(_resolve_path(request=request, raw_path=flows_path))
        else:
            flows_path = str(_derive_default_flows_path(templates_path=templates, request=request))
    elif flows_path is None:
        flows_path = str(_derive_default_flows_path(templates_path=templates, request=request))

    return {
        "contract": str(_resolve_path(request=request, raw_path=contract)),
        "templates": str(_resolve_path(request=request, raw_path=templates)),
        "scenario": scenario,
        "sequence": kwargs.get("sequence", positional.get("sequence")),
        "flow": kwargs.get("flow", positional.get("flow")),
        "flows_path": flows_path,
        "scope": scope,
        "strict": strict,
        "host": host,
        "port": port,
        "auto_start": auto_start,
    }


def _parse_marker_positional(marker: pytest.Mark) -> dict[str, Any]:
    if not marker.args:
        return {}
    if len(marker.args) > 1:
        raise pytest.UsageError(
            "@pytest.mark.mockture accepts at most one positional argument."
        )

    value = marker.args[0]
    if isinstance(value, str):
        return {"flow": value}
    if isinstance(value, list):
        return {"sequence": value}
    if isinstance(value, dict):
        return {"scenario": value}
    raise pytest.UsageError(
        "@pytest.mark.mockture positional arg must be flow name (str), sequence (list), or scenario (dict)."
    )


def _resolve_mock_instance(
    request: pytest.FixtureRequest,
    config: dict[str, Any],
    module_pool: dict[tuple[str, str, bool, str, int], Mockture],
    session_pool: dict[tuple[str, str, bool, str, int], Mockture],
) -> tuple[Mockture, bool]:
    key = (
        config["contract"],
        config["templates"],
        config["strict"],
        config["host"],
        config["port"],
    )
    scope = config["scope"]

    if scope == "function":
        mock = _create_mock(config=config)
        if config["auto_start"]:
            mock.start()
        return mock, True

    if scope == "module":
        if key not in module_pool:
            module_pool[key] = _create_mock(config=config)
            if config["auto_start"]:
                module_pool[key].start()
        return module_pool[key], False

    if key not in session_pool:
        session_pool[key] = _create_mock(config=config)
        if config["auto_start"]:
            session_pool[key].start()
    return session_pool[key], False


def _create_mock(config: dict[str, Any]) -> Mockture:
    return Mockture(
        contract_path=config["contract"],
        templates_path=config["templates"],
        strict=config["strict"],
        host=config["host"],
        port=config["port"],
    )


def _register_marker_behavior(mock: Mockture, config: dict[str, Any]) -> None:
    scenario = config.get("scenario")
    if scenario is not None:
        mock.respond(scenario)

    sequence = config.get("sequence")
    if sequence is not None:
        _register_sequence(mock=mock, sequence=sequence)

    flow = config.get("flow")
    if flow is not None:
        _register_named_flow(
            mock=mock,
            flow_name=str(flow),
            flows_path=str(config["flows_path"]),
        )


def _register_sequence(mock: Mockture, sequence: Any) -> None:
    if not isinstance(sequence, list):
        raise pytest.UsageError(
            "@pytest.mark.mockture 'sequence' must be a list."
        )

    for entry in sequence:
        if isinstance(entry, str):
            mock.respond(entry)
            continue

        if isinstance(entry, dict) and "template" in entry:
            template = entry.get("template")
            args = entry.get("args", {})
            if not isinstance(template, str) or not isinstance(args, dict):
                raise pytest.UsageError(
                    "Sequence dict entries must use {template: str, args: dict}."
                )
            mock.respond(template, **args)
            continue

        if isinstance(entry, dict):
            mock.respond(entry)
            continue

        raise pytest.UsageError(
            "Unsupported sequence entry. Use template name strings or mapping entries."
        )


def _register_named_flow(mock: Mockture, flow_name: str, flows_path: str) -> None:
    flow_file = Path(flows_path)
    if not flow_file.exists():
        raise pytest.UsageError(
            f"Flow file '{flow_file}' does not exist for flow '{flow_name}'."
        )

    raw = yaml.safe_load(flow_file.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise pytest.UsageError(
            f"Flow file '{flow_file}' must contain a mapping."
        )

    flows = raw.get("flows")
    if isinstance(flows, dict):
        registry = flows
    else:
        registry = raw

    if flow_name not in registry:
        raise pytest.UsageError(
            f"Flow '{flow_name}' not found in '{flow_file}'."
        )

    _apply_flow_entry(mock=mock, entry=registry[flow_name], flow_name=flow_name)


def _apply_flow_entry(mock: Mockture, entry: Any, flow_name: str) -> None:
    if isinstance(entry, str):
        mock.respond(entry)
        return

    if isinstance(entry, list):
        _register_sequence(mock=mock, sequence=entry)
        return

    if isinstance(entry, dict) and "sequence" in entry:
        _register_sequence(mock=mock, sequence=entry["sequence"])
        return

    if isinstance(entry, dict):
        mock.respond(entry)
        return

    raise pytest.UsageError(
        f"Flow '{flow_name}' has unsupported shape."
    )


def _derive_default_flows_path(templates_path: str, request: pytest.FixtureRequest) -> Path:
    templates = _resolve_path(request=request, raw_path=templates_path)
    name = templates.name
    if name.endswith(".templates.yml"):
        return Path(templates.parent, name.replace(".templates.yml", ".flows.yml"))
    if name.endswith(".templates.yaml"):
        return Path(templates.parent, name.replace(".templates.yaml", ".flows.yaml"))
    return Path(templates.parent, f"{templates.stem}.flows.yml")


def _resolve_path(request: pytest.FixtureRequest, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate

    node_path = Path(str(request.node.path))
    base = node_path.parent
    from_test_dir = Path(base, candidate)
    if from_test_dir.exists():
        return from_test_dir

    return Path.cwd().joinpath(candidate)
