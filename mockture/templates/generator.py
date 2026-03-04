"""Fluent template generator from OpenAPI specs."""

from __future__ import annotations

import json
import re
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from mockture.errors import ContractConfigError


class TemplateGenerator:
    """Generate Mockture templates from OpenAPI contracts."""

    def __init__(self, contract_path: str) -> None:
        self._contract_path = Path(contract_path)
        self._spec = self._load_spec()
        self._templates: dict[str, dict[str, Any]] = {}

    def path(self, path_value: str) -> "PathBuilder":
        return PathBuilder(generator=self, path_value=path_value)

    def all(self) -> "GlobalAllBuilder":
        return GlobalAllBuilder(generator=self)

    def save(self, output_path: str, verbose: bool = False) -> "TemplateGenerator":
        target = Path(output_path)
        payload = {"templates": self._templates}
        target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        if verbose:
            print(f"Generated {len(self._templates)} templates into {target}")
            print(", ".join(self._templates.keys()))
        return self

    def templates(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._templates)

    def _register_template(self, name: str, template: dict[str, Any]) -> None:
        if name in self._templates:
            raise ContractConfigError(
                f"Duplicate template name '{name}'. "
                "Hint: use unique template names across all builder calls."
            )
        self._templates[name] = template

    def _operation(self, path_value: str, method: str) -> dict[str, Any]:
        paths = self._spec.get("paths", {})
        if path_value not in paths:
            raise ContractConfigError(
                f"Path '{path_value}' not found in '{self._contract_path}'. "
                "Hint: use a path declared in the OpenAPI spec."
            )
        path_item = paths[path_value]
        method_lower = method.lower()
        if method_lower not in path_item:
            raise ContractConfigError(
                f"Method '{method.upper()}' not found for path '{path_value}'. "
                "Hint: use a declared method for this path."
            )
        operation = path_item[method_lower]
        if not isinstance(operation, dict):
            raise ContractConfigError(
                f"Invalid operation shape for '{method.upper()} {path_value}'. "
                "Hint: operation must be an object."
            )
        return operation

    def _response_schema(self, path_value: str, method: str, status_code: int) -> dict[str, Any]:
        operation = self._operation(path_value, method)
        responses = operation.get("responses")
        if not isinstance(responses, dict):
            raise ContractConfigError(
                f"No responses object for '{method.upper()} {path_value}'. "
                "Hint: declare responses in the OpenAPI spec."
            )
        status_key = str(status_code)
        if status_key not in responses:
            raise ContractConfigError(
                f"Status code '{status_code}' not declared for '{method.upper()} {path_value}'. "
                "Hint: choose a status code defined in the spec."
            )
        response = responses[status_key]
        if not isinstance(response, dict):
            raise ContractConfigError(
                f"Response for status '{status_code}' is invalid. "
                "Hint: response entries must be objects."
            )
        content = response.get("content", {})
        media = content.get("application/json", {})
        schema = media.get("schema")
        if not isinstance(schema, dict):
            raise ContractConfigError(
                f"No application/json schema for '{method.upper()} {path_value} {status_code}'. "
                "Hint: define an application/json response schema."
            )
        return self._resolve_schema(schema)

    def _resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "$ref" not in schema:
            return deepcopy(schema)
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise ContractConfigError(
                f"Unsupported $ref '{ref}' in '{self._contract_path}'. "
                "Hint: only local refs are supported."
            )
        current: Any = self._spec
        for token in ref.removeprefix("#/").split("/"):
            if not isinstance(current, dict) or token not in current:
                raise ContractConfigError(
                    f"Unable to resolve ref '{ref}' in '{self._contract_path}'. "
                    "Hint: ensure components exist."
                )
            current = current[token]
        if not isinstance(current, dict):
            raise ContractConfigError(
                f"Resolved schema for '{ref}' is invalid. Hint: referenced schema must be an object."
            )
        return deepcopy(current)

    def _build_inferred_template(
        self,
        template_name: str,
        path_value: str,
        method: str,
        status_code: int,
        explicit_params: dict[str, Any],
    ) -> dict[str, Any]:
        schema = self._response_schema(path_value=path_value, method=method, status_code=status_code)
        if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
            raise ContractConfigError(
                f"Response schema for '{method.upper()} {path_value} {status_code}' must be an object. "
                "Hint: use custom(...) for non-object payloads."
            )

        body: dict[str, Any] = {}
        args: dict[str, Any] = {"status_code": status_code}
        properties: dict[str, Any] = schema["properties"]

        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            args[field_name] = _default_value(field_name=field_name, field_schema=field_schema)
            body[field_name] = f"{{{field_name}}}"

        args.update(explicit_params)

        return {
            "args": args,
            "interaction": {
                "method": method.upper(),
                "path": path_value,
                "response": {
                    "status": "{status_code}",
                    "body": body,
                },
            },
        }

    def _build_custom_template(
        self,
        path_value: str,
        method: str,
        status_code: int,
        body: dict[str, Any],
        explicit_params: dict[str, Any],
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"status_code": status_code}
        args.update(explicit_params)
        return {
            "args": args,
            "interaction": {
                "method": method.upper(),
                "path": path_value,
                "response": {
                    "status": "{status_code}",
                    "body": deepcopy(body),
                },
            },
        }

    def _response_codes(self, path_value: str, method: str) -> list[int]:
        operation = self._operation(path_value=path_value, method=method)
        responses = operation.get("responses")
        if not isinstance(responses, dict):
            return []
        codes: list[int] = []
        for key in responses:
            if key.isdigit():
                codes.append(int(key))
        return sorted(codes)

    def _load_spec(self) -> dict[str, Any]:
        if not self._contract_path.exists():
            raise ContractConfigError(
                f"Contract file '{self._contract_path}' does not exist. "
                "Hint: pass a valid OpenAPI path."
            )
        raw = self._contract_path.read_text(encoding="utf-8")
        try:
            if self._contract_path.suffix.lower() == ".json":
                data = json.loads(raw)
            else:
                data = yaml.safe_load(raw)
        except Exception as exc:
            raise ContractConfigError(
                f"Failed to parse '{self._contract_path}'. Hint: check YAML/JSON syntax."
            ) from exc
        if not isinstance(data, dict) or "paths" not in data:
            raise ContractConfigError(
                f"Invalid OpenAPI file '{self._contract_path}'. Hint: top-level 'paths' is required."
            )
        return data


class PathBuilder:
    """Path-level builder."""

    def __init__(self, generator: TemplateGenerator, path_value: str) -> None:
        self._generator = generator
        self._path_value = path_value

    def method(self, method_value: str) -> "MethodBuilder":
        return MethodBuilder(
            generator=self._generator,
            path_value=self._path_value,
            method_value=method_value,
        )


class MethodBuilder:
    """Method-level builder with optional params."""

    def __init__(self, generator: TemplateGenerator, path_value: str, method_value: str) -> None:
        self._generator = generator
        self._path_value = path_value
        self._method_value = method_value
        self._params: dict[str, Any] = {}

    def params(self, **kwargs: Any) -> "MethodBuilder":
        self._params.update(kwargs)
        return self

    def response(self, template_name: str, status_code: int) -> "SingleTemplateBuilder":
        """Build an inferred template for the given status code."""
        template = self._generator._build_inferred_template(
            template_name=template_name,
            path_value=self._path_value,
            method=self._method_value,
            status_code=status_code,
            explicit_params=self._params,
        )
        return SingleTemplateBuilder(self._generator, template_name, template)

    def custom(
        self,
        template_name: str,
        status_code: int,
        body: dict[str, Any],
    ) -> "SingleTemplateBuilder":
        template = self._generator._build_custom_template(
            path_value=self._path_value,
            method=self._method_value,
            status_code=status_code,
            body=body,
            explicit_params=self._params,
        )
        return SingleTemplateBuilder(self._generator, template_name, template)

    def all(self) -> "MultiTemplateBuilder":
        template_entries: list[tuple[str, dict[str, Any]]] = []
        for code in self._generator._response_codes(path_value=self._path_value, method=self._method_value):
            category = "success" if code < 400 else "failure"
            name = _auto_template_name(
                path_value=self._path_value,
                method=self._method_value,
                status_code=code,
                category=category,
            )
            try:
                template = self._generator._build_inferred_template(
                    template_name=name,
                    path_value=self._path_value,
                    method=self._method_value,
                    status_code=code,
                    explicit_params=self._params,
                )
                template_entries.append((name, template))
            except ContractConfigError as exc:
                warnings.warn(
                    f"Skipping template '{name}' for "
                    f"{self._method_value.upper()} {self._path_value} {code}: {exc}",
                    stacklevel=3,
                )
        return MultiTemplateBuilder(generator=self._generator, templates=template_entries)


class SingleTemplateBuilder:
    """Builder wrapper for one template entry."""

    def __init__(
        self,
        generator: TemplateGenerator,
        template_name: str,
        template: dict[str, Any],
    ) -> None:
        self._generator = generator
        self._template_name = template_name
        self._template = template

    def to_template(self) -> TemplateGenerator:
        self._generator._register_template(self._template_name, self._template)
        return self._generator


class MultiTemplateBuilder:
    """Builder wrapper for multiple template entries."""

    def __init__(
        self,
        generator: TemplateGenerator,
        templates: list[tuple[str, dict[str, Any]]],
    ) -> None:
        self._generator = generator
        self._templates = templates

    def to_templates(self) -> TemplateGenerator:
        for name, template in self._templates:
            self._generator._register_template(name, template)
        return self._generator


class GlobalAllBuilder:
    """Generate templates for all paths/methods/responses."""

    def __init__(self, generator: TemplateGenerator) -> None:
        self._generator = generator

    def to_templates(self) -> TemplateGenerator:
        paths = self._generator._spec.get("paths", {})
        for path_value, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method_value, operation in path_item.items():
                if method_value.lower() not in {
                    "get", "post", "put", "patch", "delete", "head", "options", "trace",
                }:
                    continue
                if not isinstance(operation, dict):
                    continue
                builder = MethodBuilder(
                    generator=self._generator,
                    path_value=path_value,
                    method_value=method_value,
                )
                builder.all().to_templates()
        return self._generator


def _default_value(field_name: str, field_schema: dict[str, Any]) -> Any:
    """Infer a default value from schema — no domain-specific overrides."""
    if "example" in field_schema:
        return field_schema["example"]
    if "default" in field_schema:
        return field_schema["default"]
    if isinstance(field_schema.get("enum"), list) and field_schema["enum"]:
        return field_schema["enum"][0]
    schema_type = field_schema.get("type")
    if schema_type == "string":
        return ""
    if schema_type in {"integer", "number"}:
        return 0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        return []
    if schema_type == "object":
        return {}
    return None


def _auto_template_name(path_value: str, method: str, status_code: int, category: str) -> str:
    normalized_path = re.sub(r"{([^{}]+)}", r"\1", path_value).strip("/")
    normalized_path = normalized_path.replace("/", "_").replace("-", "_")
    if not normalized_path:
        normalized_path = "root"
    return f"{method.lower()}_{normalized_path}_{category}_{status_code}"
