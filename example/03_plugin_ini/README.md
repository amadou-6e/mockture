# mockture.ini and the api= Marker

[02_plugin_explicit/](../02_plugin_explicit/) had paths on every marker. This folder removes that repetition with a `mockture.ini` file. Markers shrink to expressing what to do, not where files live.

## What you'll learn

1. How `mockture.ini` is discovered by walking up the file system from the test file
2. The `configs_dir` naming convention — one setting resolves three files
3. `api=` on the marker and how it connects to the ini
4. `flow=` on the marker for pre-registering a named flow from the flows file
5. The `"api:flow"` shorthand
6. Module-scoped instances and the interaction accumulation gotcha

## The mockture.ini file

Place a `mockture.ini` in any directory that contains tests or a parent of it:

```ini
; tests/mockture.ini
[mockture]
configs_dir = ../configs
```

When a test runs, the plugin walks up from the test file's directory looking for the nearest `mockture.ini`. It stops at the project root — the first ancestor containing `pyproject.toml`, `setup.cfg`, or `.git`. In this example the test file lives at `tests/test_ini_usage.py`. The plugin finds `tests/mockture.ini` immediately. All paths in the ini are relative to the ini file itself, so `../configs` resolves to `03_plugin_ini/configs/`.

## configs_dir — resolving three files from one setting

With `configs_dir = ../configs` in the ini and `api="basic_api"` on the marker, the plugin builds three paths by convention:

| File | Resolved path |
|---|---|
| Contract | `configs/basic_api.openapi.yml` |
| Templates | `configs/basic_api.templates.yml` |
| Flows | `configs/basic_api.flows.yml` (optional — only loaded if present) |

The pattern is `{configs_dir}/{api}.{type}.yml`. If your files follow this naming pattern, `api=` is the only thing the marker needs to say. If your files are named differently, use explicit paths in the ini instead, as shown in [08_multi_api/](../08_multi_api/).

## The marker with api=

```python
@pytest.mark.mockture(api="basic_api", strict=True)
def test_create_order(mockture):
    mockture.respond("create_order_success", order_id="ord-ini-1")
    ...
```

Compare this to the same test in [02_plugin_explicit/](../02_plugin_explicit/), which required three extra kwargs just for file locations. The `api=` kwarg replaces the two path kwargs entirely. Adding a flows file later does not change the marker at all — the ini already knows where to find it.

## Pre-registering a named flow with flow=

`configs/basic_api.flows.yml` defines named interaction sequences. With `flow=` on the marker, those interactions are registered before the test body runs:

```python
@pytest.mark.mockture(api="basic_api", flow="create_and_fetch")
def test_named_flow(mockture):
    # POST /orders and GET /orders/{order_id} are already registered.
    r_post = httpx.post(mockture.url_for("/orders"), ...)
    r_get  = httpx.get(mockture.url_for("/orders/ord-flow-001"), ...)
```

Use `flow=` when the test's purpose is to verify behavior after a known sequence of API calls — the setup is declarative and stays out of the test body.

## The "api:flow" shorthand

If your ini uses `configs_dir`, you need `api=` to resolve files and `flow=` to name the flow. The shorthand combines both in one string:

```python
# Canonical form
@pytest.mark.mockture(api="basic_api", flow="conflict_only")

# Shorthand — equivalent
@pytest.mark.mockture(flow="basic_api:conflict_only")
```

Do not mix them: if `api=` is already set, `flow=` should be a bare name, not a `"api:flow"` string.

## Module scope and interaction accumulation

Mockture supports three scopes: `"function"` (default), `"module"`, and `"session"`. With `scope="module"`, the same `Mockture` instance is reused for all tests in the module that share the same config.

```python
@pytest.mark.mockture(api="basic_api", strict=False, scope="module")
def test_module_scope_first(mockture):
    mockture.respond("create_order_success", order_id="ord-mod-1")
    httpx.post(mockture.url_for("/orders"), ...)

@pytest.mark.mockture(api="basic_api", strict=False, scope="module")
def test_module_scope_second(mockture):
    # The instance from test_module_scope_first is reused.
    # "create_order_success" is still registered from the first test.
    mockture.respond("get_order", order_id="ord-mod-1", status="created")
    httpx.get(mockture.url_for("/orders/ord-mod-1"), ...)

    # Both the POST and GET have been called across the two tests.
    mockture.assert_called(path="/orders", method="POST", times=1)
    mockture.assert_called(path="/orders/{order_id}", method="GET", times=1)
```

`respond()` calls from earlier tests in the module are not reset between tests. Design shared-scope tests so that accumulated interactions are intentional or harmless.

## Run the tests

```bash
pytest 03_plugin_ini/
```

## Next steps

See [04_flows/](../04_flows/) for a full tour of all flow formats, or jump to [08_multi_api/](../08_multi_api/) to see two test directories each with their own independent `mockture.ini`.
