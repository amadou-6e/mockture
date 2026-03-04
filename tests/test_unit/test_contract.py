from pathlib import Path

import pytest

from mockture.contract import OpenAPIContractValidator
from mockture.errors import ContractConfigError
from mockture.errors import ContractRuntimeError


def test_config_validation_passes_for_declared_path(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    validator.validate_config_interaction(
        method="POST",
        path="/orders",
        status_code=201,
        response_body={"order_id": "ord-1", "status": "created"},
    )


def test_config_validation_unknown_path_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractConfigError):
        validator.validate_config_interaction(
            method="POST",
            path="/missing",
            status_code=201,
            response_body={"order_id": "ord-1", "status": "created"},
        )


def test_config_validation_unknown_method_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractConfigError):
        validator.validate_config_interaction(
            method="GET",
            path="/orders",
            status_code=201,
            response_body={"order_id": "ord-1", "status": "created"},
        )


def test_config_validation_unknown_status_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractConfigError):
        validator.validate_config_interaction(
            method="POST",
            path="/orders",
            status_code=202,
            response_body={"order_id": "ord-1", "status": "created"},
        )


def test_config_validation_invalid_response_schema_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractConfigError):
        validator.validate_config_interaction(
            method="POST",
            path="/orders",
            status_code=201,
            response_body={"wrong": "shape"},
        )


def test_runtime_request_validation_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractRuntimeError):
        validator.validate_request(
            method="POST",
            path="/orders",
            json_body={"item_id": "", "quantity": 0},
        )


def test_runtime_response_validation_fails(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    with pytest.raises(ContractRuntimeError):
        validator.validate_response(
            method="POST",
            path="/orders",
            status_code=201,
            response_body={"bad": "payload"},
        )


def test_path_parameter_pattern_matches(contract_path: Path) -> None:
    validator = OpenAPIContractValidator(str(contract_path))

    validator.validate_config_interaction(
        method="GET",
        path="/incidents/INC-1/threads",
        status_code=200,
        response_body={"items": []},
    )
