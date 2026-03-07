# mockture

Contract-aware in-process HTTP mocking for pytest.

```bash
pip install mockture
```

[![CI](https://img.shields.io/github/actions/workflow/status/amadou-6e/mockture/cicd.yml?label=CI)](https://github.com/amadou-6e/mockture/actions)
[![PyPI](https://img.shields.io/pypi/v/mockture)](https://pypi.org/project/mockture/)
[![Python](https://img.shields.io/pypi/pyversions/mockture)](https://pypi.org/project/mockture/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

**Your mocks are lying to you.** `responses`, `respx`, and friends let you return any dict you like, with no check that it actually matches your OpenAPI contract. When the upstream API changes, your stubs stay silent and your tests keep passing. mockture fixes this.

```python
@pytest.mark.mockture(
    contract="api/openapi.yml",
    templates="tests/templates.yml",
)
def test_create_order(mockture):
    # mockture validates the stub body against your OpenAPI spec at setup time.
    # If it's wrong, the test fails here, not in staging.
    mockture.respond("create_order_success", order_id="ord-123", status="queued")

    response = httpx.post(mockture.url_for("/orders"), json={"item_id": "A", "quantity": 1})
    assert response.status_code == 201
    assert mockture.calls_for("/orders", "POST").count == 1
```

mockture is a pytest plugin that runs an in-process HTTP mock server and validates every configured response against your OpenAPI spec. No Docker. No external process. No broker. Just a decorator and a YAML template file.

**Why not `responses` or `respx`?** They intercept at the transport layer but perform zero schema validation. When your upstream API changes its response shape, your stubs stay valid and your tests keep passing, silently encoding the bug.

**Why not Pact?** Pact is powerful but requires a Pact Broker, a bidirectional consumer/provider workflow, and team coordination. If you already have an OpenAPI spec, mockture gives you contract assurance without the infrastructure.

**Why not WireMock?** WireMock needs a JVM or Docker container. mockture starts in-process in milliseconds. No Docker Compose required in CI.

---

HTTP mocks that silently return invalid responses are one of the most common sources of "it worked in staging" bugs. mockture runs a real HTTP server on a random localhost port. Any HTTP client works, because there is no transport patching. Every stub response is validated against your OpenAPI spec at configuration time: if the body violates the schema, `respond()` raises immediately, before the test even runs. Mock drift is caught in CI, not in production.

---

## When to use this

- **Testing a FastAPI or OpenAPI-first service in pytest**: catch every stub response that drifts from the spec at setup time, not in staging.
- **Maintaining shared integration test infrastructure across microservices**: define response templates and call sequences once in YAML and reuse them across every test in the suite.
- **Standardising HTTP mocking patterns across repos**: one pytest marker, one config file, consistent `openapi contract validation` across every service your platform team owns.
- **Evaluating Pact but finding the broker workflow too heavy**: if you already have an OpenAPI spec, mockture gives you contract testing without a broker, a provider workflow, or team coordination overhead.

---

## Prerequisites

- Python 3.11 or later
- An OpenAPI 3.x spec for the service you are mocking (YAML or JSON)
- A template file defining your stub responses (YAML; see [Template authoring](#template-authoring))

No Docker, no JVM, no external process.

---

## Installation

```bash
pip install mockture
```

mockture registers itself as a pytest plugin automatically via the `pytest11` entry point. No `conftest.py` import is required.

---

## Usage

mockture is designed for backend engineers and QA/SDET engineers writing pytest integration tests against OpenAPI-documented services. The two entry points are the pytest marker (recommended) and the `Mockture` server object (for use outside pytest).

### Pytest plugin

Add the marker to any test. mockture starts the server, registers your responses, and stops the server when the test exits.

```python
import httpx
import pytest

@pytest.mark.mockture(
    contract="configs/orders.openapi.yml",
    templates="configs/orders.templates.yml",
)
def test_create_order(mockture):
    mockture.respond("create_order_success", order_id="ord-123", status="queued")

    r = httpx.post(mockture.url_for("/orders"), json={"item_id": "SKU-1", "quantity": 1})

    assert r.status_code == 201
    assert r.json() == {"order_id": "ord-123", "status": "queued"}
    mockture.assert_called("/orders", "POST", 1)
```

`url_for(path)` returns the full `http://127.0.0.1:<port>/path` URL for the running server. Use it instead of hardcoding the host and port.

### Default paths in `pyproject.toml`

To avoid repeating `contract=` and `templates=` on every marker, set project-wide defaults in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
mockture_contract  = "tests/configs/openapi.yml"
mockture_templates = "tests/configs/orders.templates.yml"
```

Tests can then use a bare marker:

```python
@pytest.mark.mockture
def test_create_order(mockture): ...
```

### Sequences

Register multiple responses in order. Requests are served first-in, first-out:

```python
@pytest.mark.mockture(
    contract=..., templates=...,
    sequence=["create_order_success", "create_order_conflict"],
)
def test_retry(mockture):
    r1 = httpx.post(mockture.url_for("/orders"), json={"item_id": "A", "quantity": 1})
    r2 = httpx.post(mockture.url_for("/orders"), json={"item_id": "A", "quantity": 1})
    assert r1.status_code == 201
    assert r2.status_code == 409
```

### Scenarios

Pre-register a named set of responses as a dict, useful for multi-endpoint tests:

```python
@pytest.mark.mockture(
    contract=..., templates=...,
    scenario={"create_order_success": {"order_id": "ord-1"}, "create_order_conflict": None},
)
def test_scenario(mockture): ...
```

### Named flows

Define reusable call sequences in a YAML flows file and reference them by name:

```python
@pytest.mark.mockture(contract=..., templates=..., flow="happy_path")
def test_happy_path(mockture): ...
```

### Shared context

Use `for_context()` to inject arguments across multiple `respond()` calls without repeating them:

```python
with mockture.for_context(order_id="ctx-001") as ctx:
    ctx.respond("create_order_success", status="queued")
    ctx.respond("create_order_success", status="completed")
```

### Contract validation modes

**Strict mode (default):** Requests that violate the OpenAPI schema are rejected with HTTP 500 and are not counted in the call log.

**Non-strict mode:** Violations are recorded but the configured response is still returned. Use `assert_no_contract_violations()` to surface them explicitly.

```python
@pytest.mark.mockture(contract=..., templates=..., strict=False)
def test_non_strict(mockture):
    mockture.respond("create_order_success")
    httpx.post(mockture.url_for("/orders"), json={"item_id": "", "quantity": 0})
    mockture.assert_no_contract_violations()   # raises AssertionError if any violations were recorded
```

### Inspecting calls

```python
view = mockture.calls_for("/orders", "POST")
print(view.count)                    # number of matching requests
print(view.records[0].json_body)     # request body of the first call
print(view.records[0].status_code)   # response status code
```

### Server object (without pytest)

The `Mockture` class can be used directly in any Python context:

```python
from mockture import Mockture

mock = Mockture(contract_path="openapi.yml", templates_path="orders.templates.yml")
mock.respond("create_order_success", order_id="ord-123", status="queued")
mock.start()

r = httpx.post(mock.url_for("/orders"), json={"item_id": "SKU-1", "quantity": 1})
assert r.status_code == 201

mock.stop()
```

### More examples

The [`example/`](example/) directory contains eight self-contained examples, ordered from lowest-level to highest-level:

| Example | What it shows |
|---|---|
| [01_basic/](example/01_basic/) | Raw `Mockture` object, manual lifecycle |
| [02_plugin_explicit/](example/02_plugin_explicit/) | Plugin with all paths on every marker |
| [03_plugin_ini/](example/03_plugin_ini/) | `pyproject.toml` defaults + `api=` / `flow=` |
| [04_flows/](example/04_flows/) | All flow formats: named, inline, scenario YAML |
| [05_context/](example/05_context/) | `for_context()`: shared args across `respond()` calls |
| [06_strict_modes/](example/06_strict_modes/) | `strict=True` vs `strict=False` |
| [07_template_authoring/](example/07_template_authoring/) | `x-mockture` annotations + two-file template layout |
| [08_multi_api/](example/08_multi_api/) | Two test directories, two APIs, two config files |

The [`usage/`](usage/) notebook (`mockture_server_usage.ipynb`) walks through the full `Mockture` server object API interactively.

---

## Template authoring

Templates are YAML files that define stub responses as parameterised blueprints. Each entry has:

- `args`: default values for every placeholder. A `null` value marks a required argument that must be supplied at `respond()` time.
- `interaction`: the HTTP method, path, status code, and response body, with `{placeholder}` tokens filled from `args`.

```yaml
create_order_success:
  args:
    order_id: ord-default
    status: created
  interaction:
    method: POST
    path: /orders
    status: 201
    response:
      body:
        order_id: "{order_id}"
        status: "{status}"
```

See [example/07_template_authoring/](example/07_template_authoring/) for the full template format including `x-mockture` annotations and multi-file layouts.

---

## Development

```bash
git clone https://github.com/amadou-6e/mockture
cd mockture
pip install -e ".[dev]"
```

Run all examples:

```bash
pytest example/
```

---

## Testing

```bash
pytest tests/
```

---

## Contributing

Issues and pull requests are welcome at [github.com/amadou-6e/mockture](https://github.com/amadou-6e/mockture/issues).

---

## License

MIT. See [LICENSE](./LICENSE).
