# Mockture Examples

Each subfolder is a self-contained example targeting a specific starting point
or feature area. They are ordered from lowest-level to highest-level convenience.

## Subfolders

| Folder | What it shows | Plugin? | ini? |
|---|---|---|---|
| [01_basic/](01_basic/) | Raw `Mockture` object — no plugin, manual lifecycle | No | No |
| [02_plugin_explicit/](02_plugin_explicit/) | Plugin with all paths on every marker | Yes | No |
| [03_plugin_ini/](03_plugin_ini/) | `mockture.ini` + `configs_dir` + `api=`/`flow=` | Yes | Yes |
| [04_flows/](04_flows/) | All flow formats: named, inline, scenario YAML file | Yes | Yes |
| [05_context/](05_context/) | `for_context()` — shared args across `respond()` calls | No | No |
| [06_strict_modes/](06_strict_modes/) | `strict=True` vs `strict=False` | No | No |
| [07_template_authoring/](07_template_authoring/) | `x-mockture` annotations + two-file template layout | Yes | Yes |
| [08_multi_api/](08_multi_api/) | Two test dirs, two `mockture.ini` files, two APIs | Yes | Yes |

## Which example to start with?

**"I just want to understand the API"** → [01_basic/](01_basic/)

**"I want to write pytest tests"** → [03_plugin_ini/](03_plugin_ini/)

**"I need to set up templates from an OpenAPI spec"** → [07_template_authoring/](07_template_authoring/)

**"My test suite covers more than one API"** → [08_multi_api/](08_multi_api/)

## Run all examples

```bash
pytest example/
```

## Common API

All examples use a simple Orders API:

- `POST /orders` — create an order (returns 201 or 409)
- `GET /orders/{order_id}` — fetch an order (returns 200 or 404)

The Auth API (08_multi_api) additionally has:

- `POST /auth/token` — issue a token (returns 200 or 401)
- `GET /auth/me` — current user (returns 200 or 401)
