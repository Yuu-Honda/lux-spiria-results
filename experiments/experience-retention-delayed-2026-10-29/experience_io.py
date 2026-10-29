#!/usr/bin/env python3
"""Mechanical environment, requested inspection, policy, and elapsed-time I/O.

No task, answer, AI choice, simulated execution, or learning judgment is authored
here. Build creates no observations. Inspect reads only the selected source.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any

from action_loop import (ACTION_CHARACTER_LIMIT, ActionError, canonical_json,
                         parse_json, sha256_bytes, utc_now, validate_action)

ALIASES = ("X01", "X02", "X03")
PROBES = (("X02", "changed"), ("X01", "original"), ("X03", "changed"),
          ("X02", "original"), ("X01", "changed"), ("X03", "original"))
MINIMUM_DELAY_SECONDS = 86400
OBSERVATION_METADATA = {
    "annotation_keys": ["$type", "$omitted", "observed_value"],
    "annotation_scope": "Annotation keys describe this observation representation, not keys claimed to exist in the source.",
    "boundary_rule": "At the source root and every payload container, keep object keys but traverse only sample, conditions, and container-valued payload; omit every other member. Non-object boundary scalars are omitted and boundary arrays retain element order.",
    "retained_branch_rule": "Within sample/conditions, retain keys and array positions; mask scalars with exact JSON types, retaining observed_value only for an immediate string-valued id member. Array elements do not inherit the id exception.",
    "omission_rule": "Omit the contents of per_query and provenance at every depth and retain only their whole-value type.",
    "character_accounting": "returned_canonical_characters counts canonical_json(observation) only, excluding this metadata and the outer inspection record.",
}


class ExperienceIOError(Exception):
    """A malformed input, unsafe path, collision, or failed invariant."""


class DelayedNotDueError(ExperienceIOError):
    """The actual minimum elapsed-time boundary has not been reached."""


def _no_symlinks(path: Path) -> None:
    path = Path(path)
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        if part == ".":
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ExperienceIOError("symlinks are not allowed: " + str(current))


def _new_output(path: Path) -> None:
    _no_symlinks(path)
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise ExperienceIOError("output already exists: " + str(path))


def _read_json(path: Path) -> tuple[bytes, Any]:
    _no_symlinks(path)
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ExperienceIOError("input must be a regular file: " + str(path))
        raw = path.read_bytes()
        return raw, parse_json(raw)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise ExperienceIOError("cannot parse " + str(path) + ": " + str(exc)) from exc


def _write_new_json(path: Path, value: Any) -> str:
    _new_output(path)
    raw = (canonical_json(value) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    return sha256_bytes(raw)


def exact_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(exact_json_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(exact_json_equal(a, b) for a, b in zip(left, right))
    if type(left) is float:
        return left.hex() == right.hex()
    return left == right


def _json_type(value: Any) -> str:
    return {dict: "object", list: "array", str: "string", bool: "boolean", int: "integer",
            float: "number", type(None): "null"}[type(value)]


def _omitted(value: Any) -> dict[str, Any]:
    return {"$omitted": True, "$type": _json_type(value)}


def _retained_projection(value: Any, member_key: str | None = None) -> Any:
    if type(value) is dict:
        return {key: _omitted(child) if key in {"per_query", "provenance"}
                else _retained_projection(child, key) for key, child in value.items()}
    if type(value) is list:
        return [_retained_projection(child) for child in value]
    result = {"$type": _json_type(value)}
    if member_key == "id" and type(value) is str:
        result["observed_value"] = value
    return result


def structural_projection(value: Any) -> Any:
    """Boundary-selective projection; this function itself performs no read."""
    if type(value) is dict:
        result = {}
        for key, child in value.items():
            if key in {"per_query", "provenance"}:
                result[key] = _omitted(child)
            elif key in {"sample", "conditions"}:
                result[key] = _retained_projection(child)
            elif key == "payload" and type(child) in (dict, list):
                result[key] = structural_projection(child)
            else:
                result[key] = _omitted(child)
        return result
    if type(value) is list:
        return [structural_projection(child) for child in value]
    return _omitted(value)


def build_environment(originals: Path, out: Path) -> dict[str, Any]:
    originals, out = Path(originals), Path(out)
    _new_output(out)
    _no_symlinks(originals)
    _no_symlinks(out.parent / "originals")
    try:
        original_root = originals.resolve(strict=True)
        expected_root = (out.parent.resolve(strict=True) / "originals").resolve(strict=True)
    except OSError as exc:
        raise ExperienceIOError("unavailable original/output layout: " + str(exc)) from exc
    if not original_root.is_dir() or original_root != expected_root:
        raise ExperienceIOError("originals must resolve from the output's ../originals directory")
    before, parsed = {}, {}
    for alias in ALIASES:
        before[alias], parsed[alias] = _read_json(original_root / (alias + ".json"))
    try:
        out.mkdir(mode=0o700)
    except OSError as exc:
        raise ExperienceIOError("output must be new: " + str(exc)) from exc
    (out / "migrated").mkdir(mode=0o700)
    records, raw_hashes = {}, {"original": {}, "changed": {}}
    for alias in ALIASES:
        path = out / "migrated" / (alias + ".json")
        _write_new_json(path, {"schema_version": "artifact-container.v2", "payload": parsed[alias]})
        raw, readback = _read_json(path)
        if (type(readback) is not dict or set(readback) != {"schema_version", "payload"}
                or readback["schema_version"] != "artifact-container.v2"
                or not exact_json_equal(readback["payload"], parsed[alias])):
            raise ExperienceIOError("written payload changed value or type: " + alias)
        original_hash, changed_hash = sha256_bytes(before[alias]), sha256_bytes(raw)
        raw_hashes["original"][alias], raw_hashes["changed"][alias] = original_hash, changed_hash
        records[alias] = {"original_sha256_before": original_hash, "changed_sha256": changed_hash,
                          "canonical_payload_sha256": sha256_bytes(canonical_json(readback["payload"]).encode("utf-8")),
                          "payload_matches_original_including_types": True}
    maps = {
        "original": {a: "../originals/" + a + ".json" for a in ALIASES},
        "changed": {a: "migrated/" + a + ".json" for a in ALIASES},
    }
    maps["probes"] = {"A%02d" % index: maps[condition][alias]
                      for index, (alias, condition) in enumerate(PROBES, 1)}
    catalogs = {stage: {a: {"family": a, "raw_sha256": raw_hashes[stage][a]} for a in ALIASES}
                for stage in ("original", "changed")}
    catalogs["probes"] = {"A%02d" % index: {"family": alias, "raw_sha256": raw_hashes[condition][alias]}
                          for index, (alias, condition) in enumerate(PROBES, 1)}
    for stage in ("original", "changed", "probes"):
        _write_new_json(out / ("source_map_" + stage + ".json"), maps[stage])
        _write_new_json(out / ("catalog_" + stage + ".json"), catalogs[stage])
    for alias in ALIASES:
        after, _ = _read_json(original_root / (alias + ".json"))
        if after != before[alias]:
            raise ExperienceIOError("original bytes changed during construction: " + alias)
        records[alias].update(original_sha256_after=sha256_bytes(after), original_bytes_unchanged=True)
    invariants = {"schema_version": "experience-environment-invariants.v1", "created_at_utc": utc_now(),
                  "construction": "environment_only_without_presupplied_observations", "files": records}
    _write_new_json(out / "INVARIANTS.json", invariants)
    return invariants


def inspect_source(sources: Path, source: str, out: Path) -> dict[str, Any]:
    """Read the map and exactly one selected source, with no unselected access.

    Relative source paths are confined to the map's parent or its parent input
    directory, which supports ../originals and migrated bindings. The projection
    and its cost counters are generated from that one actual raw source read.
    """
    sources, out = Path(sources), Path(out)
    _new_output(out)
    _, mapping = _read_json(sources)
    if (type(mapping) is not dict or not mapping or
            any(type(k) is not str or not k or type(v) is not str or not v for k, v in mapping.items())):
        raise ExperienceIOError("sources map must contain nonempty string aliases and paths")
    if type(source) is not str or source not in mapping:
        raise ExperienceIOError("unknown selected source alias")
    relative = Path(mapping[source])
    if relative.is_absolute() or "\\" in mapping[source] or "\x00" in mapping[source]:
        raise ExperienceIOError("selected source path must be relative")
    path = sources.parent / relative
    _no_symlinks(path)
    path = path.resolve(strict=True)
    permitted = sources.parent.resolve(strict=True).parent
    if path != permitted and permitted not in path.parents:
        raise ExperienceIOError("selected source path escapes the input directory")
    raw, value = _read_json(path)
    observation = structural_projection(value)
    record = {"source": source, "raw_sha256": sha256_bytes(raw), "raw_bytes_read": len(raw),
              "returned_canonical_characters": len(canonical_json(observation)),
              "observation_metadata": OBSERVATION_METADATA, "observation": observation}
    _write_new_json(out, record)
    return record


def validate_policy(policy: Any, allowedtaskid: str) -> dict[str, Any]:
    """Validate a frozen choice without executing or modifying its action.

    A valid oversized action is flagged and retained, matching the old runner's
    budget behavior. The decision, rationale, action, and prediction are never
    authored or semantically corrected here.
    """
    if type(allowedtaskid) is not str or not allowedtaskid:
        raise ExperienceIOError("allowed task id must be a nonempty string")
    if type(policy) is not dict or type(policy.get("id")) is not str or policy["id"] != allowedtaskid:
        raise ExperienceIOError("policy id must match the allowed task id")
    decision = policy.get("decision")
    characters = None
    if decision == "inspect":
        if set(policy) != {"id", "decision", "rationale"} or type(policy["rationale"]) is not str:
            raise ExperienceIOError("inspect policy must contain exactly id, decision, rationale")
    elif decision == "submit":
        if set(policy) != {"id", "decision", "action"}:
            raise ExperienceIOError("submit policy must contain exactly id, decision, action")
        try:
            validate_action(policy["action"])
            if policy["action"]["id"] != allowedtaskid:
                raise ExperienceIOError("submitted action id must match the allowed task id")
            characters = len(canonical_json(policy["action"]))
        except (ActionError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise ExperienceIOError("invalid submitted action: " + str(exc)) from exc
    else:
        raise ExperienceIOError("policy decision must be inspect or submit")
    return {"id": allowedtaskid, "decision": decision, "canonical_action_characters": characters,
            "budget_limit": ACTION_CHARACTER_LIMIT,
            "budget_exceeded": characters is not None and characters > ACTION_CHARACTER_LIMIT}


def _finite_clock(value: Any, label: str) -> int | float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ExperienceIOError(label + " must be finite nonnegative Unix seconds, never boolean")
    return value


def check_delayed_due(memory_freeze_file: Path, now_unix: int | float | None = None) -> dict[str, Any]:
    """Guard actual collection time only; never schedule or execute anything.

    Freeze metadata must include frozen_at_unix. now_unix is injectable for
    synthetic tests; normal callers omit it and use the actual wall clock.
    """
    _, freeze = _read_json(Path(memory_freeze_file))
    if type(freeze) is not dict or "frozen_at_unix" not in freeze:
        raise ExperienceIOError("memory freeze must contain frozen_at_unix")
    frozen = _finite_clock(freeze["frozen_at_unix"], "frozen_at_unix")
    now = _finite_clock(time.time() if now_unix is None else now_unix, "now_unix")
    due = frozen + MINIMUM_DELAY_SECONDS
    if not math.isfinite(due):
        raise ExperienceIOError("computed due time must be finite")
    elapsed = now - frozen
    if now < due or elapsed < MINIMUM_DELAY_SECONDS:
        raise DelayedNotDueError("delayed collection not due: elapsed=" + str(elapsed) + "; due_unix=" + str(due))
    return {"checked_at_unix": now, "frozen_at_unix": frozen, "elapsed_seconds": elapsed,
            "due_unix": due, "due": True}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--originals", required=True, type=Path)
    build.add_argument("--out", required=True, type=Path)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--sources", required=True, type=Path)
    inspect.add_argument("--source", required=True)
    inspect.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build_environment(args.originals, args.out)
            result = {"status": "built", "out": str(args.out)}
        else:
            result = inspect_source(args.sources, args.source, args.out)
    except (ExperienceIOError, OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(canonical_json({"status": "failed", "error": {"type": type(exc).__name__, "message": str(exc)}}), file=sys.stderr)
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
