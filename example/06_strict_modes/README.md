# Contract Validation: Strict and Non-Strict Mode

Mockture validates every interaction against the OpenAPI contract in two phases. The first phase runs at configuration time when `respond()` is called, checking whether the template's rendered response body matches the declared schema. The second phase runs at request time, checking the incoming request body against the schema for that endpoint. The `strict` flag controls what happens when a violation is detected at runtime.

For an interactive walkthrough, open [tutorial.ipynb](tutorial.ipynb).

## What you'll learn

1. What config-time validation means and why it happens at `respond()` time
2. What strict mode does: HTTP 500 on schema violations
3. What non-strict mode does: serve the response anyway and record the violation
4. How `assert_no_contract_violations()` works in both modes
5. When to use strict vs non-strict

## Phase 1 — Config-time validation

When you call `respond("some_template")`, Mockture renders the response body and checks it against the OpenAPI response schema before the server starts.

`configs/basic_api.templates.yml` includes an intentionally broken template:

```yaml
invalid_success_shape:
  args:
    status_code: 201
  interaction:
    method: POST
    path: /orders
    response:
      status: "{status_code}"
      body:
        bad_field: should_fail    # not in the OrderResponse schema
```

With `strict=True`:

```python
mock = Mockture(contract_path=..., templates_path=..., strict=True)

with pytest.raises(ContractConfigError):
    mock.respond("invalid_success_shape")    # raises immediately
```

With `strict=False`:

```python
mock = Mockture(..., strict=False)
mock.respond("invalid_success_shape")    # does not raise — violation recorded
```

Config-time validation runs regardless of strict mode. The difference is only in what happens at runtime when a request violation is detected.

## Phase 2 — Runtime validation (strict=True)

In strict mode, Mockture checks the incoming request body against the OpenAPI request schema. If it violates — wrong types, missing required fields, out-of-range values — the server returns HTTP 500 instead of the configured response:

```json
{"error": "contract_violation", "message": "...details..."}
```

```python
mock = Mockture(..., strict=True)
mock.respond("create_order_success")
mock.start()

r = httpx.post(mock.url_for("/orders"), json={"item_id": "", "quantity": 0})
assert r.status_code == 500
assert r.json()["error"] == "contract_violation"
```

The test catches the violation immediately in the status code. Use strict mode when you want contract violations to be test failures.

## Phase 2 — Runtime validation (strict=False)

In non-strict mode, a violating request still gets the configured response. The violation is silently recorded for later inspection:

```python
mock = Mockture(..., strict=False)
mock.respond("create_order_success", order_id="ord-ns-1")
mock.start()

r = httpx.post(mock.url_for("/orders"), json={"item_id": "", "quantity": 0})

assert r.status_code == 201                  # configured response returned
assert r.json()["order_id"] == "ord-ns-1"

with pytest.raises(AssertionError, match="contract"):
    mock.assert_no_contract_violations()     # surfaces the recorded violation
```

Use non-strict mode when testing client behavior that does not depend on whether the request is schema-valid — for example, testing that your client handles a 201 response body correctly regardless of how it got there.

## Violations always accumulate

In both modes, every violation is recorded until `stop()` is called. This means you can send multiple bad requests and then inspect all of them at once:

```python
mock.start()
httpx.post(mock.url_for("/orders"), json={"item_id": "",  "quantity": 0})    # violation 1
httpx.post(mock.url_for("/orders"), json={"item_id": "x", "quantity": 9999}) # violation 2
mock.assert_no_contract_violations()   # reports both
```

## When to use which mode

| Scenario | Mode |
|---|---|
| You want contract violations to fail the test immediately | `strict=True` (default) |
| You are testing client error handling, not schema compliance | `strict=False` |
| You are writing a template that intentionally violates the contract | `strict=False` + `assert_no_contract_violations()` to confirm the violation was recorded |

## Run the tests

```bash
pytest 06_strict_modes/
```

## Next steps

See [07_template_authoring/](../07_template_authoring/) for how `x-mockture` annotations let the OpenAPI spec generate templates automatically.
