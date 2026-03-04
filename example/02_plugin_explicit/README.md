# The pytest Plugin, Step by Step

This folder shows what the plugin gives you compared to [01_basic/](../01_basic/). The same tests are now written as ordinary pytest functions with no manual `start()`/`stop()` and no `try/finally`. The marker is the entry point for everything.

## What you'll learn

1. How to activate the Mockture pytest plugin in a project
2. What the `@pytest.mark.mockture` marker does behind the scenes
3. How `respond()` is called inside the test body after the server is already running
4. The `use_mockture` import alias as an alternative to the marker
5. Passing an inline scenario dict to `respond()`

## Activating the plugin

The plugin is not active by default. Add this to your `conftest.py`:

```python
# conftest.py
pytest_plugins = ["mockture.pytest_plugin"]
```

One line. The plugin registers the `mockture` marker and wires up the `mockture` fixture. Without this line, `@pytest.mark.mockture` is silently ignored.

## The marker

```python
@pytest.mark.mockture(
    contract="configs/basic_api.openapi.yml",
    templates="configs/basic_api.templates.yml",
    strict=True,
)
def test_create_order(mockture):
    mockture.respond("create_order_success", order_id="ord-1")
    ...
```

When pytest collects this test, the plugin reads the contract and templates paths from the marker kwargs, constructs a `Mockture` instance, calls `start()` on it, injects the running instance as the `mockture` fixture parameter, runs your test body where you call `respond()` and make HTTP requests, then calls `stop()` after the test completes whether it passes or fails. The `mockture` fixture parameter name is fixed — the plugin always injects it under that name.

## Calling respond() inside the test

In [01_basic/](../01_basic/) we called `respond()` before `start()`. Here we call it after, because the server is already running when the test body executes. Both orderings work: `respond()` can register interactions on a running server just as well as on a stopped one.

```python
def test_create_order(mockture):
    # Server is already started when we get here.
    mockture.respond("create_order_success", order_id="ord-1")

    r = httpx.post(mockture.url_for("/orders"), json={"item_id": "SKU-1", "quantity": 1})
    assert r.status_code == 201
```

## use_mockture — the import alias

`use_mockture` is imported from `mockture` and is identical to `pytest.mark.mockture`. Use whichever you prefer:

```python
from mockture import use_mockture

@use_mockture(contract=..., templates=..., strict=False)
def test_something(mockture):
    ...
```

## Inline scenario dict

Instead of calling `respond()` separately for each template, you can pass a dict directly. Keys are template names, values are args (or `None` to use defaults):

```python
@pytest.mark.mockture(contract=..., templates=..., strict=True)
def test_inline_scenario_dict(mockture):
    mockture.respond({
        "create_order_success": {"order_id": "ord-s1", "status": "created"},
        "get_order":            {"order_id": "ord-s1", "status": "created"},
    })
```

This registers both interactions in a single `respond()` call, which is useful when a test exercises a sequence of endpoints that belong together.

## The repetition problem

Notice that every marker in this folder carries the same `contract=` and `templates=` paths. If you have 20 tests, that is 40 repeated path strings. If the files move, you update 40 places. This folder shows the explicit form intentionally. The solution is a `mockture.ini` config file, shown in [03_plugin_ini/](../03_plugin_ini/).

## Run the tests

```bash
pytest 02_plugin_explicit/
```

## Next steps

Move to [03_plugin_ini/](../03_plugin_ini/) to put the paths into `mockture.ini` and let markers shrink to a single `api=` kwarg.
