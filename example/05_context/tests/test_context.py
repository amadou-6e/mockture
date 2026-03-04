"""05_context — for_context() scoped context manager.

When multiple respond() calls in a test share the same arg values
(e.g., the same order_id), for_context() avoids repeating them on
every call. Args set on the context have lower priority than explicit
kwargs on each respond() call.
"""

from pathlib import Path

import httpx

from mockture.server import Mockture


_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = str(_ROOT / "configs" / "basic_api.openapi.yml")
_TEMPLATES = str(_ROOT / "configs" / "basic_api.templates.yml")


def _mock(**kwargs) -> Mockture:
    return Mockture(contract_path=_CONTRACT, templates_path=_TEMPLATES, **kwargs)


def test_for_context_shares_order_id() -> None:
    """All respond() calls inside the block inherit order_id from context."""
    mock = _mock(strict=True)

    with mock.for_context(order_id="ord-ctx-001") as ctx:
        ctx.respond("create_order_success", status="queued")
        ctx.respond("get_order", status="queued")

    mock.start()

    try:
        r_post = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "SKU-1", "quantity": 1},
            timeout=5.0,
        )
        r_get = httpx.get(mock.url_for("/orders/ord-ctx-001"), timeout=5.0)

        assert r_post.status_code == 201
        assert r_post.json()["order_id"] == "ord-ctx-001"
        assert r_get.status_code == 200
        assert r_get.json()["order_id"] == "ord-ctx-001"

        mock.assert_no_contract_violations()
    finally:
        mock.stop()


def test_explicit_kwarg_overrides_context() -> None:
    """An explicit kwarg on respond() wins over the context value."""
    mock = _mock(strict=True)

    with mock.for_context(order_id="ctx-default", status="created") as ctx:
        ctx.respond("create_order_success")                         # uses ctx values
        ctx.respond("get_order", status="processing")        # overrides status only

    mock.start()

    try:
        r_post = httpx.post(
            mock.url_for("/orders"),
            json={"item_id": "A", "quantity": 1},
            timeout=5.0,
        )
        r_get = httpx.get(mock.url_for("/orders/ctx-default"), timeout=5.0)

        assert r_post.json() == {"order_id": "ctx-default", "status": "created"}
        assert r_get.json() == {"order_id": "ctx-default", "status": "processing"}
    finally:
        mock.stop()


def test_multiple_contexts_independent() -> None:
    """Two separate for_context() blocks register independent interactions."""
    mock = _mock(strict=True)

    with mock.for_context(order_id="ord-A") as ctx:
        ctx.respond("create_order_success", status="created")
        ctx.respond("get_order", status="created")

    with mock.for_context(order_id="ord-B") as ctx:
        ctx.respond("create_order_success", status="queued")
        ctx.respond("get_order", status="queued")

    mock.start()

    try:
        httpx.post(mock.url_for("/orders"), json={"item_id": "A", "quantity": 1}, timeout=5.0)
        httpx.post(mock.url_for("/orders"), json={"item_id": "B", "quantity": 1}, timeout=5.0)
        r_a = httpx.get(mock.url_for("/orders/ord-A"), timeout=5.0)
        r_b = httpx.get(mock.url_for("/orders/ord-B"), timeout=5.0)

        assert r_a.json()["status"] == "created"
        assert r_b.json()["status"] == "queued"
        mock.assert_called(path="/orders", method="POST", times=2)
    finally:
        mock.stop()


def test_context_without_context_manager() -> None:
    """for_context() can also be used without 'with' — ctx.respond() works the same."""
    mock = _mock(strict=False)

    ctx = mock.for_context(order_id="ord-noctx")
    ctx.respond("get_order", status="created")

    mock.start()

    try:
        r = httpx.get(mock.url_for("/orders/ord-noctx"), timeout=5.0)
        assert r.status_code == 200
        assert r.json()["order_id"] == "ord-noctx"
    finally:
        mock.stop()
