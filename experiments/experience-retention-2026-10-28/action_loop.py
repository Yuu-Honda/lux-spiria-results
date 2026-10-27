#!/usr/bin/env python3
"""Bounded JSON actions, actual file artifacts, and a mechanical validator.

The caller supplies every source, action, and independent expected result. This
module provides no research questions, source selection, expected answers,
semantic interpretation, or learning/accuracy conclusions.

All inputs are read once. Actions can access only the resulting in-memory source
snapshot. Every output path must be new; item directories use sequence numbers
so that action IDs can never select filesystem paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
from typing import Any


ACTION_CHARACTER_LIMIT = 6000
FLOAT_ABSOLUTE_TOLERANCE = 1e-12


class HarnessError(Exception):
    """A malformed run configuration or an unavailable output destination."""


class ActionError(Exception):
    """An invalid expression or a failed action execution."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    """Canonical representation used for action hashes and character accounting."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def error_record(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite JSON number")
    return value


def _reject_constant(text: str) -> Any:
    raise ValueError("nonfinite JSON constant: " + text)


def parse_json(raw: bytes) -> Any:
    """Reject duplicate keys, NaN/Infinity, overflowed floats, and invalid UTF-8."""
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_float=_finite_float,
        parse_constant=_reject_constant,
    )
    # Escaped unpaired surrogates can survive json.loads but cannot be written
    # as UTF-8. Reject them at the input boundary, where a failure can be saved.
    pending = [value]
    while pending:
        part = pending.pop()
        if type(part) is str:
            part.encode("utf-8")
        elif type(part) is dict:
            pending.extend(part)
            pending.extend(part.values())
        elif type(part) is list:
            pending.extend(part)
    return value


def _read_input(path: Path, label: str, input_hashes: dict[str, Any]) -> Any:
    try:
        raw = path.read_bytes()
    except (OSError, ValueError) as exc:
        input_hashes[label] = {"path": str(path), "sha256": None, "error": error_record(exc)}
        raise HarnessError("cannot read " + label + ": " + str(exc)) from exc
    input_hashes[label] = {"path": str(path), "sha256": sha256_bytes(raw), "error": None}
    try:
        return parse_json(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        input_hashes[label]["error"] = error_record(exc)
        raise HarnessError("invalid " + label + " JSON: " + str(exc)) from exc


def _write_new_json(path: Path, value: Any) -> str:
    raw = (canonical_json(value) + "\n").encode("utf-8")
    # Exclusive creation is deliberate: no output may replace a previous result.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
    return sha256_bytes(raw)


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise ActionError(label + " must contain exactly: " + ", ".join(sorted(keys)))


def _number(value: Any) -> int | float:
    if type(value) not in (int, float):
        raise ActionError("arithmetic requires numbers; booleans are not numbers")
    if type(value) is float and not math.isfinite(value):
        raise ActionError("nonfinite arithmetic value")
    return value


def _leaf(value: Any) -> bool:
    return value is None or type(value) in (str, bool, int) or (type(value) is float and math.isfinite(value))


def _validate_expression(expression: Any) -> None:
    if type(expression) is not dict or type(expression.get("op")) is not str:
        raise ActionError("expression must be an object with a string op")
    operation = expression["op"]
    if operation == "get":
        _exact_keys(expression, {"op", "source", "path"}, "get expression")
        if type(expression["source"]) is not str or not expression["source"]:
            raise ActionError("get source must be a nonempty alias")
        if type(expression["path"]) is not list:
            raise ActionError("get path must be a list")
        if any(type(part) not in (str, int) for part in expression["path"]):
            raise ActionError("path elements must be exact strings or integers, never booleans")
    elif operation == "sum":
        _exact_keys(expression, {"op", "args"}, "sum expression")
        if type(expression["args"]) is not list or not expression["args"]:
            raise ActionError("sum args must be a nonempty list")
        for argument in expression["args"]:
            _validate_expression(argument)
    elif operation in ("sub", "div"):
        _exact_keys(expression, {"op", "left", "right"}, operation + " expression")
        _validate_expression(expression["left"])
        _validate_expression(expression["right"])
    else:
        raise ActionError("unsupported expression operation")


def validate_action(action: Any) -> None:
    _exact_keys(action, {"id", "prediction", "rationale", "status", "fields"}, "action")
    if type(action["id"]) is not str or not action["id"]:
        raise ActionError("action id must be a nonempty string")
    if type(action["prediction"]) is not str or action["prediction"] not in {"accepted", "rejected", "uncertain"}:
        raise ActionError("prediction must be accepted, rejected, or uncertain")
    if type(action["rationale"]) is not str:
        raise ActionError("rationale must be a string")
    if type(action["status"]) is not str or action["status"] not in {"write", "unavailable"}:
        raise ActionError("action status must be write or unavailable")
    if type(action["fields"]) is not dict:
        raise ActionError("fields must be an object")
    if action["status"] == "unavailable":
        if action["fields"]:
            raise ActionError("unavailable action requires empty fields")
    else:
        for expression in action["fields"].values():
            _validate_expression(expression)


def _resolve_get(expression: dict[str, Any], sources: dict[str, Any], source_errors: dict[str, Any]) -> Any:
    alias = expression["source"]
    if alias not in sources:
        if alias in source_errors:
            raise ActionError("source alias is unavailable: " + alias)
        raise ActionError("unknown source alias: " + alias)
    value = sources[alias]
    for part in expression["path"]:
        if type(value) is dict:
            if type(part) is not str:
                raise ActionError("object path element must be a string")
            if part not in value:
                raise ActionError("object path key is missing")
            value = value[part]
        elif type(value) is list:
            if type(part) is not int:
                raise ActionError("list path element must be an integer, never a boolean")
            if not 0 <= part < len(value):
                raise ActionError("list path index is out of range")
            value = value[part]
        else:
            raise ActionError("path traverses a scalar value")
    return value


def evaluate_expression(expression: dict[str, Any], sources: dict[str, Any], source_errors: dict[str, Any]) -> Any:
    operation = expression["op"]
    if operation == "get":
        return _resolve_get(expression, sources, source_errors)
    if operation == "sum":
        value: int | float = 0
        for argument in expression["args"]:
            value = _number(value + _number(evaluate_expression(argument, sources, source_errors)))
        return value
    left = _number(evaluate_expression(expression["left"], sources, source_errors))
    right = _number(evaluate_expression(expression["right"], sources, source_errors))
    if operation == "sub":
        return _number(left - right)
    if operation == "div":
        if right == 0:
            raise ActionError("division by zero")
        return _number(left / right)
    raise ActionError("unsupported expression operation")


def execute_action(action: dict[str, Any], sources: dict[str, Any], source_errors: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a validated action; writing the actual artifact is run_batch's job."""
    if action["status"] == "unavailable":
        return {"status": "unavailable", "values": None}
    values = {}
    for name, expression in action["fields"].items():
        value = evaluate_expression(expression, sources, source_errors)
        if not _leaf(value):
            raise ActionError("final field must be a finite scalar JSON value")
        values[name] = value
    return {"status": "ok", "values": values}


def _validate_expected(expected: Any) -> None:
    if type(expected) is not dict:
        raise HarnessError("expected results must be an object keyed by task id")
    for task_id, record in expected.items():
        if not task_id:
            raise HarnessError("expected task ids must be nonempty strings")
        try:
            _exact_keys(record, {"status", "values"}, "expected result")
            if type(record["status"]) is not str or record["status"] not in {"ok", "unavailable"}:
                raise ActionError("expected status must be ok or unavailable")
            if record["status"] == "unavailable":
                if record["values"] is not None:
                    raise ActionError("unavailable expected result requires null values")
            elif type(record["values"]) is not dict or not all(_leaf(value) for value in record["values"].values()):
                raise ActionError("ok expected result requires an object of finite scalar values")
        except ActionError as exc:
            raise HarnessError("invalid expected result for task " + task_id + ": " + str(exc)) from exc


def _preflight_ids(actions: Any, expected: dict[str, Any]) -> None:
    if type(actions) is not list:
        raise HarnessError("actions must be a JSON list")
    ids = []
    for action in actions:
        if type(action) is not dict or type(action.get("id")) is not str or not action["id"]:
            raise HarnessError("every action must have a nonempty string id before execution")
        ids.append(action["id"])
    if len(ids) != len(set(ids)):
        raise HarnessError("duplicate action ids; no actions executed")
    if set(ids) != set(expected):
        raise HarnessError("action ids and expected result ids do not match; no actions executed")


def _snapshot_sources(source_map: Any, map_path: Path, input_hashes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source_map) is not dict:
        raise HarnessError("sources map must be an object mapping aliases to JSON paths")
    for alias, path in source_map.items():
        if not alias or type(path) is not str or not path:
            raise HarnessError("source aliases and paths must be nonempty strings")
    sources: dict[str, Any] = {}
    errors: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    input_hashes["sources"] = manifest
    for alias, source_path in source_map.items():
        path = Path(source_path)
        if not path.is_absolute():
            path = map_path.parent / path
        path = path.resolve()
        record: dict[str, Any] = {"path": str(path), "sha256": None, "error": None}
        manifest[alias] = record
        try:
            raw = path.read_bytes()
            record["sha256"] = sha256_bytes(raw)
            sources[alias] = parse_json(raw)
        except (OSError, ValueError, UnicodeError, RecursionError) as exc:
            record["error"] = error_record(exc)
            errors[alias] = record["error"]
    return sources, errors


def compare_values(actual: Any, expected: Any, path: str = "$") -> list[str]:
    """Strict JSON types, exact structure, and absolute tolerance for floats only."""
    if type(actual) is not type(expected):
        return [path + ": type mismatch"]
    if type(actual) is dict:
        if set(actual) != set(expected):
            return [path + ": object keys differ"]
        differences: list[str] = []
        for key in sorted(actual):
            differences.extend(compare_values(actual[key], expected[key], path + "[" + json.dumps(key, ensure_ascii=False) + "]"))
        return differences
    if type(actual) is list:
        if len(actual) != len(expected):
            return [path + ": list lengths differ"]
        differences = []
        for index, (left, right) in enumerate(zip(actual, expected)):
            differences.extend(compare_values(left, right, path + "[" + str(index) + "]"))
        return differences
    if type(actual) is float:
        if not math.isfinite(actual) or not math.isfinite(expected):
            return [path + ": nonfinite float"]
        return [] if abs(actual - expected) <= FLOAT_ABSOLUTE_TOLERANCE else [path + ": float differs"]
    return [] if actual == expected else [path + ": value differs"]


def validate_artifact(artifact_path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    """Reopen and parse the actual saved artifact before mechanical comparison."""
    started = utc_now()
    try:
        raw = artifact_path.read_bytes()
        actual = parse_json(raw)
        differences = compare_values(actual, expected)
        return {
            "status": "accepted" if not differences else "rejected",
            "differences": differences,
            "error": None,
            "artifact_sha256": sha256_bytes(raw),
            "checked_at_utc": started,
            "comparison": {"strict_types": True, "float_absolute_tolerance": FLOAT_ABSOLUTE_TOLERANCE},
        }
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        return {
            "status": "rejected",
            "differences": [],
            "error": error_record(exc),
            "artifact_sha256": None,
            "checked_at_utc": started,
            "comparison": {"strict_types": True, "float_absolute_tolerance": FLOAT_ABSOLUTE_TOLERANCE},
        }


def _run_item(index: int, action: dict[str, Any], expected: dict[str, Any], output: Path,
              sources: dict[str, Any], source_errors: dict[str, Any], input_hashes: dict[str, Any]) -> dict[str, Any]:
    serialized = canonical_json(action)
    directory = "item-" + str(index).zfill(4)
    item_path = output / directory
    item_path.mkdir(mode=0o700)
    execution: dict[str, Any] = {
        "id": action["id"],
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "raw_status": None,
        "error": None,
        "input_hashes": input_hashes,
        "action_sha256": sha256_bytes(serialized.encode("utf-8")),
        "artifact_sha256": None,
        "canonical_characters": len(serialized),
        "budget_limit": ACTION_CHARACTER_LIMIT,
        "budget_exceeded": len(serialized) > ACTION_CHARACTER_LIMIT,
    }
    artifact_path = item_path / "artifact.json"
    try:
        validate_action(action)
    except (ActionError, ValueError, TypeError, RecursionError) as exc:
        execution["raw_status"] = "invalid_action"
        execution["error"] = error_record(exc)
    else:
        try:
            artifact = execute_action(action, sources, source_errors)
            execution["artifact_sha256"] = _write_new_json(artifact_path, artifact)
            execution["raw_status"] = artifact["status"]
        except (ActionError, ArithmeticError, ValueError, TypeError, RecursionError, OSError) as exc:
            execution["raw_status"] = "execution_error"
            execution["error"] = error_record(exc)
    execution["finished_at_utc"] = utc_now()
    _write_new_json(item_path / "execution.json", execution)
    validation = validate_artifact(artifact_path, expected)
    _write_new_json(item_path / "validation.json", validation)
    return {
        "id": action["id"],
        "directory": directory,
        "prediction": action.get("prediction"),
        "execution_status": execution["raw_status"],
        "validation_status": validation["status"],
        "canonical_characters": execution["canonical_characters"],
        "budget_exceeded": execution["budget_exceeded"],
        "action_sha256": execution["action_sha256"],
        "artifact_sha256": execution["artifact_sha256"],
    }


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "items": len(items),
        "accepted": sum(item["validation_status"] == "accepted" for item in items),
        "rejected": sum(item["validation_status"] == "rejected" for item in items),
        "artifacts_written": sum(item["artifact_sha256"] is not None for item in items),
        "invalid_actions": sum(item["execution_status"] == "invalid_action" for item in items),
        "execution_errors": sum(item["execution_status"] == "execution_error" for item in items),
        "budget_exceeded": sum(item["budget_exceeded"] for item in items),
    }


def run_batch(sources_map_path: str | Path, actions_path: str | Path,
              expected_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    """Run caller-authored actions once, retaining successes and all failures.

    Configuration errors raise HarnessError after saving a failed run_summary in
    the new output directory. An existing output directory is never modified.
    A valid batch returns a summary even if individual actions are rejected.
    """
    output = Path(out_path).absolute()
    try:
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
    except (OSError, ValueError) as exc:
        raise HarnessError("output directory must be new: " + str(exc)) from exc
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "input_hashes": {},
        "items": [],
        "counts": _counts([]),
        "error": None,
        "policy": {
            "action_character_limit": ACTION_CHARACTER_LIMIT,
            "budget_behavior": "flag_only_no_truncation_no_retry",
            "strict_json_types": True,
            "float_absolute_tolerance": FLOAT_ABSOLUTE_TOLERANCE,
            "prediction_comparison": "external",
        },
    }
    try:
        map_path = Path(sources_map_path).absolute()
        source_map = _read_input(map_path, "sources_map", summary["input_hashes"])
        actions = _read_input(Path(actions_path).absolute(), "actions", summary["input_hashes"])
        expected = _read_input(Path(expected_path).absolute(), "expected", summary["input_hashes"])
        _validate_expected(expected)
        _preflight_ids(actions, expected)
        sources, source_errors = _snapshot_sources(source_map, map_path, summary["input_hashes"])
        for index, action in enumerate(actions, 1):
            summary["items"].append(_run_item(index, action, expected[action["id"]], output,
                                               sources, source_errors, summary["input_hashes"]))
        summary["status"] = "completed"
    except (HarnessError, OSError, ValueError, TypeError, RecursionError) as exc:
        summary["status"] = "failed"
        summary["error"] = error_record(exc)
        summary["counts"] = _counts(summary["items"])
        summary["finished_at_utc"] = utc_now()
        _write_new_json(output / "run_summary.json", summary)
        if isinstance(exc, HarnessError):
            raise
        raise HarnessError("run failed: " + str(exc)) from exc
    summary["counts"] = _counts(summary["items"])
    summary["finished_at_utc"] = utc_now()
    _write_new_json(output / "run_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="execute frozen-source actions in a new output directory")
    run.add_argument("--sources", required=True, help="JSON source-alias to path map; paths relative to map file")
    run.add_argument("--actions", required=True, help="caller-authored JSON action list")
    run.add_argument("--expected", required=True, help="independently authored expected results keyed by action id")
    run.add_argument("--out", required=True, help="output directory that does not yet exist")
    args = parser.parse_args(argv)
    try:
        summary = run_batch(args.sources, args.actions, args.expected, args.out)
    except HarnessError as exc:
        print(canonical_json({"status": "failed", "error": error_record(exc)}), file=sys.stderr)
        return 2
    print(canonical_json(summary))
    return 1 if summary["counts"]["rejected"] or summary["counts"]["budget_exceeded"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
