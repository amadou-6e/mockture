# Sharing Args with for_context()

When a test exercises multiple endpoints for the same entity, repeating the entity's ID on every `respond()` call is noisy and fragile. `for_context()` lets you declare shared args once and have them injected into every call inside the block, while still allowing individual calls to override any single arg.

For an interactive walkthrough, open [tutorial.ipynb](tutorial.ipynb).

## What you'll learn

1. Why arg repetition is a problem in multi-endpoint tests
2. How `for_context()` injects args into every `respond()` in the block
3. The override priority — explicit kwargs win over context values
4. Using two independent contexts on the same server instance

## The problem without for_context()

Suppose you are testing a create-then-fetch sequence and need a specific `order_id` to thread through both calls:

```python
mock.respond("create_order_success", order_id="ord-ctx-001", status="queued")
mock.respond("get_order",            order_id="ord-ctx-001", status="queued")
mock.respond("get_order_not_found",  order_id="ord-ctx-001")
```

`order_id="ord-ctx-001"` appears three times. Rename the order and you update three places with a risk of missing one.

## The solution: for_context()

```python
with mock.for_context(order_id="ord-ctx-001") as ctx:
    ctx.respond("create_order_success", status="queued")
    ctx.respond("get_order",            status="queued")
    ctx.respond("get_order_not_found")
```

`for_context()` returns a `MocktureContext` object. Every `ctx.respond()` call merges the context args in as if you had passed them explicitly, but at a lower priority than the kwargs on the call itself.

## Arg resolution priority

The priority order from highest to lowest is:

1. Explicit kwargs on the `respond()` call
2. Args set on the context via `for_context()`
3. Default values declared in the template

So this:

```python
with mock.for_context(order_id="ctx-default", status="created") as ctx:
    ctx.respond("create_order_success")                       # uses both context values
    ctx.respond("get_order", status="processing")       # overrides status only
```

produces a first interaction with `order_id="ctx-default"` and `status="created"`, and a second with `order_id="ctx-default"` and `status="processing"`. The explicit `status="processing"` on the second call wins; the `order_id` still comes from the context because it was not overridden.

## Two independent contexts

Multiple `for_context()` blocks on the same mock instance register independent sets of interactions:

```python
with mock.for_context(order_id="ord-A") as ctx:
    ctx.respond("create_order_success", status="created")
    ctx.respond("get_order",            status="created")

with mock.for_context(order_id="ord-B") as ctx:
    ctx.respond("create_order_success", status="queued")
    ctx.respond("get_order",            status="queued")
```

After `mock.start()`, the server has four registered interactions. Both `POST /orders` and `GET /orders/{order_id}` serve whichever interaction matches the incoming request path.

## Run the tests

```bash
pytest 05_context/
```

This folder uses raw `Mockture` with no plugin to keep the focus entirely on `for_context()`. The same pattern works inside a plugin-injected `mockture` fixture.

## Next steps

See [06_strict_modes/](../06_strict_modes/) for a detailed look at what happens when a request violates the contract.
