"""OpenAPI contract validation adapter."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema import ValidationError

from mockture.errors import ContractConfigError
from mockture.errors import ContractRuntimeError


class OpenAPIContractValidator:
    """Minimal OpenAPI adapter for config-time and runtime schema checks."""

    def __init__(self, contract_path: str) -> None:
        self._contract_path = Path(contract_path)
        self._spec = self._load_contract()
        self._paths = self._spec.get("paths", {})

    def validate_config_interaction(
        self,
        method: str,
        path: str,
        status_code: int,
        response_body: Any,
    ) -> None:
        operation = self._operation_for(method, path, config_time=True)
        response = self._response_for(operation, status_code, method, path, config_time=True)
        schema = self._json_schema_from_response(response)
        if schema is None:
            return
        self._validate_schema(
            schema=schema,
            value=response_body,
            method=method,
            path=path,
            status_code=status_code,
            runtime=False,
        )

    def validate_request(self, method: str, path: str, json_body: Any) -> None:
        operation = self._operation_for(method, path, config_time=False)
        schema = self._request_schema(operation)
        if schema is None:
            return
        self._validate_schema(
            schema=schema,
            value=json_body if json_body is not None else {},
            method=method,
            path=path,
            runtime=True,
            location="request",
        )

    def validate_response(
        self,
        method: str,
        path: str,
        status_code: int,
        response_body: Any,
    ) -> None:
        operation = self._operation_for(method, path, config_time=False)
        response = self._response_for(
            operation=operation,
            status_code=status_code,
            method=method,
            path=path,
            config_time=False,
        )
        schema = self._json_schema_from_response(response)
        if schema is None:
            return
        self._validate_schema(
            schema=schema,
            value=response_body,
            method=method,
            path=path,
            status_code=status_code,
            runtime=True,
            location="response",
        )

    def _load_contract(self) -> dict[str, Any]:
        if not self._contract_path.exists():
            raise ContractConfigError(
                f"Contract file '{self._contract_path}' does not exist. "
                "Hint: pass a valid OpenAPI YAML/JSON path."
            )
        raw = self._contract_path.read_text(encoding="utf-8")
        try:
            if self._contract_path.suffix.lower() == ".json":
                spec = json.loads(raw)
            else:
                spec = yaml.safe_load(raw)
        except Exception as exc:
            raise ContractConfigError(
                f"Failed to parse contract '{self._contract_path}'. "
                "Hint: check YAML/JSON syntax."
            ) from exc

        if not isinstance(spec, dict) or "paths" not in spec:
            raise ContractConfigError(
                f"Invalid OpenAPI contract '{self._contract_path}'. "
                "Hint: ensure a top-level 'paths' object exists."
            )
        return spec

    def _operation_for(self, method: str, path: str, config_time: bool) -> dict[str, Any]:
        method_lower = method.lower()
        path_item = self._path_item(path, method, config_time)
        if method_lower not in path_item:
            message = (
                f"Method '{method.upper()}' for path '{path}' is not declared in contract. "
                "Hint: configure a declared method or update contract."
            )
            if config_time:
                raise ContractConfigError(message)
            raise ContractRuntimeError(message)
        operation = path_item[method_lower]
        if not isinstance(operation, dict):
            message = (
                f"Operation '{method.upper()} {path}' has invalid contract shape. "
                "Hint: operation entry must be an object."
            )
            if config_time:
                raise ContractConfigError(message)
            raise ContractRuntimeError(message)
        return operation

    def _path_item(self, concrete_path: str, method: str, config_time: bool) -> dict[str, Any]:
        if concrete_path in self._paths:
            item = self._paths[concrete_path]
            if isinstance(item, dict):
                return item

        for template_path, item in self._paths.items():
            if not isinstance(item, dict):
                continue
            if _path_matches(template_path, concrete_path):
                return item

        message = (
            f"Path '{concrete_path}' is not declared in contract for method "
            f"'{method.upper()}'. Hint: configure a declared path."
        )
        if config_time:
            raise ContractConfigError(message)
        raise ContractRuntimeError(message)

    def _response_for(
        self,
        operation: dict[str, Any],
        status_code: int,
        method: str,
        path: str,
        config_time: bool,
    ) -> dict[str, Any]:
        responses = operation.get("responses")
        if not isinstance(responses, dict):
            message = (
                f"Operation '{method.upper()} {path}' has no valid responses object. "
                "Hint: declare responses in contract."
            )
            if config_time:
                raise ContractConfigError(message)
            raise ContractRuntimeError(message)

        status_key = str(status_code)
        if status_key in responses:
            response = responses[status_key]
        elif "default" in responses:
            response = responses["default"]
        else:
            message = (
                f"Status code '{status_code}' is not declared for '{method.upper()} {path}'. "
                "Hint: configure a declared status code."
            )
            if config_time:
                raise ContractConfigError(message)
            raise ContractRuntimeError(message)

        if not isinstance(response, dict):
            message = (
                f"Response entry for '{method.upper()} {path} {status_code}' is invalid. "
                "Hint: response must be an object."
            )
            if config_time:
                raise ContractConfigError(message)
            raise ContractRuntimeError(message)
        return response

    def _request_schema(self, operation: dict[str, Any]) -> dict[str, Any] | None:
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            return None
        content = request_body.get("content")
        if not isinstance(content, dict):
            return None
        media = content.get("application/json")
        if not isinstance(media, dict):
            return None
        schema = media.get("schema")
        if not isinstance(schema, dict):
            return None
        return self._deref_schema(schema)

    def _json_schema_from_response(self, response: dict[str, Any]) -> dict[str, Any] | None:
        content = response.get("content")
        if not isinstance(content, dict):
            return None
        media = content.get("application/json")
        if not isinstance(media, dict):
            return None
        schema = media.get("schema")
        if not isinstance(schema, dict):
            return None
        return self._deref_schema(schema)

    def _deref_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        clone = deepcopy(schema)
        if "$ref" in clone:
            ref = clone["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#/"):
                raise ContractConfigError(
                    f"Unsupported schema ref '{ref}' in '{self._contract_path}'. "
                    "Hint: only local #/ refs are supported in MVP."
                )
            target = deepcopy(self._resolve_ref(ref))
            siblings = {key: value for key, value in clone.items() if key != "$ref"}
            merged = {**target, **siblings}
            return self._deref_schema(merged)

        for key, value in list(clone.items()):
            if isinstance(value, dict):
                clone[key] = self._deref_schema(value)
            elif isinstance(value, list):
                clone[key] = [
                    self._deref_schema(item) if isinstance(item, dict) else item
                    for item in value
                ]
        return clone

    def _resolve_ref(self, ref: str) -> Any:
        current: Any = self._spec
        tokens = ref.removeprefix("#/").split("/")
        for token in tokens:
            if not isinstance(current, dict) or token not in current:
                raise ContractConfigError(
                    f"Cannot resolve ref '{ref}' in '{self._contract_path}'. "
                    "Hint: ensure referenced schema exists."
                )
            current = current[token]
        return current

    def _validate_schema(
        self,
        schema: dict[str, Any],
        value: Any,
        method: str,
        path: str,
        status_code: int | None = None,
        runtime: bool = False,
        location: str = "response",
    ) -> None:
        try:
            Draft202012Validator(schema).validate(value)
        except ValidationError as exc:
            if runtime:
                if location == "request":
                    raise ContractRuntimeError(
                        f"Request contract violation for '{method.upper()} {path}': "
                        f"{exc.message}. Hint: send request payload matching schema."
                    ) from exc
                raise ContractRuntimeError(
                    f"Response contract violation for '{method.upper()} {path}' "
                    f"status '{status_code}': {exc.message}. "
                    "Hint: configure response body matching schema."
                ) from exc
            raise ContractConfigError(
                f"Configured response violates contract for '{method.upper()} {path}' "
                f"status '{status_code}': {exc.message}. "
                "Hint: adjust template response body to match schema."
            ) from exc


def _path_matches(template_path: str, concrete_path: str) -> bool:
    escaped = re.escape(template_path)
    pattern = re.sub(r"\\\{[^{}]+\\\}", r"[^/]+", escaped)
    return re.fullmatch(pattern, concrete_path) is not None
