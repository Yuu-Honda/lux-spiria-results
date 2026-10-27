#!/usr/bin/env python3
"""Verify this bundle, replay saved actions once, and compare real artifact bytes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True

CONDITIONS = (
    ("practice", "gold_practice.json", 6),
    ("prior_plan_only", "gold_later.json", 9),
    ("raw_feedback", "gold_later.json", 9),
    ("raw_feedback_and_review", "gold_later.json", 9),
)


class ReplayError(Exception):
    pass


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReplayError("duplicate JSON object key")
        value[key] = item
    return value


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def write_new_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


def verify_bundle(bundle):
    """Check every file before importing or invoking the bundled action engine."""
    manifest_path = bundle / "manifest.json"
    if manifest_path.is_symlink():
        raise ReplayError("manifest must be a regular file")
    manifest_raw = manifest_path.read_bytes()
    manifest = read_json(manifest_path)
    if type(manifest) is not dict or set(manifest) != {"schema_version", "files"} or manifest["schema_version"] != 1:
        raise ReplayError("unsupported manifest schema")
    files = manifest["files"]
    if type(files) is not dict or not files or "manifest.json" in files:
        raise ReplayError("manifest must list every other bundle file, excluding itself")
    declared = set()
    for name, record in files.items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or path.as_posix() != name or
                ".." in path.parts or "\\" in name or type(record) is not dict or
                set(record) != {"sha256", "bytes"} or type(record["sha256"]) is not str or
                not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) or
                type(record["bytes"]) is not int or record["bytes"] < 0):
            raise ReplayError("invalid manifest file entry")
        declared.add(name)
    actual = set()
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise ReplayError("symlinks are not allowed in this bundle")
        if path.is_file():
            name = path.relative_to(bundle).as_posix()
            if name != "manifest.json":
                actual.add(name)
        elif not path.is_dir():
            raise ReplayError("nonregular bundle entry")
    if actual != declared:
        raise ReplayError("bundle files differ from manifest; missing=" + repr(sorted(declared - actual)) +
                          "; extra=" + repr(sorted(actual - declared)))
    mismatches = []
    for name in sorted(declared):
        raw = (bundle / name).read_bytes()
        if len(raw) != files[name]["bytes"] or sha256(raw) != files[name]["sha256"]:
            mismatches.append(name)
    if mismatches:
        raise ReplayError("bundle SHA256/size mismatch: " + repr(mismatches))
    required = {"action_loop.py", "test_action_loop.py", "source_map.json", "gold_practice.json", "gold_later.json"}
    if not required <= declared:
        raise ReplayError("required replay files are missing")
    source_map = read_json(bundle / "source_map.json")
    if source_map != {name: "sources/" + name + ".json" for name in ("D01", "D02", "D03")}:
        raise ReplayError("source map must reference only the three bundled relative source paths")
    return {"status": "verified", "manifest_sha256": sha256(manifest_raw),
            "verified_files_excluding_manifest": len(declared), "files_including_manifest": len(declared) + 1}


def replay(bundle, output, report):
    report["bundle_verification"] = verify_bundle(bundle)
    spec = importlib.util.spec_from_file_location("bundled_action_loop", bundle / "action_loop.py")
    if spec is None or spec.loader is None:
        raise ReplayError("cannot load verified bundled action engine")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    comparisons = []
    runs = []
    for condition, gold_file, count in CONDITIONS:
        actions_path = bundle / "actions" / (condition + ".json")
        actions = read_json(actions_path)
        if type(actions) is not list or len(actions) != count:
            raise ReplayError("unexpected action count for " + condition)
        for action in actions:
            if type(action) is not dict or type(action.get("id")) is not str or not re.fullmatch(r"[PTR][0-9]{2}", action["id"]):
                raise ReplayError("unsafe or unexpected action id")
        summary = engine.run_batch(bundle / "source_map.json", actions_path,
                                   bundle / gold_file, output / condition)
        runs.append({"condition": condition, "status": summary["status"], "counts": summary["counts"]})
        for item in summary["items"]:
            actual_path = output / condition / item["directory"] / "artifact.json"
            recorded_path = bundle / "recorded" / condition / (item["id"] + ".json")
            actual_hash = sha256(actual_path.read_bytes()) if actual_path.is_file() else None
            recorded_hash = sha256(recorded_path.read_bytes())
            comparisons.append({"condition": condition, "task_id": item["id"],
                                "actual_sha256": actual_hash, "recorded_sha256": recorded_hash,
                                "identical_bytes": actual_hash == recorded_hash,
                                "validator_status": item["validation_status"],
                                "budget_exceeded": item["budget_exceeded"]})
    report["runs"] = runs
    report["artifact_comparisons"] = comparisons
    report["artifacts_compared"] = len(comparisons)
    report["artifacts_identical"] = sum(item["identical_bytes"] for item in comparisons)
    report["validator_accepted"] = sum(item["validator_status"] == "accepted" for item in comparisons)
    report["budget_violations"] = sum(item["budget_exceeded"] for item in comparisons)
    report["status"] = "passed" if (len(comparisons) == 33 and
        all(item["identical_bytes"] and item["validator_status"] == "accepted" and
            not item["budget_exceeded"] for item in comparisons)) else "failed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="new output directory outside this bundle")
    args = parser.parse_args(argv)
    bundle = Path(__file__).resolve().parent
    output = Path(args.out).expanduser().resolve()
    report = {"schema_version": 1, "status": "failed", "started_at_utc": utc_now(),
              "finished_at_utc": None, "python_version": sys.version.split()[0],
              "replay_scope": "saved actions and actual artifacts; no AI regeneration or external engine",
              "error": None}
    created = False
    try:
        if output == bundle or bundle in output.parents:
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
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
