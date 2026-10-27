#!/usr/bin/env python3
"""Verify a public bundle and replay saved choices; never generate AI choices."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types

sys.dont_write_bytecode = True
MANIFEST_NAME = "MANIFEST.json"
PINNED_CODE = {
    "action_loop.py": "61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297",
    "experience_io.py": "e66ca22700b19a6bae4340561bb5183473b605b8a07bb6e61f0c1bcb4ab78543",
}
PLAN_FIELDS = {"key", "task_id", "source", "map", "action_file", "action_selector",
               "policy_file", "policy_selector", "expected_file", "expected_result", "inspection_file"}
RESULT_FIELDS = {"id", "execution_status", "validation_status", "artifact_sha256", "error"}


class ReplayError(Exception):
    """A manifest, plan, or replay violates the frozen mechanical contract."""


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReplayError("duplicate JSON object key")
        value[key] = item
    return value


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ReplayError("nonfinite JSON number")
    return value


def _reject_constant(text):
    raise ReplayError("nonfinite JSON constant: " + text)


def read_json(path):
    value = json.loads(Path(path).read_bytes().decode("utf-8"), object_pairs_hook=_unique_object,
                       parse_float=_finite_float, parse_constant=_reject_constant)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            item.encode("utf-8")
        elif type(item) is dict:
            pending.extend(item)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return value


def write_new_json(path, value):
    raw = (canonical_json(value) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


def exact_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(exact_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(exact_equal(a, b) for a, b in zip(left, right))
    if type(left) is float:
        return left.hex() == right.hex()
    return left == right


def safe_name(name):
    if type(name) is not str or not name or "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return (bool(path.parts) and not path.is_absolute() and path.as_posix() == name
            and not any(p in {"", ".", ".."} for p in path.parts)
            and not re.match(r"^[A-Za-z]:", name))


def valid_digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def verify_manifest(bundle):
    """Hash every regular file before importing any bundled code."""
    if bundle.is_symlink() or not bundle.is_dir():
        raise ReplayError("bundle must be a regular directory")
    manifest_path = bundle / MANIFEST_NAME
    if not stat.S_ISREG(manifest_path.lstat().st_mode):
        raise ReplayError("manifest must be a regular file")
    manifest_raw = manifest_path.read_bytes()
    manifest = read_json(manifest_path)
    if (type(manifest) is not dict or set(manifest) != {"schema_version", "files"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1):
        raise ReplayError("unsupported manifest schema")
    files = manifest["files"]
    if type(files) is not dict or not files or MANIFEST_NAME in files:
        raise ReplayError("manifest must list all files except itself")
    for name, record in files.items():
        if (not safe_name(name) or type(record) is not dict or set(record) != {"sha256", "bytes"}
                or not valid_digest(record["sha256"]) or type(record["bytes"]) is not int or record["bytes"] < 0):
            raise ReplayError("invalid manifest entry: " + repr(name))
    actual = set()
    for path in bundle.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ReplayError("bundle symlinks are forbidden")
        if stat.S_ISREG(mode):
            name = path.relative_to(bundle).as_posix()
            if name != MANIFEST_NAME:
                actual.add(name)
        elif not stat.S_ISDIR(mode):
            raise ReplayError("nonregular bundle entry")
    if actual != set(files):
        raise ReplayError("manifest file set differs; missing=" + repr(sorted(set(files) - actual)) + "; extra=" + repr(sorted(actual - set(files))))
    for name, record in files.items():
        raw = (bundle / name).read_bytes()
        if len(raw) != record["bytes"] or sha256(raw) != record["sha256"]:
            raise ReplayError("manifest SHA256/size mismatch: " + name)
    required = set(PINNED_CODE) | {"replay.py", "replay_plan.json"}
    required |= {"input/environment/source_map_" + name + ".json" for name in ("original", "changed", "probes")}
    if not required <= actual:
        raise ReplayError("required bundle files missing")
    for name, expected in PINNED_CODE.items():
        if files[name]["sha256"] != expected:
            raise ReplayError("pinned code differs: " + name)
    return ({"status": "verified", "manifest_sha256": sha256(manifest_raw),
             "verified_files_excluding_manifest": len(actual), "files_including_manifest": len(actual) + 1,
             "pinned_code_verified": True}, files)


def _listed_path(bundle, inventory, name):
    if not safe_name(name) or name not in inventory:
        raise ReplayError("plan path must name a manifest-listed file: " + repr(name))
    return bundle / name


def _select(value, selector, label):
    if selector is None and type(value) is dict:
        return value
    if type(selector) is int and selector >= 0 and type(value) is list and selector < len(value) and type(value[selector]) is dict:
        return value[selector]
    raise ReplayError("selector must be null for an object or a nonnegative integer for an array: " + label)


def prepare_plan(bundle, inventory):
    plan = read_json(bundle / "replay_plan.json")
    if (type(plan) is not dict or set(plan) != {"schema_version", "entries"}
            or type(plan["schema_version"]) is not int or plan["schema_version"] != 1
            or type(plan["entries"]) is not list or not plan["entries"]):
        raise ReplayError("invalid replay plan schema")
    prepared, keys = [], set()
    for entry in plan["entries"]:
        if (type(entry) is not dict or set(entry) != PLAN_FIELDS or type(entry["key"]) is not str
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", entry["key"]) or entry["key"] in keys
                or type(entry["task_id"]) is not str or not entry["task_id"]
                or type(entry["source"]) is not str or not entry["source"]
                or entry["map"] not in {"original", "changed", "probes"}):
            raise ReplayError("invalid, unsafe, or duplicate replay entry")
        keys.add(entry["key"])
        action_path = _listed_path(bundle, inventory, entry["action_file"])
        policy_path = _listed_path(bundle, inventory, entry["policy_file"])
        expected_path = _listed_path(bundle, inventory, entry["expected_file"])
        action = _select(read_json(action_path), entry["action_selector"], "action")
        policy = _select(read_json(policy_path), entry["policy_selector"], "policy")
        if action.get("id") != entry["task_id"] or policy.get("id") != entry["task_id"]:
            raise ReplayError("policy/action id must match task_id")
        # Preserve an actually invalid action for the engine's real validation;
        # replay does not repair or pre-empt its recorded invalid_action result.
        if policy.get("decision") == "inspect":
            if set(policy) != {"id", "decision", "rationale"} or type(policy["rationale"]) is not str or entry["inspection_file"] is None:
                raise ReplayError("inspect policy requires one saved requested inspection")
        elif policy.get("decision") == "submit":
            if (set(policy) != {"id", "decision", "action"} or entry["inspection_file"] is not None
                    or not exact_equal(policy["action"], action)):
                raise ReplayError("submit policy must lock the saved action and have no inspection")
        else:
            raise ReplayError("invalid saved policy decision")
        gold = read_json(expected_path)
        if type(gold) is not dict or entry["task_id"] not in gold:
            raise ReplayError("expected_file must be a gold object keyed by task_id")
        expected = entry["expected_result"]
        if (type(expected) is not dict or set(expected) != RESULT_FIELDS or expected["id"] != entry["task_id"]
                or expected["execution_status"] not in {"ok", "unavailable", "invalid_action", "execution_error"}
                or expected["validation_status"] not in {"accepted", "rejected"}
                or (expected["artifact_sha256"] is not None and not valid_digest(expected["artifact_sha256"]))):
            raise ReplayError("invalid expected_result")
        error = expected["error"]
        if error is not None and (type(error) is not dict or set(error) != {"type", "message"} or any(type(v) is not str for v in error.values())):
            raise ReplayError("expected error must be null or exact type/message")
        map_path = bundle / "input/environment" / ("source_map_" + entry["map"] + ".json")
        mapping = read_json(map_path)
        if type(mapping) is not dict or entry["source"] not in mapping or type(mapping[entry["source"]]) is not str:
            raise ReplayError("assigned source alias missing from selected map")
        relative = mapping[entry["source"]]
        if not relative or Path(relative).is_absolute() or "\\" in relative or "\x00" in relative:
            raise ReplayError("source map target must be relative")
        target = (map_path.parent / relative).resolve(strict=True)
        try:
            target_name = target.relative_to(bundle).as_posix()
        except ValueError as exc:
            raise ReplayError("source map target escapes bundle") from exc
        _listed_path(bundle, inventory, target_name)
        inspection = None
        if entry["inspection_file"] is not None:
            inspection_path = _listed_path(bundle, inventory, entry["inspection_file"])
            inspection = read_json(inspection_path)
            if type(inspection) is not dict or inspection.get("source") != entry["source"]:
                raise ReplayError("saved inspection source differs from assigned source")
            for field in ("raw_bytes_read", "returned_canonical_characters"):
                if type(inspection.get(field)) is not int or inspection[field] < 0:
                    raise ReplayError("saved inspection cost must be a nonnegative integer")
            if not valid_digest(inspection.get("raw_sha256")):
                raise ReplayError("saved inspection raw source SHA is invalid")
        prepared.append({"entry": entry, "action": action, "gold": gold[entry["task_id"]], "map_path": map_path,
                         "target": target, "inspection": inspection})
    return prepared


def _compile_verified(bundle, name, module_name):
    path = bundle / name
    raw = path.read_bytes()
    if sha256(raw) != PINNED_CODE[name]:
        raise ReplayError("pinned code changed after verification: " + name)
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def load_modules(bundle):
    engine = _compile_verified(bundle, "action_loop.py", "verified_action_loop")
    sentinel = object()
    previous = sys.modules.get("action_loop", sentinel)
    sys.modules["action_loop"] = engine
    try:
        apparatus = _compile_verified(bundle, "experience_io.py", "verified_experience_io")
    finally:
        if previous is sentinel:
            del sys.modules["action_loop"]
        else:
            sys.modules["action_loop"] = previous
    return engine, apparatus


def replay(bundle, output, report):
    report["bundle_verification"], inventory = verify_manifest(bundle)
    prepared = prepare_plan(bundle, inventory)
    engine, apparatus = load_modules(bundle)
    (output / "assigned_inputs").mkdir(mode=0o700)
    (output / "inspections").mkdir(mode=0o700)
    items, inspections = [], []
    for saved in prepared:
        entry, action = saved["entry"], saved["action"]
        key = entry["key"]
        if saved["inspection"] is not None:
            generated_path = output / "inspections" / (key + ".json")
            actual = apparatus.inspect_source(saved["map_path"], entry["source"], generated_path)
            recorded_path = bundle / entry["inspection_file"]
            saved_record = saved["inspection"]
            matches = {field: exact_equal(actual[field], saved_record.get(field))
                       for field in ("source", "raw_sha256", "raw_bytes_read", "returned_canonical_characters")}
            actual_hash, recorded_hash = sha256(generated_path.read_bytes()), sha256(recorded_path.read_bytes())
            matches["raw_inspection_json_sha256"] = actual_hash == recorded_hash
            inspections.append({"key": key, "source": entry["source"], "actual_sha256": actual_hash,
                                "recorded_sha256": recorded_hash, "raw_bytes_read": actual["raw_bytes_read"],
                                "returned_canonical_characters": actual["returned_canonical_characters"],
                                "matches": matches, "all_match": all(matches.values())})
        prefix = output / "assigned_inputs" / key
        map_path, action_path, gold_path = (Path(str(prefix) + suffix) for suffix in ("-map.json", "-action.json", "-gold.json"))
        write_new_json(map_path, {entry["source"]: str(saved["target"])})
        write_new_json(action_path, [action])
        write_new_json(gold_path, {entry["task_id"]: saved["gold"]})
        summary = engine.run_batch(map_path, action_path, gold_path, output / ("run-" + key))
        if len(summary["items"]) != 1:
            raise ReplayError("each assigned run must contain exactly one item")
        item = summary["items"][0]
        item_dir = output / ("run-" + key) / item["directory"]
        execution = read_json(item_dir / "execution.json")
        artifact_path = item_dir / "artifact.json"
        actual_hash = sha256(artifact_path.read_bytes()) if artifact_path.is_file() else None
        actual = {"id": item["id"], "execution_status": item["execution_status"],
                  "validation_status": item["validation_status"], "artifact_sha256": actual_hash, "error": execution["error"]}
        expected = entry["expected_result"]
        matches = {field: exact_equal(actual[field], expected[field]) for field in RESULT_FIELDS}
        matches["execution_artifact_sha256"] = actual_hash == execution["artifact_sha256"] == item["artifact_sha256"]
        matches["one_assigned_source_only"] = set(execution["input_hashes"]["sources"]) == {entry["source"]}
        items.append({"key": key, "task_id": entry["task_id"], "source": entry["source"], "actual": actual,
                      "expected": expected, "matches": matches, "all_match": all(matches.values()),
                      "budget_exceeded": item["budget_exceeded"]})
    artifacts = [item for item in items if item["expected"]["artifact_sha256"] is not None]
    errors = [item for item in items if item["expected"]["error"] is not None]
    report.update(item_comparisons=items, inspection_comparisons=inspections, items_compared=len(items),
                  items_matching=sum(item["all_match"] for item in items), expected_artifacts=len(artifacts),
                  generated_artifacts=sum(item["actual"]["artifact_sha256"] is not None for item in items),
                  generated_artifact_sha256_match_count=sum(item["matches"]["artifact_sha256"] for item in artifacts),
                  expected_errors=len(errors), expected_errors_preserved=sum(item["all_match"] for item in errors),
                  inspections_compared=len(inspections), inspections_matching=sum(item["all_match"] for item in inspections),
                  actual_inspection_raw_bytes=sum(item["raw_bytes_read"] for item in inspections),
                  actual_inspection_returned_characters=sum(item["returned_canonical_characters"] for item in inspections),
                  budget_violations=sum(item["budget_exceeded"] for item in items))
    report["status"] = "passed" if all(item["all_match"] for item in items + inspections) else "failed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="absolute new directory outside the bundle")
    parser.add_argument("--bundle", type=Path, help="defaults to this script's parent")
    args = parser.parse_args(argv)
    report = {"schema_version": 1, "status": "failed", "started_at_utc": utc_now(), "finished_at_utc": None,
              "choices_source": "saved_bundle_actions_and_policies", "fresh_ai_choices_generated": False,
              "replay_scope": "Saved requested inspections and saved actions only; no fresh AI choices or delayed collection.",
              "bundle_verification": {"status": "not_verified"}, "error": None}
    created = False
    output = Path(args.out).expanduser()
    try:
        bundle_arg = args.bundle if args.bundle is not None else Path(__file__).parent
        if bundle_arg.is_symlink():
            raise ReplayError("bundle root must not be a symlink")
        bundle = bundle_arg.resolve(strict=True)
        if not output.is_absolute():
            raise ReplayError("output must be absolute")
        try:
            output.lstat()
        except FileNotFoundError:
            pass
        else:
            raise ReplayError("output already exists")
        output = output.resolve()
        if output == bundle or bundle in output.parents:
            raise ReplayError("output must be outside the bundle")
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        created = True
        replay(bundle, output, report)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    report["finished_at_utc"] = utc_now()
    if created:
        try:
            write_new_json(output / "replay_verification.json", report)
        except Exception as exc:
            report["status"] = "failed"
            report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    print(canonical_json(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
