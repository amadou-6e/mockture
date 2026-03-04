from pathlib import Path

import pytest

pytest_plugins = ["mockture.pytest_plugin"]


@pytest.fixture
def fixtures_dir() -> Path:
    return Path("tests", "configs", "fixtures")


@pytest.fixture
def contract_path(fixtures_dir: Path) -> Path:
    return Path(fixtures_dir, "test_openapi.yml")


@pytest.fixture
def templates_path(fixtures_dir: Path) -> Path:
    return Path(fixtures_dir, "test_orders.templates.yml")


@pytest.fixture
def scenario_path(fixtures_dir: Path) -> Path:
    return Path(fixtures_dir, "test_orders.flows.yml")

