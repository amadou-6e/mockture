"""Command-line interface for mockture."""

from __future__ import annotations

import argparse
import glob as _glob
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mockture",
        description="Contract-aware in-process HTTP mocking tools.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # generate
    gen = sub.add_parser(
        "generate",
        help="Generate templates from x-mockture annotations in an OpenAPI spec.",
    )
    gen.add_argument(
        "specs",
        nargs="+",
        metavar="SPEC",
        help="OpenAPI YAML/JSON file(s); glob patterns accepted.",
    )
    gen.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output file path (only valid when a single spec is provided).",
    )
    gen.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing output files.",
    )
    gen.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated YAML to stdout; do not write any files.",
    )

    # validate
    val = sub.add_parser(
        "validate",
        help="Validate OpenAPI spec structure and local $ref resolution.",
    )
    val.add_argument("specs", nargs="+", metavar="SPEC")

    # list-templates
    lst = sub.add_parser(
        "list-templates",
        help="List templates that would be generated from x-mockture annotations.",
    )
    lst.add_argument("specs", nargs="+", metavar="SPEC")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "generate": _cmd_generate,
        "validate": _cmd_validate,
        "list-templates": _cmd_list_templates,
    }
    sys.exit(handlers[args.command](args))


# ---------------------------------------------------------------------------
# Subcommand: generate
# ---------------------------------------------------------------------------

def _cmd_generate(args: argparse.Namespace) -> int:
    spec_paths = _resolve_specs(args.specs)
    if not spec_paths:
        print("mockture generate: no matching spec files found.", file=sys.stderr)
        return 1

    if args.output and len(spec_paths) > 1:
        print(
            "mockture generate: --output can only be used with a single spec file.",
            file=sys.stderr,
        )
        return 1

    exit_code = 0
    for spec_path in spec_paths:
        out_path = Path(args.output) if args.output else _auto_output_path(spec_path)

        if not args.dry_run and not args.force and out_path.exists():
            print(f"  skip  {out_path}  (already exists; use --force to overwrite)")
            continue

        try:
            templates, required_map, skipped = _generate_from_annotations(spec_path)
        except _SpecError as exc:
            print(f"  error  {spec_path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        for endpoint in skipped:
            print(f"  skip endpoint  {endpoint}  (insufficient schema info; skipping template generation)")

        content = _render_templates_yaml(templates, spec_path, required_map)

        if args.dry_run:
            print(f"# --- {spec_path} -> {out_path} ---")
            print(content)
        else:
            out_path.write_text(content, encoding="utf-8")
            print(f"  wrote  {out_path}  ({len(templates)} template(s))")

    return exit_code


# ---------------------------------------------------------------------------
# Subcommand: validate
# ---------------------------------------------------------------------------

def _cmd_validate(args: argparse.Namespace) -> int:
    spec_paths = _resolve_specs(args.specs)
    if not spec_paths:
        print("mockture validate: no matching spec files found.", file=sys.stderr)
        return 1

    exit_code = 0
    for spec_path in spec_paths:
        print(f"Validating {spec_path} ...")
        issues: list[str] = []

        try:
            spec = _load_spec(spec_path)
        except _SpecError as exc:
            print(f"  error  {exc}")
            exit_code = 1
            continue

        print("  ok  parsed successfully")

        openapi_version = spec.get("openapi") or spec.get("swagger")
        if not openapi_version:
            issues.append("missing 'openapi' (or 'swagger') version key")
        else:
            print(f"  ok  openapi version: {openapi_version}")

        if "paths" not in spec:
            issues.append("missing top-level 'paths' key")
        else:
            path_count = len(spec["paths"])
            op_count = sum(
                1
                for path_item in spec["paths"].values()
                if isinstance(path_item, dict)
                for method in path_item
                if method.lower() in HTTP_METHODS
            )
            print(f"  ok  {path_count} path(s), {op_count} operation(s)")

        ref_issues = _check_refs(spec)
        if ref_issues:
            issues.extend(ref_issues)
        else:
            ref_count = _count_refs(spec)
            print(f"  ok  all $refs resolved ({ref_count} found)")

        if issues:
            for issue in issues:
                print(f"  error  {issue}")
            print("  Invalid.")
            exit_code = 1
        else:
            print("  Valid.")

    return exit_code


# ---------------------------------------------------------------------------
# Subcommand: list-templates
# ---------------------------------------------------------------------------

def _cmd_list_templates(args: argparse.Namespace) -> int:
    spec_paths = _resolve_specs(args.specs)
    if not spec_paths:
        print("mockture list-templates: no matching spec files found.", file=sys.stderr)
        return 1

    for spec_path in spec_paths:
        print(f"Scanning {spec_path} ...")
        try:
            spec = _load_spec(spec_path)
        except _SpecError as exc:
            print(f"  error  {exc}", file=sys.stderr)
            continue

        found = 0
        for path_value, path_item in spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                for status_str, response_obj in (operation.get("responses") or {}).items():
                    if not isinstance(response_obj, dict):
                        continue
                    template_name = response_obj.get("x-mockture-template")
                    if not template_name:
                        continue
                    print(f"  {template_name}  <-  {method.upper()} {path_value} [{status_str}]")
                    found += 1

        if found == 0:
            print("  (no x-mockture-template annotations found)")
        else:
            print(f"  {found} template(s) found.")

    return 0


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _generate_from_annotations(
    spec_path: Path,
) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    """Return (templates, required_args_map, skipped_descriptions).

    required_args_map: template_name → list of required arg names (for YAML
    comment rendering).  skipped_descriptions: human-readable list of
    endpoints that were skipped with a reason.
    """
    spec = _load_spec(spec_path)
    templates: dict[str, Any] = {}
    required_map: dict[str, list[str]] = {}
    skipped: list[str] = []

    for path_value, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            for status_str, response_obj in (operation.get("responses") or {}).items():
                if not isinstance(response_obj, dict):
                    continue
                template_name = response_obj.get("x-mockture-template")
                if not template_name:
                    continue

                try:
                    status_code = int(status_str)
                except ValueError:
                    skipped.append(
                        f"{method.upper()} {path_value} [{status_str}]"
                        f" (template: {template_name!r}) — non-integer status code"
                    )
                    continue

                defaults: dict[str, Any] = dict(response_obj.get("x-mockture-defaults") or {})
                required_args: set[str] = set(response_obj.get("x-mockture-required") or [])
                custom_body = response_obj.get("x-mockture-body")

                if custom_body is not None:
                    template, req_list = _build_custom_template(
                        method=method,
                        path_value=path_value,
                        status_code=status_code,
                        body=custom_body,
                        defaults=defaults,
                        required_args=required_args,
                    )
                else:
                    schema = _extract_schema(response_obj, spec)
                    if schema is None:
                        skipped.append(
                            f"{method.upper()} {path_value} {status_code}"
                            f" (template: {template_name!r}) — no application/json schema"
                        )
                        continue
                    if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
                        skipped.append(
                            f"{method.upper()} {path_value} {status_code}"
                            f" (template: {template_name!r}) — schema is not an object with properties"
                        )
                        continue
                    template, req_list = _build_annotated_template(
                        method=method,
                        path_value=path_value,
                        status_code=status_code,
                        schema=schema,
                        defaults=defaults,
                        required_args=required_args,
                    )

                templates[template_name] = template
                if req_list:
                    required_map[template_name] = req_list

    return templates, required_map, skipped


def _build_annotated_template(
    method: str,
    path_value: str,
    status_code: int,
    schema: dict[str, Any],
    defaults: dict[str, Any],
    required_args: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Build a template by walking schema properties.

    Arg naming priority per field:
    1. A defaults key that equals field_name exactly.
    2. A defaults key that ends with '_<field_name>' (e.g. 'order_status' for 'status').
    3. field_name itself.

    Returns (template_dict, required_arg_names).
    """
    args: dict[str, Any] = {"status_code": status_code}
    body: dict[str, Any] = {}
    consumed_defaults: set[str] = set()
    req_list: list[str] = []

    for field_name, field_schema in schema["properties"].items():
        if not isinstance(field_schema, dict):
            continue
        arg_name = _match_arg_name(field_name, defaults)
        consumed_defaults.add(arg_name)

        if arg_name in required_args:
            args[arg_name] = None
            req_list.append(arg_name)
        elif arg_name in defaults:
            args[arg_name] = defaults[arg_name]
        else:
            args[arg_name] = _infer_default(field_name, field_schema)

        body[field_name] = f"{{{arg_name}}}"

    # Any defaults keys not consumed by schema fields become extra args.
    for key, value in defaults.items():
        if key not in consumed_defaults:
            if key in required_args:
                args[key] = None
                req_list.append(key)
            else:
                args[key] = value

    return {
        "args": args,
        "interaction": {
            "method": method.upper(),
            "path": path_value,
            "response": {
                "status": "{status_code}",
                "body": body,
            },
        },
    }, req_list


def _build_custom_template(
    method: str,
    path_value: str,
    status_code: int,
    body: dict[str, Any],
    defaults: dict[str, Any],
    required_args: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Build a template using x-mockture-body, bypassing schema inference."""
    args: dict[str, Any] = {"status_code": status_code}
    req_list: list[str] = []

    for key, value in defaults.items():
        if key in required_args:
            args[key] = None
            req_list.append(key)
        else:
            args[key] = value

    return {
        "args": args,
        "interaction": {
            "method": method.upper(),
            "path": path_value,
            "response": {
                "status": "{status_code}",
                "body": deepcopy(body),
            },
        },
    }, req_list


# ---------------------------------------------------------------------------
# YAML rendering
# ---------------------------------------------------------------------------

def _render_templates_yaml(
    templates: dict[str, Any],
    spec_path: Path,
    required_map: dict[str, list[str]],
) -> str:
    header = (
        f"# Auto-generated by: mockture generate {spec_path}\n"
        "# DO NOT EDIT — regenerate from the OpenAPI spec instead.\n"
        "# Hand-authored templates live in the corresponding .templates.yml.\n"
    )
    raw = yaml.safe_dump({"templates": templates}, sort_keys=False, allow_unicode=True)

    # Replace `arg_name: null` lines with `arg_name:  # required — x-mockture-required`
    all_required = {arg for req_list in required_map.values() for arg in req_list}
    for arg_name in all_required:
        raw = re.sub(
            rf"^( +{re.escape(arg_name)}): null\n",
            rf"\1:  # required — x-mockture-required\n",
            raw,
            flags=re.MULTILINE,
        )

    return header + "\n" + raw


# ---------------------------------------------------------------------------
# Spec utilities
# ---------------------------------------------------------------------------

def _resolve_specs(patterns: list[str]) -> list[Path]:
    """Expand file paths and glob patterns; deduplicate preserving order."""
    result: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if p.exists() and p.is_file():
            result.append(p)
        else:
            result.extend(sorted(Path(m) for m in _glob.glob(pattern)))

    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in result:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(p)
    return deduped


def _auto_output_path(spec_path: Path) -> Path:
    """Derive output path: foo.openapi.yml → foo.templates.auto.yml."""
    stem = spec_path.stem  # strips last suffix
    if stem.endswith(".openapi"):
        stem = stem[: -len(".openapi")]
    return spec_path.parent / f"{stem}.templates.auto.yml"


def _load_spec(spec_path: Path) -> dict[str, Any]:
    if not spec_path.exists():
        raise _SpecError(f"file not found: {spec_path}")
    raw = spec_path.read_text(encoding="utf-8")
    try:
        if spec_path.suffix.lower() == ".json":
            import json
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw)
    except Exception as exc:
        raise _SpecError(f"failed to parse {spec_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise _SpecError(f"invalid spec {spec_path}: top-level must be a mapping")
    if "paths" not in data:
        raise _SpecError(f"invalid spec {spec_path}: missing top-level 'paths' key")
    return data


def _extract_schema(
    response_obj: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the resolved application/json schema, or None if unavailable."""
    content = response_obj.get("content")
    if not isinstance(content, dict):
        return None
    media = content.get("application/json")
    if not isinstance(media, dict):
        return None
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return None
    return _resolve_ref(spec, schema)


def _resolve_ref(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any] | None:
    """Follow a local $ref; return the resolved schema or None."""
    if "$ref" not in schema:
        return schema
    ref = schema["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    current: Any = spec
    for token in ref.removeprefix("#/").split("/"):
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current if isinstance(current, dict) else None


def _check_refs(spec: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    _walk_refs(spec, spec, issues)
    return issues


def _walk_refs(node: Any, spec: dict[str, Any], issues: list[str]) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str):
                issues.append(f"$ref is not a string: {ref!r}")
            elif not ref.startswith("#/"):
                issues.append(f"external $ref not supported: {ref!r}")
            elif _resolve_ref(spec, node) is None:
                issues.append(f"unresolvable $ref: {ref!r}")
        else:
            for value in node.values():
                _walk_refs(value, spec, issues)
    elif isinstance(node, list):
        for item in node:
            _walk_refs(item, spec, issues)


def _count_refs(spec: dict[str, Any]) -> int:
    counter = [0]
    _count_refs_in(spec, counter)
    return counter[0]


def _count_refs_in(node: Any, counter: list[int]) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            counter[0] += 1
        else:
            for value in node.values():
                _count_refs_in(value, counter)
    elif isinstance(node, list):
        for item in node:
            _count_refs_in(item, counter)


# ---------------------------------------------------------------------------
# Arg inference
# ---------------------------------------------------------------------------

def _match_arg_name(field_name: str, defaults: dict[str, Any]) -> str:
    """Resolve the arg name for a schema field against x-mockture-defaults keys.

    Priority:
    1. Exact match: defaults key == field_name.
    2. Suffix match: defaults key ends with '_<field_name>' (e.g. 'order_status' → 'status').
    3. Fallback: field_name itself.
    """
    if field_name in defaults:
        return field_name
    for key in defaults:
        if key.endswith(f"_{field_name}"):
            return key
    return field_name


def _infer_default(field_name: str, field_schema: dict[str, Any]) -> Any:
    """Infer a default value from schema — no domain-specific overrides."""
    if "example" in field_schema:
        return field_schema["example"]
    if "default" in field_schema:
        return field_schema["default"]
    if isinstance(field_schema.get("enum"), list) and field_schema["enum"]:
        return field_schema["enum"][0]
    schema_type = field_schema.get("type")
    if schema_type == "string":
        return ""
    if schema_type in {"integer", "number"}:
        return 0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        return []
    if schema_type == "object":
        return {}
    return None


# ---------------------------------------------------------------------------
# Internal exception
# ---------------------------------------------------------------------------

class _SpecError(Exception):
    """Raised when a spec file cannot be loaded or parsed."""


if __name__ == "__main__":
    main()
