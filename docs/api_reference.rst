API Reference
=============

Core Runtime API
----------------

`mockture.Mockture`
  Main in-process mock server class used in tests.

`mockture.use_mockture`
  Decorator alias for `pytest.mark.mockture(...)`.

`mockture.TemplateGenerator`
  OpenAPI-driven template generator helper.

Pytest Integration
------------------

Enable plugin usage with:

.. code-block:: python

   pytest_plugins = ["mockture.pytest_plugin"]

Then configure a test with:

.. code-block:: python

   import pytest

   @pytest.mark.mockture(
       contract="path/to/openapi.yml",
       templates="path/to/templates.yml",
   )
   def test_api(mockture):
       ...

CLI
---

`mockture generate`
  Generate templates from OpenAPI `x-mockture-*` annotations.

`mockture validate`
  Validate OpenAPI structure and local reference resolution.

`mockture list-templates`
  List templates discoverable from annotated specs.

