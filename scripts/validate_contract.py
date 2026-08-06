from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "contracts" / "openapi.yaml"
EVENT_SCHEMA_PATH = ROOT / "contracts" / "events.schema.json"
PROMPT_PATH = ROOT / "PROJECT_MASTER_PROMPT.md"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def fail(message: str) -> None:
    raise AssertionError(message)


def operations(document: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    result: list[tuple[str, str, dict[str, Any]]] = []
    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                result.append((method.upper(), path, operation))
    return result


def prompt_endpoints() -> set[tuple[str, str]]:
    pattern = re.compile(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \|", re.MULTILINE)
    return {(match.group(1), match.group(2)) for match in pattern.finditer(PROMPT_PATH.read_text(encoding="utf-8"))}


def parameter_refs(operation: dict[str, Any]) -> set[str]:
    return {
        parameter["$ref"]
        for parameter in operation.get("parameters", [])
        if isinstance(parameter, dict) and "$ref" in parameter
    }


def validate_openapi(document: dict[str, Any]) -> None:
    validate_spec(document)
    all_operations = operations(document)
    if len(all_operations) != 158:
        fail(f"OpenAPI must contain 158 operations, found {len(all_operations)}")

    prompt_set = prompt_endpoints()
    contract_set = {(method, path) for method, path, _ in all_operations}
    if prompt_set != contract_set:
        missing = sorted(prompt_set - contract_set)
        extra = sorted(contract_set - prompt_set)
        fail(f"OpenAPI and master prompt endpoint sets differ; missing={missing}, extra={extra}")

    operation_ids = [operation["operationId"] for _, _, operation in all_operations]
    if len(operation_ids) != len(set(operation_ids)):
        fail("operationId values must be globally unique")

    for method, path, operation in all_operations:
        for extension in ["x-backend-owner", "x-frontend-owner", "x-permission"]:
            if not operation.get(extension):
                fail(f"{method} {path} is missing {extension}")
        if "TODO" in json.dumps(operation, ensure_ascii=False) or "FIXME" in json.dumps(operation, ensure_ascii=False):
            fail(f"{method} {path} contains unfinished marker")
        if method == "PATCH" and "#/components/parameters/IfMatch" not in parameter_refs(operation):
            fail(f"PATCH {path} must require If-Match")
        for name in re.findall(r"{([A-Za-z][A-Za-z0-9]*)}", path):
            matching = [
                parameter
                for parameter in operation.get("parameters", [])
                if parameter.get("name") == name and parameter.get("in") == "path" and parameter.get("required") is True
            ]
            if not matching:
                fail(f"{method} {path} is missing required path parameter {name}")
        success_responses = [code for code in operation["responses"] if code.startswith("2")]
        if len(success_responses) != 1:
            fail(f"{method} {path} must have exactly one success response")
        success = operation["responses"][success_responses[0]]
        if success.get("headers", {}).get("X-Request-Id") is None:
            fail(f"{method} {path} success response must return X-Request-Id")

    for name, response in document["components"]["responses"].items():
        if response.get("headers", {}).get("X-Request-Id") is None:
            fail(f"shared error response {name} must return X-Request-Id")


def validate_json_example(document: dict[str, Any], schema_name: str, example_name: str) -> None:
    example = json.loads((ROOT / "contracts" / "examples" / example_name).read_text(encoding="utf-8"))
    contract_uri = "urn:bid-platform:openapi"
    registry = Registry().with_resource(
        contract_uri,
        Resource.from_contents(document, default_specification=DRAFT202012),
    )
    validator = Draft202012Validator(
        {"$ref": f"{contract_uri}#/components/schemas/{schema_name}"},
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(example), key=lambda item: list(item.path))
    if errors:
        details = "; ".join(error.message for error in errors)
        fail(f"{example_name} does not match {schema_name}: {details}")


def validate_events() -> None:
    schema = json.loads(EVENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    example = json.loads(
        (ROOT / "contracts" / "examples" / "realtime-job-progress.json").read_text(encoding="utf-8")
    )
    errors = sorted(validator.iter_errors(example), key=lambda item: list(item.path))
    if errors:
        fail("realtime event example is invalid: " + "; ".join(error.message for error in errors))


def main() -> int:
    document = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    validate_openapi(document)
    validate_json_example(document, "CreateBidTaskRequest", "create-bid-task.request.json")
    validate_json_example(document, "CreateEvaluationDraftRequest", "create-evaluation.request.json")
    validate_events()
    print("[OK] OpenAPI: 158 unique operations, owners, headers, concurrency and prompt parity")
    print("[OK] Request examples and realtime event schema")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, TypeError, ValueError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(1) from error
