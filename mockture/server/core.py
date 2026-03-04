"""Core Mockture server implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from typing import TYPE_CHECKING

from mockture.server.assertions import CallRecord
from mockture.server.assertions import CallView
from mockture.server.context import MocktureContext
from mockture.contract import OpenAPIContractValidator
from mockture.errors import ContractRuntimeError
from mockture.errors import MocktureError
from mockture.templates import normalize_respond_input
from mockture.templates import TemplateLibrary

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer


@dataclass
class _Interaction:
    template_name: str
    method: str
    path: str
    status_code: int
    body: Any
    headers: dict[str, str]


class Mockture:
    """Configurable contract-aware in-process HTTP mock server."""

    def __init__(
        self,
        contract_path: str,
        templates_path: str,
        strict: bool = True,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self._strict = strict
        self._host = host
        self._port = port

        self._templates = TemplateLibrary(templates_path=templates_path)
        self._contract = OpenAPIContractValidator(contract_path=contract_path)

        self._httpserver: HTTPServer | None = None
        self._configured: list[_Interaction] = []
        self._calls: list[CallRecord] = []
        self._violations: list[str] = []

    @property
    def base_url(self) -> str:
        if self._httpserver is None:
            raise MocktureError(
                "Mockture server is not started. Hint: call start() before using base_url."
            )
        return self._httpserver.url_for("")

    def url_for(self, path: str) -> str:
        if self._httpserver is None:
            raise MocktureError(
                "Mockture server is not started. Hint: call start() before using url_for()."
            )
        return self._httpserver.url_for(path)

    def start(self) -> None:
        if self._httpserver is not None:
            return
        try:
            from pytest_httpserver import HTTPServer as _HTTPServer
        except ModuleNotFoundError as exc:
            raise MocktureError(
                "Missing dependency 'pytest-httpserver'. "
                "Hint: install it before calling start()."
            ) from exc
        self._httpserver = _HTTPServer(host=self._host, port=self._port)
        self._httpserver.start()

        for interaction in self._configured:
            self._register_interaction(interaction)

    def stop(self) -> None:
        if self._httpserver is None:
            return
        self._httpserver.stop()
        self._httpserver = None

    def for_context(self, **context_args: Any) -> MocktureContext:
        return MocktureContext(parent=self, context_args=context_args)

    def for_incident(self, incident_id: str) -> MocktureContext:
        return self.for_context(incident_id=incident_id)

    def respond(self, target: str | dict[str, Any], **kwargs: Any) -> "Mockture":
        self._respond_with_context({}, target, kwargs)
        return self

    def _respond_with_context(
        self,
        context_args: dict[str, Any],
        target: str | dict[str, Any],
        kwargs: dict[str, Any],
    ) -> None:
        invocations = normalize_respond_input(first_arg=target, kwargs=kwargs)
        for template_name, explicit_args in invocations:
            rendered = self._templates.render(
                template_name=template_name,
                context_args=context_args,
                explicit_args=explicit_args,
            )
            response = rendered.get("response", {})
            method = str(rendered["method"]).upper()
            path = str(rendered["path"])
            status = int(response.get("status", 200))
            body = response.get("body")
            headers = response.get("headers", {})
            if not isinstance(headers, dict):
                headers = {}

            self._contract.validate_config_interaction(
                method=method,
                path=path,
                status_code=status,
                response_body=body,
            )

            interaction = _Interaction(
                template_name=template_name,
                method=method,
                path=path,
                status_code=status,
                body=body,
                headers={str(key): str(value) for key, value in headers.items()},
            )
            self._configured.append(interaction)

            if self._httpserver is not None:
                self._register_interaction(interaction)

    def calls_for(self, path: str, method: str) -> CallView:
        method_upper = method.upper()
        filtered = [
            record
            for record in self._calls
            if record.path == path and record.method == method_upper
        ]
        return CallView(records=filtered)

    def assert_called(self, path: str, method: str, times: int) -> None:
        observed = self.calls_for(path=path, method=method).count
        if observed != times:
            raise AssertionError(
                f"Expected '{method.upper()} {path}' to be called {times} times, "
                f"observed {observed}."
            )

    def assert_no_contract_violations(self) -> None:
        if self._violations:
            lines = "\n".join(self._violations)
            raise AssertionError(f"Contract violations detected:\n{lines}")

    def _register_interaction(self, interaction: _Interaction) -> None:
        if self._httpserver is None:
            return

        def _handler(request: Any) -> Any:
            from werkzeug.wrappers import Response

            request_json = request.get_json(silent=True)
            request_path = request.path
            status_code = interaction.status_code
            response_body = interaction.body
            response_headers = dict(interaction.headers)

            request_error = self._capture_request_validation(
                interaction.method,
                request_path,
                request_json,
            )
            if request_error and self._strict:
                return _error_response(500, request_error)

            response_error = self._capture_response_validation(
                interaction.method,
                request_path,
                status_code,
                response_body,
            )
            if response_error and self._strict:
                return _error_response(500, response_error)

            body_text = json.dumps(response_body) if response_body is not None else ""
            headers = {"Content-Type": "application/json", **response_headers}
            self._calls.append(
                CallRecord(
                    method=interaction.method,
                    path=request_path,
                    json_body=request_json,
                    headers={str(key): str(value) for key, value in request.headers.items()},
                    status_code=status_code,
                )
            )
            return Response(response=body_text, status=status_code, headers=headers)

        self._httpserver.expect_request(
            uri=interaction.path,
            method=interaction.method,
        ).respond_with_handler(_handler)

    def _capture_request_validation(
        self,
        method: str,
        path: str,
        json_body: Any,
    ) -> str | None:
        try:
            self._contract.validate_request(method=method, path=path, json_body=json_body)
            return None
        except ContractRuntimeError as exc:
            message = str(exc)
            self._violations.append(message)
            return message

    def _capture_response_validation(
        self,
        method: str,
        path: str,
        status_code: int,
        response_body: Any,
    ) -> str | None:
        try:
            self._contract.validate_response(
                method=method,
                path=path,
                status_code=status_code,
                response_body=response_body,
            )
            return None
        except ContractRuntimeError as exc:
            message = str(exc)
            self._violations.append(message)
            return message


def _error_response(status_code: int, message: str) -> Any:
    from werkzeug.wrappers import Response

    payload = {"error": "contract_violation", "message": message}
    return Response(
        response=json.dumps(payload),
        status=status_code,
        headers={"Content-Type": "application/json"},
    )
