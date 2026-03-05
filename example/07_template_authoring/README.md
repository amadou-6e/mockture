# Templates from the OpenAPI Spec

Writing templates by hand is tedious and error-prone: field names must match the schema, defaults need to be invented, and every schema change requires a manual templates update. The `x-mockture` annotation approach puts template names and defaults directly in the spec, making the contract the single source of truth.

## What you'll learn

1. The four `x-mockture` annotations and what each one does
2. How `mockture generate` produces a `templates.yml` from annotations
3. Why `x-mockture-required` exists and what happens without it
4. The two-file layout — auto-generated vs hand-authored
5. What annotations cannot express and how to handle it

## The annotation approach

Instead of writing templates by hand, you annotate response objects in the OpenAPI spec:

```yaml
paths:
  /orders:
    post:
      responses:
        '201':
          description: Order created
          x-mockture-template: create_order_success     # opt this response into generation
          x-mockture-defaults:                          # default arg values
            order_id: ord-default
            status: created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderResponse'
```

Running `mockture generate configs/basic_api.openapi.yml` reads these annotations and writes `configs/basic_api.templates.auto.yml`. You can inspect the generated file to understand exactly what it contains: [configs/basic_api.templates.auto.yml](configs/basic_api.templates.auto.yml).

## The four annotations

`x-mockture-template` is required to opt a response into generation. Without this key, the response is ignored by `mockture generate`. This lets you annotate only the responses you need templates for.

`x-mockture-defaults` provides default arg values for specific fields. Values here override schema-inferred defaults. If a field appears in the schema but is not in `x-mockture-defaults`, `mockture generate` infers a default from the schema using this order: example, then default, then enum first value, then type-based fallback (`""` for strings, `0` for integers, `false` for booleans).

`x-mockture-required` forces a field to have a `null` default, meaning the caller must supply it via `respond()`. If they do not, Mockture raises `TemplateArgsError`. Without `x-mockture-required`, an identifier field like `order_id` would receive a type-based fallback of `""` and become silently optional:

```yaml
  x-mockture-required:
    - order_id    # caller must always supply this
```

`x-mockture-body` provides an explicit body dict and bypasses schema inference entirely. Use this for templates that intentionally violate the contract schema. It is mutually exclusive with `x-mockture-defaults`.

## How arg inference works

For each annotated response, `mockture generate` walks the JSON schema properties and creates a template arg for each field. Default values are resolved in this order:

1. Value in `x-mockture-defaults` for that field
2. `example` on the schema field
3. `default` on the schema field
4. First value of `enum`
5. Type-based fallback: `""` for strings, `0` for integers/numbers, `false` for booleans, `[]` for arrays, `{}` for objects

`status_code` is always added as a reserved arg set to the HTTP status integer.

## The two-file layout

`mockture generate` always overwrites its output file. Any hand-edits to `.auto.yml` will be lost on the next run. The solution is two files:

```
configs/
  basic_api.openapi.yml          # annotated spec — single source of truth
  basic_api.templates.auto.yml   # generated — safe to overwrite, do not edit
  basic_api.templates.yml        # hand-authored — survives regeneration
```

Hand-author templates when you need things annotations cannot express: body directives (`$generate`, `$thread`), intentional contract violations you want to keep long-term, or templates with complex default logic. The `mockture.ini` in this folder points at `basic_api.templates.auto.yml` as the primary templates file. A test that also needs `invalid_success_shape` from the hand-authored file overrides `templates=` on the marker directly.

## Run the tests

```bash
# Once mockture generate CLI exists:
mockture generate 07_template_authoring/configs/basic_api.openapi.yml

pytest 07_template_authoring/
```

The `.auto.yml` file is already committed as the expected generator output, so the tests run without the CLI today.

## Next steps

See [08_multi_api/](../08_multi_api/) to see how directory-scoped `mockture.ini` files let a project with multiple services keep each API's config completely independent.
