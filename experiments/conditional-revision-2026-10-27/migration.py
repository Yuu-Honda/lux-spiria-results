#!/usr/bin/env python3
"""Construct a new, value-preserving JSON environment; never execute actions.

Only D01.json, D02.json, and D03.json are inputs. No task, query, expected result,
action, or source-specific interpretation is accepted by this utility.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Any

from action_loop import canonical_json, parse_json, sha256_bytes, utc_now


ALIASES = ("D01", "D02", "D03")
OMITTED_KEYS = frozenset(("per_query", "provenance"))
WRAPPER_SCHEMA = "artifact-container.v2"


class MigrationError(Exception):
    """An invalid source, conflicting destination, or failed invariant."""


def _json_type(value: Any) -> str:
    return {
        dict: "object", list: "array", str: "string", bool: "boolean",
        int: "integer", float: "number", type(None): "null",
    }[type(value)]


def exact_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without bool/int coercion or float tolerance."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(
            exact_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            exact_json_equal(a, b) for a, b in zip(left, right)
        )
    if type(left) is float:
        return left.hex() == right.hex()
    return left == right


def structural_projection(value: Any, member_key: str | None = None) -> Any:
    """Project structure with fixed key omissions and one string-id exception.

    Marker keys describe observations, not keys claimed to exist in the source.
    Array elements do not inherit the containing object's member key.
    """
    if type(value) is dict:
        return {
            key: {"$omitted": True, "$type": _json_type(child)}
            if key in OMITTED_KEYS else structural_projection(child, key)
            for key, child in value.items()
        }
    if type(value) is list:
        return [structural_projection(child) for child in value]
    result = {"$type": _json_type(value)}
    if member_key == "id" and type(value) is str:
        result["observed_value"] = value
    return result


def _write_new_json(path: Path, value: Any) -> str:
    raw = (canonical_json(value) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
    return sha256_bytes(raw)


def _read_json(path: Path) -> tuple[bytes, Any]:
    try:
        raw = path.read_bytes()
        return raw, parse_json(raw)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise MigrationError("cannot parse " + str(path) + ": " + str(exc)) from exc


def _check_new_output(path: Path) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise MigrationError("output already exists: " + str(path))


def build_environment(originals: Path, out: Path) -> dict[str, Any]:
    """Write a new environment after preflight validation of all three inputs.

    The fixed relative source maps require the originals directory to resolve
    from ../originals beside the destination. The destination's parent exists.
    """
    originals, out = Path(originals), Path(out)
    _check_new_output(out)
    try:
        original_root = originals.resolve(strict=True)
        expected_root = (out.parent.resolve(strict=True) / "originals").resolve(strict=True)
    except OSError as exc:
        raise MigrationError("unavailable input/output layout: " + str(exc)) from exc
    if not original_root.is_dir() or original_root != expected_root:
        raise MigrationError("originals must resolve from the output's ../originals directory")

    before: dict[str, bytes] = {}
    parsed: dict[str, Any] = {}
    for alias in ALIASES:
        before[alias], parsed[alias] = _read_json(original_root / (alias + ".json"))

    # mkdir is the exclusive reservation, including a competing builder that
    # arrives after the initial lstat check. Existing outputs are never reused.
    try:
        out.mkdir(mode=0o700)
    except OSError as exc:
        raise MigrationError("cannot create new output: " + str(exc)) from exc
    (out / "migrated").mkdir(mode=0o700)

    records: dict[str, Any] = {}
    projections: dict[str, Any] = {}
    for alias in ALIASES:
        relative = "migrated/" + alias + ".json"
        wrapped_path = out / relative
        _write_new_json(wrapped_path, {"schema_version": WRAPPER_SCHEMA, "payload": parsed[alias]})
        wrapped_raw, readback = _read_json(wrapped_path)
        if type(readback) is not dict or set(readback) != {"schema_version", "payload"}:
            raise MigrationError("written wrapper has unexpected keys: " + alias)
        if readback["schema_version"] != WRAPPER_SCHEMA:
            raise MigrationError("written wrapper has unexpected schema: " + alias)
        if not exact_json_equal(readback["payload"], parsed[alias]):
            raise MigrationError("written payload changed a value or type: " + alias)
        # The projection is deliberately made from the parsed saved file.
        projection = structural_projection(readback)
        projections[alias] = projection
        records[alias] = {
            "original_sha256_before": sha256_bytes(before[alias]),
            "wrapped_sha256": sha256_bytes(wrapped_raw),
            "canonical_payload_sha256": sha256_bytes(canonical_json(readback["payload"]).encode("utf-8")),
            "observation_sha256": sha256_bytes(canonical_json(projection).encode("utf-8")),
            "payload_matches_original_including_types": True,
        }

    source_map_v1 = {alias: "../originals/" + alias + ".json" for alias in ALIASES}
    source_map_v2 = {alias: "migrated/" + alias + ".json" for alias in ALIASES}
    later: dict[str, str] = {}
    catalog: dict[str, dict[str, str]] = {}
    for index, alias in enumerate(ALIASES):
        legacy, wrapped = "S%02d" % (index * 2 + 1), "S%02d" % (index * 2 + 2)
        later[legacy], later[wrapped] = source_map_v1[alias], source_map_v2[alias]
        catalog[legacy] = {"origin_alias": alias, "format": "legacy_root"}
        catalog[wrapped] = {"origin_alias": alias, "format": "wrapped_v2"}
    for name, value in (
        ("source_map_v1.json", source_map_v1), ("source_map_v2.json", source_map_v2),
        ("source_map_later.json", later), ("catalog.json", catalog),
    ):
        _write_new_json(out / name, value)

    observations = {
        "observation_metadata": {
            "projection_convention": "Objects retain source keys; arrays retain element order; scalars become type markers. Marker keys describe observations and are not claims about source keys.",
            "scalar_marker_key": "$type",
            "scalar_type_labels": ["integer", "number", "string", "boolean", "null"],
            "omitted_dictionary_keys": sorted(OMITTED_KEYS),
            "omission_convention": "At every object depth, each omitted member is replaced by an omission marker and the whole member's actual JSON type; its contents are not traversed.",
            "omission_marker_key": "$omitted",
            "string_id_convention": "Only an immediate object member named id whose value is a string also has observed_value; array elements do not inherit this exception.",
            "value_marker_key": "observed_value",
            "projection_input": "Each parsed wrapped file read back after it was written.",
        },
        "observations": projections,
    }
    observation_file_sha256 = _write_new_json(out / "observations.json", observations)

    for alias in ALIASES:
        after = (original_root / (alias + ".json")).read_bytes()
        if after != before[alias]:
            raise MigrationError("original bytes changed during construction: " + alias)
        records[alias]["original_sha256_after"] = sha256_bytes(after)
        records[alias]["original_bytes_unchanged"] = True
    invariants = {
        "schema_version": "migration-invariants.v1",
        "created_at_utc": utc_now(),
        "construction": "environment_only",
        "files": records,
        "observations_file_sha256": observation_file_sha256,
    }
    _write_new_json(out / "INVARIANTS.json", invariants)
    return invariants


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="construct a new environment without running actions")
    build.add_argument("--originals", required=True, type=Path)
    build.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        build_environment(args.originals, args.out)
    except (MigrationError, OSError, ValueError, UnicodeError, RecursionError) as exc:
        print("migration error: " + str(exc), file=sys.stderr)
        return 1
    print(canonical_json({"status": "built", "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
