# Your First Mock Server

Mockture is a contract-aware in-process HTTP mock server. Rather than running a real service during tests, you configure it with an OpenAPI contract and a library of named response templates, and it serves those responses from a local port while simultaneously validating every request and response against the schema.

Start here. This folder introduces Mockture from first principles with no pytest plugin, no ini files, and no fixtures. Once you understand the manual lifecycle, everything the plugin automates in later examples will make sense.

For an interactive walkthrough, open [tutorial.ipynb](tutorial.ipynb).

## What you'll learn

1. What Mockture is (a contract-aware HTTP server that runs in-process)
2. The lifecycle: construct, register responses, start, assert, stop
3. How `respond()` resolves args and validates against the OpenAPI contract at configuration time
4. How to chain multiple interactions on a single server instance
5. How to inspect every request that arrived

## The API we're mocking

`configs/basic_api.openapi.yml` defines a simple Order API with two endpoints: `POST /orders` which creates an order and returns 201 on success or 409 on conflict, and `GET /orders/{order_id}` which fetches an order and returns 200 if found or 404 if missing.

`configs/basic_api.templates.yml` defines named response templates, one per scenario. Here is what `create_order_success` looks like:

```yaml
create_order_success:
  args:
    status_code: 201
    order_id: ord-default    # has a default, can be overridden at respond() time
    status: created    # has a default
  interaction:
    method: POST
    path: /orders
    response:
      status: "{status_code}"
      body:
        order_id: "{order_id}"
        status: "{status}"
```

The `args` block defines what is configurable. All string values in `interaction` are interpolated with Python `str.format_map`, so `{order_id}` becomes whatever value was passed at `respond()` time.

## Step 1 — Construct

```python
from mockture.server import Mockture

mock = Mockture(
    contract_path="configs/basic_api.openapi.yml",
    templates_path="configs/basic_api.templates.yml",
    strict=True,
)
```

Constructing the server loads the contract and templates into memory. The HTTP server is not started yet — `start()` comes later. `strict=True` means runtime schema violations return HTTP 500. See [06_strict_modes/](../06_strict_modes/) for a comparison with non-strict mode.

## Step 2 — Register a response

```python
mock.respond("create_order_success", order_id="ord-123", status="queued")
```

`respond()` does three things. It looks up `create_order_success` in the templates file. It resolves args — your kwargs override template defaults, so `order_id` and `status` are overridden while `status_code` keeps its default of 201. It validates the rendered response body against the OpenAPI schema right now, before the server starts. If the body does not match, `ContractConfigError` is raised immediately.

`respond()` returns `self` for chaining:

```python
mock.respond("create_order_success", order_id="ord-A") \
    .respond("get_order", order_id="ord-A", status="created")
```

You can also call `respond()` before or after `start()`. Calls made before `start()` are queued and registered the moment the server starts.

## Step 3 — Start, request, stop

```python
mock.start()

try:
    response = httpx.post(
        mock.url_for("/orders"),   # "http://127.0.0.1:<ephemeral_port>/orders"
        json={"item_id": "SKU-1", "quantity": 2},
    )
    assert response.status_code == 201
    assert response.json() == {"order_id": "ord-123", "status": "queued"}
finally:
    mock.stop()
```

`url_for(path)` builds the full URL for the running server with no hardcoded ports. `stop()` is idempotent and resets all registered interactions. Always call it in a `finally` block.

## Step 4 — Assertions

```python
mock.assert_called(path="/orders", method="POST", times=1)
mock.assert_no_contract_violations()
```

`assert_called()` raises `AssertionError` if the endpoint was called a different number of times than expected. `assert_no_contract_violations()` raises if any request or response violated the schema.

To inspect calls in detail:

```python
view = mock.calls_for("/orders", "POST")
print(view.count)                   # 2
print(view.records[0].json_body)    # {"item_id": "SKU-1", "quantity": 2}
print(view.records[0].status_code)  # 201
```

## Run the tests

```bash
pytest 01_basic/
```

## Test file walkthrough

`tests/test_raw_mockture.py` contains seven focused tests:

| Test | Demonstrates |
|---|---|
| `test_create_order_returns_201` | Full happy-path lifecycle |
| `test_fetch_order_returns_200` | GET with a path parameter |
| `test_conflict_returns_409` | Registering the 409 template |
| `test_respond_chaining_registers_multiple_interactions` | Chaining `respond()` calls |
| `test_respond_before_start_queues_interaction` | `respond()` before `start()` |
| `test_invalid_template_raises_at_respond_time` | Config-time `ContractConfigError` |
| `test_calls_for_returns_recorded_requests` | `calls_for()` inspection |

## Next steps

Once you are comfortable with the manual lifecycle, move to [02_plugin_explicit/](../02_plugin_explicit/) where the plugin handles `start()` and `stop()`, or jump to [03_plugin_ini/](../03_plugin_ini/) where a config file removes path repetition entirely.
