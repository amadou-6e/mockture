Quickstart
==========

By the end of this page you will have a contract-validated pytest test running against
an in-process mock server.

Prerequisites
-------------

- Python 3.11 or later
- An OpenAPI 3.x spec for the service you are mocking (YAML or JSON)
- A template file defining your stub responses (see :ref:`writing-templates` below)

No Docker, no JVM, no external process.

Installation
------------

.. code-block:: bash

   pip install mockture

mockture registers itself as a pytest plugin automatically. No ``conftest.py`` import
is needed.

Your First mockture Test
------------------------

The example below shows the complete lifecycle: configure a response, start the server,
make a request, assert behavior, and let the plugin handle teardown.

.. code-block:: python

   import httpx
   import pytest

   @pytest.mark.mockture(
       contract="configs/orders.openapi.yml",
       templates="configs/orders.templates.yml",
   )
   def test_create_order(mockture):
       mockture.respond("create_order_success", order_id="ord-123", status="queued")

       r = httpx.post(
           mockture.url_for("/orders"),
           json={"item_id": "SKU-1", "quantity": 1},
       )

       assert r.status_code == 201
       assert r.json() == {"order_id": "ord-123", "status": "queued"}
       mockture.assert_called("/orders", "POST", 1)

``mockture.url_for(path)`` returns the full ``http://127.0.0.1:<port>/path`` for the
running server. Use it instead of hardcoding host and port.

What Just Happened
------------------

``respond()`` validated the template body against the OpenAPI schema before the server
started. If the body had violated the schema, the test would have failed at that line
with a ``ContractConfigError``, not downstream in an assertion.

``start()`` is called automatically by the plugin when the test begins. ``stop()`` is
called automatically when the test exits. The server runs on a random localhost port for
the lifetime of one test function.

.. _writing-templates:

Writing Templates
-----------------

Templates are YAML files that define stub responses as parameterised blueprints.

.. code-block:: yaml

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

Each ``args`` key is a placeholder. A ``null`` value marks a required argument that
must be supplied at ``respond()`` time.

Setting Default Paths
---------------------

To avoid repeating ``contract=`` and ``templates=`` on every marker, set project-wide
defaults in ``pyproject.toml``:

.. code-block:: toml

   [tool.pytest.ini_options]
   mockture_contract  = "tests/configs/openapi.yml"
   mockture_templates = "tests/configs/orders.templates.yml"

Tests can then use a bare marker: ``@pytest.mark.mockture``.

Next Steps
----------

- :doc:`introduction` -- audience fit and full capability overview
- :doc:`api_reference` -- complete API surface reference
- `Usage notebook <https://github.com/amadou-6e/mockture/blob/main/usage/mockture_server_usage.ipynb>`_ -- interactive walkthrough: arg overrides, chaining, ``for_context()``, strict vs non-strict modes, call inspection
- `Examples <https://github.com/amadou-6e/mockture/tree/main/example>`_ -- eight self-contained suites from raw object to multi-API plugin setups

