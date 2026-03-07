mockture
========

Contract-aware in-process HTTP mocking for pytest.

.. code-block:: bash

   pip install mockture

**Your mocks are lying to you.** ``responses``, ``respx``, and friends let you return
any dict you like, with no check that it actually matches your OpenAPI contract. When
the upstream API changes, your stubs stay silent and your tests keep passing. mockture
fixes this.

.. code-block:: python

   import httpx
   import pytest

   @pytest.mark.mockture(
       contract="api/openapi.yml",
       templates="tests/templates.yml",
   )
   def test_create_order(mockture):
       # validated against the OpenAPI spec at setup time
       mockture.respond("create_order_success", order_id="ord-123", status="queued")

       response = httpx.post(mockture.url_for("/orders"), json={"item_id": "A", "quantity": 1})
       assert response.status_code == 201
       assert mockture.calls_for("/orders", "POST").count == 1

mockture is a pytest plugin that runs an in-process HTTP mock server and validates every
configured response against your OpenAPI spec. No Docker. No external process. No broker.
Just a decorator and a YAML template file.

**Why not** ``responses`` **or** ``respx`` **?**
They intercept at the transport layer but perform zero schema validation. When your
upstream API changes its response shape, your stubs stay valid and your tests keep
passing, silently encoding the bug.

**Why not Pact?**
Pact is powerful but requires a Pact Broker, a bidirectional consumer/provider workflow,
and team coordination. If you already have an OpenAPI spec, mockture gives you contract
assurance without the infrastructure.

**Why not WireMock?**
WireMock needs a JVM or Docker container. mockture starts in-process in milliseconds.
No Docker Compose required in CI.

----

Who Is This For
---------------

**Backend engineers testing OpenAPI-first services.**
If you ship a FastAPI or any OpenAPI-documented service and write pytest integration
tests, mockture catches stub drift at test setup time rather than in staging. You get
contract-validated in-process mocks without changing how you run tests.

**QA and SDET engineers maintaining shared test infrastructure.**
If you own integration test suites that span multiple services, mockture lets you define
response templates and call sequences once in YAML and reuse them across every test in
the suite. Named flows, scenarios, and ``for_context()`` replace repetitive inline setup.

**Platform and developer-experience teams standardising mocking patterns.**
One pytest marker and one config file give you consistent ``openapi contract validation``
across every service repo. No more per-repo patching strategies or divergent mocking
approaches.

**Teams evaluating Pact but finding the workflow too heavy.**
If you already have an OpenAPI spec, that spec is your contract. mockture uses it
directly: no broker, no provider workflow, no bidirectional coordination required.

----

What You Can Do With mockture
-----------------------------

**Catch mock drift before staging.**
Every stub response is validated against the OpenAPI schema at ``respond()`` time. A
body that violates the schema raises ``ContractConfigError`` before the server starts,
so the failure points directly to the misconfigured template rather than to a downstream
assertion.

**Define once, reuse everywhere.**
YAML response templates accept placeholder arguments with defaults. A single template
covers all test variations: call ``respond("create_order_success")`` for the default
shape or ``respond("create_order_success", order_id="ord-123", status="queued")`` to
override individual fields.

**Compose realistic call sequences.**
Use ``sequence=``, ``scenario=``, or named ``flow=`` on the pytest marker to pre-register
multi-step interaction patterns. Share argument values across related calls with
``for_context()``.

**Choose how strict contract enforcement is.**
In ``strict=True`` mode (default), requests that violate the OpenAPI schema are rejected
with HTTP 500 and not counted. In ``strict=False`` mode, violations are recorded and
surfaced explicitly via ``assert_no_contract_violations()``.

----

Where To Go Next
----------------

- :doc:`quick_start` -- run your first contract-aware mock in five minutes
- :doc:`api_reference` -- full API surface reference
- `Usage notebook <https://github.com/amadou-6e/mockture/blob/main/usage/mockture_server_usage.ipynb>`_ -- interactive walkthrough of the full ``Mockture`` object API
- `Examples <https://github.com/amadou-6e/mockture/tree/main/example>`_ -- eight self-contained example suites from raw object to multi-API plugin setups

