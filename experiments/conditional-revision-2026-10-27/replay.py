#!/usr/bin/env python3
"""Verify a bundle, replay its saved choices, and compare recorded outcomes.

This program does not generate AI choices. It re-executes the supplied saved
actions with the bundled deterministic action engine in a new external folder.
"""

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
from typing import Any

sys.dont_write_bytecode = True

ALIASES = ("D01", "D02", "D03")
FROZEN_CODE_SHA256 = {
    "action_loop.py": "61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297",
    "test_action_loop.py": "a7485fe3f91b47e01d9b710dd935d5784254af53bc3e02c99e47097e8f12fbb5",
    "migration.py": "5bc8f53b91e731c42a690a012227a95e892185ec22291608cdc35298ab5df7b4",
    "test_migration.py": "6c3dcaeac5434d4396d7583a5dae150cc3b97ef734b49ad656229293f502ffc6",
}
CONDITIONS = (
    ("legacy", "input/saved_actions.json", "source_map_v1.json", "input/saved_gold.json", 3),
    ("wrapped", "input/saved_actions.json", "source_map_v2.json", "input/saved_gold.json", 3),
    ("repair", "actions/repair.json", "source_map_v2.json", "input/saved_gold.json", 3),
    ("raw_observations", "actions/raw_observations.json", "source_map_later.json", "input/later_gold.json", 6),
    ("raw_observations_and_conditional_review", "actions/raw_observations_and_conditional_review.json", "source_map_later.json", "input/later_gold.json", 6),
)
OBSERVATION_METADATA = {
    "projection_convention": "Objects retain source keys; arrays retain element order; scalars become type markers. Marker keys describe observations and are not claims about source keys.",
    "scalar_marker_key": "$type",
    "scalar_type_labels": ["integer", "number", "string", "boolean", "null"],
    "omitted_dictionary_keys": ["per_query", "provenance"],
    "omission_convention": "At every object depth, each omitted member is replaced by an omission marker and the whole member's actual JSON type; its contents are not traversed.",
    "omission_marker_key": "$omitted",
    "string_id_convention": "Only an immediate object member named id whose value is a string also has observed_value; array elements do not inherit this exception.",
    "value_marker_key": "observed_value",
    "projection_input": "Each parsed wrapped file read back after it was written.",
}


class ReplayError(Exception):
    """A bundle or replay does not satisfy the frozen mechanical contract."""


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReplayError("duplicate JSON object key")
        result[key] = value
    return result


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ReplayError("nonfinite JSON number")
    return value


def _reject_constant(text):
    raise ReplayError("nonfinite JSON constant: " + text)


def read_json(path: Path) -> Any:
    value = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object,
                       parse_float=_finite_float, parse_constant=_reject_constant)
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


def write_new_json(path: Path, value: Any) -> None:
    raw = (canonical_json(value) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


def exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(exact_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(exact_equal(a, b) for a, b in zip(left, right))
    if type(left) is float:
        return left.hex() == right.hex()
    return left == right


def _json_type(value):
    return {dict: "object", list: "array", str: "string", bool: "boolean", int: "integer",
            float: "number", type(None): "null"}[type(value)]


def structural_projection(value, member_key=None):
    if type(value) is dict:
        return {key: {"$omitted": True, "$type": _json_type(child)}
                if key in {"per_query", "provenance"} else structural_projection(child, key)
                for key, child in value.items()}
    if type(value) is list:
        return [structural_projection(child) for child in value]
    result = {"$type": _json_type(value)}
    if member_key == "id" and type(value) is str:
        result["observed_value"] = value
    return result


def _safe_name(name):
    if type(name) is not str or not name or "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return (bool(path.parts) and not path.is_absolute() and path.as_posix() == name and
            all(part not in {"", ".", ".."} for part in path.parts) and
            not re.match(r"^[A-Za-z]:", name))


def _valid_digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _required_files():
    files = set(FROZEN_CODE_SHA256) | {"replay.py", "protocol.json", "input/saved_actions.json",
            "input/saved_gold.json", "input/later_tasks.json", "input/later_gold.json",
            "actions/repair.json", "memory/conditional_review.json", "actions/raw_observations.json",
            "actions/raw_observations_and_conditional_review.json"}
    files |= {"input/originals/" + a + ".json" for a in ALIASES}
    files |= {"input/environment/migrated/" + a + ".json" for a in ALIASES}
    files |= {"input/environment/" + n for n in ("source_map_v1.json", "source_map_v2.json",
              "source_map_later.json", "catalog.json", "observations.json", "INVARIANTS.json")}
    files |= {"expected_runs/" + condition[0] + ".json" for condition in CONDITIONS}
    return files


def verify_manifest(bundle: Path) -> dict[str, Any]:
    """Validate every entry before loading any bundled Python module."""
    if bundle.is_symlink() or not bundle.is_dir():
        raise ReplayError("bundle must be a regular directory")
    manifest_path = bundle / "manifest.json"
    if not stat.S_ISREG(manifest_path.lstat().st_mode):
        raise ReplayError("manifest must be a regular file")
    manifest_raw = manifest_path.read_bytes()
    manifest = read_json(manifest_path)
    if type(manifest) is not dict or set(manifest) != {"schema_version", "files"} or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ReplayError("unsupported manifest schema")
    declared = manifest["files"]
    if type(declared) is not dict or not declared or "manifest.json" in declared:
        raise ReplayError("manifest must list every other file, excluding itself")
    for name, record in declared.items():
        if (not _safe_name(name) or type(record) is not dict or set(record) != {"sha256", "bytes"}
                or not _valid_digest(record["sha256"]) or type(record["bytes"]) is not int or record["bytes"] < 0):
            raise ReplayError("invalid manifest file entry: " + repr(name))
    actual = set()
    for path in bundle.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ReplayError("symlinks are not allowed in this bundle")
        if stat.S_ISREG(mode):
            name = path.relative_to(bundle).as_posix()
            if name != "manifest.json":
                actual.add(name)
        elif not stat.S_ISDIR(mode):
            raise ReplayError("nonregular bundle entry")
    if actual != set(declared):
        raise ReplayError("bundle files differ from manifest; missing=" + repr(sorted(set(declared) - actual)) + "; extra=" + repr(sorted(actual - set(declared))))
    for name, record in declared.items():
        raw = (bundle / name).read_bytes()
        if len(raw) != record["bytes"] or sha256(raw) != record["sha256"]:
            raise ReplayError("bundle SHA256/size mismatch: " + name)
    if not _required_files() <= actual:
        raise ReplayError("required replay files are missing: " + repr(sorted(_required_files() - actual)))
    for name, expected in FROZEN_CODE_SHA256.items():
        if declared[name]["sha256"] != expected:
            raise ReplayError("copied frozen code differs: " + name)
    return {"status": "verified", "manifest_sha256": sha256(manifest_raw),
            "verified_files_excluding_manifest": len(actual), "files_including_manifest": len(actual) + 1,
            "frozen_code_copies_verified": True}


def _check_environment(bundle):
    environment = bundle / "input/environment"
    v1 = {a: "../originals/" + a + ".json" for a in ALIASES}
    v2 = {a: "migrated/" + a + ".json" for a in ALIASES}
    later, catalog = {}, {}
    for index, alias in enumerate(ALIASES):
        for offset, source_map, format_name in ((1, v1, "legacy_root"), (2, v2, "wrapped_v2")):
            source_alias = "S%02d" % (index * 2 + offset)
            later[source_alias] = source_map[alias]
            catalog[source_alias] = {"origin_alias": alias, "format": format_name}
    for name, expected in (("source_map_v1.json", v1), ("source_map_v2.json", v2),
                           ("source_map_later.json", later), ("catalog.json", catalog)):
        if not exact_equal(read_json(environment / name), expected):
            raise ReplayError("unexpected fixed environment mapping: " + name)
    invariants = read_json(environment / "INVARIANTS.json")
    if (type(invariants) is not dict or set(invariants) != {"schema_version", "created_at_utc", "construction", "files", "observations_file_sha256"}
            or invariants["schema_version"] != "migration-invariants.v1" or invariants["construction"] != "environment_only"
            or type(invariants["files"]) is not dict or set(invariants["files"]) != set(ALIASES)):
        raise ReplayError("unexpected environment invariant schema")
    timestamp = invariants["created_at_utc"]
    if type(timestamp) is not str or not timestamp.endswith("Z") or datetime.fromisoformat(timestamp.replace("Z", "+00:00")).utcoffset().total_seconds() != 0:
        raise ReplayError("invariant timestamp must be UTC")
    projections = {}
    for alias in ALIASES:
        original_path = bundle / "input/originals" / (alias + ".json")
        wrapped_path = environment / "migrated" / (alias + ".json")
        original, wrapped = read_json(original_path), read_json(wrapped_path)
        if (type(wrapped) is not dict or set(wrapped) != {"schema_version", "payload"}
                or wrapped["schema_version"] != "artifact-container.v2" or not exact_equal(original, wrapped["payload"])):
            raise ReplayError("wrapped payload differs in value or type: " + alias)
        projection = structural_projection(wrapped)
        projections[alias] = projection
        expected = {"original_sha256_before": sha256(original_path.read_bytes()),
                    "original_sha256_after": sha256(original_path.read_bytes()),
                    "wrapped_sha256": sha256(wrapped_path.read_bytes()),
                    "canonical_payload_sha256": sha256(canonical_json(wrapped["payload"]).encode("utf-8")),
                    "observation_sha256": sha256(canonical_json(projection).encode("utf-8")),
                    "payload_matches_original_including_types": True, "original_bytes_unchanged": True}
        if not exact_equal(invariants["files"][alias], expected):
            raise ReplayError("environment invariant mismatch: " + alias)
    observations_path = environment / "observations.json"
    expected_observations = {"observation_metadata": OBSERVATION_METADATA, "observations": projections}
    if not exact_equal(read_json(observations_path), expected_observations):
        raise ReplayError("observations differ from regenerated wrapped-file projections")
    if invariants["observations_file_sha256"] != sha256(observations_path.read_bytes()):
        raise ReplayError("observations raw hash mismatch")
    return {"status": "verified", "payloads_preserved_including_types": len(ALIASES),
            "observations_regenerated": len(ALIASES), "fixed_relative_maps_verified": True}


def _check_expected_runs(bundle):
    expected_runs, expected_artifacts = {}, set()
    for condition, actions_file, _, _, count in CONDITIONS:
        actions = read_json(bundle / actions_file)
        expected = read_json(bundle / "expected_runs" / (condition + ".json"))
        if type(actions) is not list or len(actions) != count or type(expected) is not list or len(expected) != count:
            raise ReplayError("unexpected action/outcome count: " + condition)
        ids = []
        for action, item in zip(actions, expected):
            if (type(action) is not dict or type(action.get("id")) is not str or
                    not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", action["id"])):
                raise ReplayError("unsafe or invalid action id: " + condition)
            if (type(item) is not dict or set(item) != {"id", "execution_status", "validation_status", "artifact_sha256", "error"}
                    or item["id"] != action["id"] or type(item["execution_status"]) is not str
                    or item["validation_status"] not in {"accepted", "rejected"}
                    or (item["artifact_sha256"] is not None and not _valid_digest(item["artifact_sha256"]))):
                raise ReplayError("invalid or reordered expected item: " + condition)
            error = item["error"]
            if error is not None and (type(error) is not dict or set(error) != {"type", "message"} or any(type(error[k]) is not str for k in error)):
                raise ReplayError("invalid expected error: " + condition)
            ids.append(action["id"])
            path = "expected_artifacts/" + condition + "/" + item["id"] + ".json"
            if item["artifact_sha256"] is not None:
                expected_artifacts.add(path)
                if not (bundle / path).is_file() or sha256((bundle / path).read_bytes()) != item["artifact_sha256"]:
                    raise ReplayError("expected artifact missing or hash differs: " + path)
                read_json(bundle / path)
        if len(ids) != len(set(ids)):
            raise ReplayError("duplicate action id: " + condition)
        if condition == "repair" and set(ids) != {"P01", "P03", "P05"}:
            raise ReplayError("repair must preserve P01/P03/P05 ids")
        expected_runs[condition] = expected
    actual_artifacts = {p.relative_to(bundle).as_posix() for p in (bundle / "expected_artifacts").rglob("*") if p.is_file()}
    if actual_artifacts != expected_artifacts:
        raise ReplayError("expected_artifacts must exist exactly for recorded actual artifacts")
    return expected_runs


def verify_bundle(bundle):
    verification = verify_manifest(bundle)
    verification["environment"] = _check_environment(bundle)
    _check_expected_runs(bundle)
    return verification


def load_engine(bundle):
    # Compile verified source bytes directly so an on-disk bytecode cache cannot
    # replace the source that the manifest and frozen hash actually verified.
    path = bundle / "action_loop.py"
    raw = path.read_bytes()
    if sha256(raw) != FROZEN_CODE_SHA256["action_loop.py"]:
        raise ReplayError("action engine changed after verification")
    module = types.ModuleType("verified_bundle_action_loop")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def replay(bundle: Path, output: Path, report: dict[str, Any]) -> None:
    report["bundle_verification"] = verify_bundle(bundle)
    expected_runs = _check_expected_runs(bundle)
    engine = load_engine(bundle)
    comparisons, runs = [], []
    for condition, actions_file, map_file, gold_file, _ in CONDITIONS:
        summary = engine.run_batch(bundle / "input/environment" / map_file, bundle / actions_file,
                                   bundle / gold_file, output / condition)
        runs.append({"condition": condition, "status": summary["status"], "counts": summary["counts"]})
        expected = expected_runs[condition]
        if len(summary["items"]) != len(expected):
            raise ReplayError("replayed item count differs: " + condition)
        for item, saved in zip(summary["items"], expected):
            item_dir = output / condition / item["directory"]
            execution = read_json(item_dir / "execution.json")
            artifact_path = item_dir / "artifact.json"
            actual_hash = sha256(artifact_path.read_bytes()) if artifact_path.is_file() else None
            actual = {"id": item["id"], "execution_status": item["execution_status"],
                      "validation_status": item["validation_status"], "artifact_sha256": actual_hash,
                      "error": execution["error"]}
            matches = {key: exact_equal(actual[key], saved[key]) for key in saved}
            matches["execution_artifact_sha256"] = actual_hash == execution["artifact_sha256"] == item["artifact_sha256"]
            comparisons.append({"condition": condition, "id": item["id"], "actual": actual,
                                "expected": saved, "matches": matches, "all_match": all(matches.values()),
                                "budget_exceeded": item["budget_exceeded"]})
    report["runs"] = runs
    report["item_comparisons"] = comparisons
    report["items_compared"] = len(comparisons)
    report["items_matching"] = sum(item["all_match"] for item in comparisons)
    artifacts = [item for item in comparisons if item["expected"]["artifact_sha256"] is not None]
    errors = [item for item in comparisons if item["expected"]["error"] is not None]
    report["generated_artifacts"] = sum(item["actual"]["artifact_sha256"] is not None for item in comparisons)
    report["expected_artifacts"] = len(artifacts)
    report["generated_artifact_sha256_match_count"] = sum(item["matches"]["artifact_sha256"] for item in artifacts)
    report["expected_errors"] = len(errors)
    report["expected_errors_preserved"] = sum(item["all_match"] for item in errors)
    report["budget_violations"] = sum(item["budget_exceeded"] for item in comparisons)
    report["status"] = "passed" if len(comparisons) == 21 and all(item["all_match"] and not item["budget_exceeded"] for item in comparisons) else "failed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="absolute new output directory outside the bundle")
    parser.add_argument("--bundle", type=Path, help="bundle directory; defaults to this script's parent")
    args = parser.parse_args(argv)
    report = {"schema_version": 1, "status": "failed", "started_at_utc": utc_now(),
              "finished_at_utc": None, "python_version": sys.version.split()[0],
              "choices_source": "saved_bundle_actions", "fresh_ai_choices_generated": False,
              "replay_scope": "Re-execution of saved choices and comparison of recorded mechanical outcomes; no AI regeneration.",
              "bundle_verification": {"status": "not_verified"}, "error": None}
    created = False
    output = Path(args.out).expanduser()
    try:
        bundle_argument = args.bundle if args.bundle is not None else Path(__file__).parent
        if bundle_argument.is_symlink():
            raise ReplayError("bundle must not be a symlink")
        bundle = bundle_argument.resolve(strict=True)
        if not output.is_absolute():
            raise ReplayError("output must be an absolute path")
        # Check lstat before resolve so broken symlinks are existing outputs too.
        try:
            output.lstat()
        except FileNotFoundError:
            pass
        else:
            raise ReplayError("output already exists")
        output = output.resolve()
        if output == bundle or bundle in output.parents or output in bundle.parents:
            raise ReplayError("output must be outside the verified bundle")
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
