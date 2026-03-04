# Two APIs, Two Directories, Zero Shared Config

Real projects often test multiple services. Mockture's `mockture.ini` discovery is directory-scoped — each test subdirectory can point at a completely different API. Tests in different directories never share state: different contracts, different templates, different `Mockture` instances.

## What you'll learn

1. The explicit-paths mode of `mockture.ini` for when `configs_dir` naming does not fit
2. How two test directories share one `conftest.py` but have independent `mockture.ini` files
3. Why no `api=` is needed on the marker when explicit paths are set in the ini
4. Running the two API suites together or independently

## The project structure

```
08_multi_api/
  configs/
    orders/
      orders.openapi.yml
      orders.templates.yml
    auth/
      auth.openapi.yml
      auth.templates.yml
  conftest.py              # activates the plugin for both subdirectories
  tests_orders/
    mockture.ini           # points at configs/orders/
    test_orders.py
  tests_auth/
    mockture.ini           # points at configs/auth/
    test_auth.py
```

`conftest.py` at the root activates the plugin for both subdirectories. Each test directory has its own `mockture.ini` — they are discovered independently by the plugin.

## The explicit-paths mockture.ini

Unlike [03_plugin_ini/](../03_plugin_ini/) where `configs_dir` handled naming, here the configs live in separate subdirectories and do not follow the `{api}.openapi.yml` convention. We use explicit path settings instead:

```ini
; tests_orders/mockture.ini
[mockture]
contract  = ../configs/orders/orders.openapi.yml
templates = ../configs/orders/orders.templates.yml
```

```ini
; tests_auth/mockture.ini
[mockture]
contract  = ../configs/auth/auth.openapi.yml
templates = ../configs/auth/auth.templates.yml
```

Paths are relative to the ini file itself, so `../configs/orders/` resolves correctly regardless of where pytest is invoked from.

## The marker with explicit paths in the ini

When the ini provides both `contract` and `templates` explicitly, the marker needs no path kwargs at all — not even `api=`:

```python
# tests_orders/test_orders.py
@pytest.mark.mockture                        # bare marker — all config comes from the ini
def test_create_order(mockture):
    mockture.respond("create_order_success", order_id="ord-1")
    ...

# tests_auth/test_auth.py
@pytest.mark.mockture                        # same marker form — different ini, different API
def test_login_success(mockture):
    mockture.respond("login_success", access_token="tok-abc123")
    ...
```

The two markers look identical but resolve to completely different `Mockture` instances with different contracts and templates. The resolution happens through the ini file in each test's directory.

## How ini discovery works here

When pytest runs `tests_orders/test_orders.py`, the plugin starts from `tests_orders/`, finds `tests_orders/mockture.ini` immediately, and builds paths relative to that file's location. When pytest runs `tests_auth/test_auth.py`, the same process finds `tests_auth/mockture.ini`. The two discoveries are completely independent and neither sees the other's ini file.

## Complete independence

The two test suites share the `conftest.py` that activates the plugin and nothing else. They do not share contracts, templates, `Mockture` instances, server ports, or violation accumulators. Violations in one suite never affect the other. This is how you would set up a project where `orders-service` and `auth-service` are tested by the same test run but independently mocked.

## Run the tests

```bash
# Both suites
pytest 08_multi_api/

# Orders only
pytest 08_multi_api/tests_orders/

# Auth only
pytest 08_multi_api/tests_auth/
```
