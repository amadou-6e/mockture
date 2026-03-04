# All the Ways to Pre-Register Interactions

A flow is any set of interactions registered before the test body makes its first HTTP call. Flows keep setup out of test logic and make the test's intent clearer. This folder covers every format the engine supports.

## What you'll learn

1. The six formats for registering interactions and when to use each
2. The `flows.yml` file — a registry of named flows
3. The three shapes a flow entry can take: sequence, single-string, scenario dict
4. Inline `sequence=` and `scenario=` on the marker
5. Loading a scenario from a `.yml` file at test time
6. Multiple invocations of the same template in one scenario

## The six formats at a glance

| Format | Declared | Registered | Best for |
|---|---|---|---|
| Named flow (sequence) | `flows.yml` | `flow="name"` on marker | Ordered multi-step sequences |
| Named flow (string) | `flows.yml` | `flow="name"` on marker | Single-template shorthand |
| Named flow (scenario) | `flows.yml` | `flow="name"` on marker | Multi-template, order-independent |
| Inline `sequence=` | marker | automatically | One-off sequences that don't need a name |
| Inline `scenario=` | marker | automatically | One-off scenario dicts |
| Scenario YAML file | `.yml` file | `respond(filepath)` | Reusable scenarios shared across tests |

## Format 1 — Named sequence in flows.yml

A sequence is an ordered list. Each entry is either a template name alone (uses defaults) or a `{template, args}` dict:

```yaml
flows:
  create_and_fetch:
    - template: create_order_success
      args:
        order_id: ord-flow-001
        status: queued
    - template: get_order
      args:
        order_id: ord-flow-001
        status: queued
```

```python
@pytest.mark.mockture(api="basic_api", flow="create_and_fetch")
def test_named_sequence_flow(mockture):
    # Both POST /orders and GET /orders/{order_id} are already registered.
    r_post = httpx.post(mockture.url_for("/orders"), ...)
    r_get  = httpx.get(mockture.url_for("/orders/ord-flow-001"), ...)
```

## Format 2 — Single-template shorthand

When a flow consists of one template only, write it as a plain string value instead of a list:

```yaml
  conflict_only: create_order_conflict    # equivalent to: - create_order_conflict
```

## Format 3 — Scenario dict in flows.yml

A scenario dict in `flows.yml` is identical to what you pass to `respond(dict)` inline. Keys are template names, values are args:

```yaml
  happy_path_scenario:
    create_order_success:
      order_id: ord-happy-001
    get_order:
      order_id: ord-happy-001
```

Unlike a sequence, a scenario dict has no implied ordering between templates. Use it when two endpoints need to be available but the test might call them in any order.

## Format 4 — Inline sequence on the marker

For one-off sequences that don't belong in `flows.yml`, put them directly on the marker with `sequence=`:

```python
@pytest.mark.mockture(
    api="basic_api",
    sequence=[
        "create_order_success",
        {"template": "get_order", "args": {"order_id": "ord-seq-1", "status": "created"}},
    ],
)
def test_inline_sequence_on_marker(mockture):
    ...
```

## Format 5 — Inline scenario on the marker

For one-off scenario dicts, use `scenario=` with a dict:

```python
@pytest.mark.mockture(
    api="basic_api",
    scenario={
        "create_order_success": {"order_id": "ord-s1"},
        "create_order_conflict": None,    # None means use template defaults
    },
)
def test_inline_scenario_on_marker(mockture):
    ...
```

## Format 6 — Scenario YAML file

For scenarios reused across multiple test files, keep them as `.yml` files and pass the file path to `respond()`. The file format is the same as the inline scenario dict, but in YAML:

```yaml
# tests/scenarios/reorder_scenario.yml
create_order_success:
  order_id: ord-reorder-001

get_order:
  - order_id: ord-reorder-001    # first invocation
    status: created
  - order_id: ord-reorder-001    # second invocation
    status: processing
```

```python
mockture.respond("tests/scenarios/reorder_scenario.yml")
```

`respond()` detects that the string is an existing file path and loads it as a scenario. A string that does not match an existing file is treated as a template name instead.

## Multiple invocations of the same template

A list value in a scenario dict registers the same template multiple times, each with different args:

```python
mockture.respond({
    "create_order_success": [
        {"order_id": "ord-multi-1", "status": "created"},
        {"order_id": "ord-multi-2", "status": "queued"},
    ]
})
```

Both interactions are registered on `POST /orders` and served independently for separate requests.

## Run the tests

```bash
pytest 04_flows/
```

## Next steps

See [05_context/](../05_context/) for `for_context()`, which shares args across `respond()` calls within a single test.
