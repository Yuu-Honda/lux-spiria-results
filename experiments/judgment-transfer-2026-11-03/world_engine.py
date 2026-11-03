"""Deterministic real artifact engines and independent artifact validation.

No model choices, source ranking, judgment authoring, or native memory access.
The public validator follows the requested identity/merge contract and never
uses the recipe mapping to decide acceptance.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from common import canonical, keys, loads, need, sha, string, tree_hashes, utc, write_new

A_EFFECTS = frozenset({"literal", "trim", "decimal"})
B_EFFECTS = frozenset({"resume_after_checkpoint", "replay_skip_existing_key", "replay_upsert_by_key"})


def check_case(case, mechanism):
    keys(case, {"case_id", "version", "contract", "input"})
    string(case["case_id"], "case id", 100)
    string(case["version"], "version", 100)
    keys(case["contract"], {"kind", "text"})
    string(case["contract"]["text"], "contract natural text", 20000)
    kinds = {"literal", "trim", "decimal"} if mechanism == "A" else {"preserve", "refresh"}
    need(case["contract"]["kind"] in kinds, "invalid contract kind")
    keys(case["input"], {"records"} if mechanism == "A" else {"records", "initial_store", "checkpoint"})
    rows = case["input"]["records"]
    need(type(rows) is list and bool(rows), "nonempty input records required")
    _records(rows, mechanism)
    if mechanism == "B":
        initial = case["input"]["initial_store"]
        need(type(initial) is list, "initial store must be a list")
        _records(initial, "B")
        checkpoint = case["input"]["checkpoint"]
        need(type(checkpoint) is int and 0 <= checkpoint <= len(rows), "invalid input-prefix checkpoint")
    return case


def _records(rows, mechanism):
    seen = set()
    for row in rows:
        keys(row, {"id", "key", "value"} if mechanism == "A" else {"id", "value"})
        string(row["id"], "record id", 1000)
        string(row["value"], "record value", empty=True)
        if mechanism == "A":
            string(row["key"], "record key", empty=True)
        need(row["id"] not in seen, "duplicate input/initial id")
        seen.add(row["id"])


def check_world(world):
    keys(world, {"world_id", "mechanism", "operations", "versions", "training_cases", "probes"})
    string(world["world_id"], "world id", 100)
    need(world["mechanism"] in {"A", "B"}, "unknown mechanism")
    ops = world["operations"]
    need(type(ops) is list and len(ops) == 3 and len(set(ops)) == 3, "three distinct opaque operations required")
    for op in ops:
        need(type(op) is str and re.fullmatch(r"op-[a-f0-9]{8,32}", op), "opaque operation identifier required")
    keys(world["versions"], {"v1", "v2"})
    effects = A_EFFECTS if world["mechanism"] == "A" else B_EFFECTS
    for version in ("v1", "v2"):
        mapping = world["versions"][version]
        keys(mapping, set(ops))
        need(set(mapping.values()) == effects, "mapping must be an effect permutation")
    before = [world["versions"]["v1"][op] for op in ops]
    after = [world["versions"]["v2"][op] for op in ops]
    need(after in [before[1:] + before[:1], before[-1:] + before[:-1]], "v2 must be nonidentity cyclic rotation")
    cases = world["training_cases"]
    need(type(cases) is list and len(cases) == 3, "three training cases required")
    keys(world["probes"], {"same_version", "changed_version"})
    all_cases = cases + list(world["probes"].values())
    need(len({case["case_id"] for case in all_cases}) == 5, "unique case ids required")
    for case in all_cases:
        check_case(case, world["mechanism"])
    need(all(case["version"] == "v1" for case in cases), "training must use v1")
    need(world["probes"]["same_version"]["version"] == "v1" and world["probes"]["changed_version"]["version"] == "v2", "probe version differs")
    same, changed = world["probes"]["same_version"], world["probes"]["changed_version"]
    need(same["input"] == changed["input"] and same["contract"] == changed["contract"], "probe phases must have identical novel input and contract")
    if world["mechanism"] == "A":
        need({case["contract"]["kind"] for case in cases} == {"literal", "trim", "decimal"}, "A training must cover three contracts")
    else:
        need([case["contract"]["kind"] for case in cases].count("preserve") == 2 and [case["contract"]["kind"] for case in cases].count("refresh") == 1, "B training must include two preserve and one refresh cases")
    return world


def check_worlds(value):
    keys(value, {"schema", "worlds"})
    need(value["schema"] == "judgment-transfer-worlds.v1", "unknown worlds schema")
    worlds = value["worlds"]
    need(type(worlds) is list and len(worlds) == 6, "six independent worlds required")
    for world in worlds:
        check_world(world)
    need(len({w["world_id"] for w in worlds}) == 6, "distinct world ids required")
    need([w["mechanism"] for w in worlds].count("A") == 3 and [w["mechanism"] for w in worlds].count("B") == 3, "three histories per mechanism required")
    return worlds


def _operation_key(key, effect):
    if effect == "literal":
        return key
    if effect == "trim":
        return key.strip()
    need(effect == "decimal", "unknown key grouping effect")
    # Accepted grammar is explicit; e.g. 01 and +1 collide but keep both ids.
    return str(int(key, 10)) if re.fullmatch(r"[+-]?[0-9]+", key) else key


def _equivalent(left, right, contract):
    # Independent relation-based oracle; it does not call operation transforms.
    if contract == "literal":
        return left == right
    if contract == "trim":
        return left.strip() == right.strip()
    need(contract == "decimal", "unknown grouping contract")
    decimal_left = re.fullmatch(r"[+-]?[0-9]+", left) is not None
    decimal_right = re.fullmatch(r"[+-]?[0-9]+", right) is not None
    if decimal_left and decimal_right:
        return int(left, 10) == int(right, 10)
    if decimal_left != decimal_right:
        return False
    return left == right


def expected_partition(case):
    rows = case["input"]["records"]
    pending = list(rows)
    expected = []
    while pending:
        representative = pending.pop(0)
        members = {representative["id"]}
        rest = []
        for row in pending:
            if _equivalent(representative["key"], row["key"], case["contract"]["kind"]):
                members.add(row["id"])
            else:
                rest.append(row)
        expected.append(frozenset(members))
        pending = rest
    return frozenset(expected)


def expected_store(case):
    source = {row["id"]: row["value"] for row in case["input"]["records"]}
    existing = {row["id"]: row["value"] for row in case["input"]["initial_store"]}
    return source | existing if case["contract"]["kind"] == "preserve" else existing | source


def validate_artifact(case, mechanism, dest, *, operation_status):
    """Parse real output bytes and compare contract, coverage, and integrity."""
    dest = Path(dest)
    reasons = []
    artifact = None
    try:
        artifact = loads((dest / "artifact.json").read_bytes())
        if mechanism == "A":
            keys(artifact, {"schema", "records", "groups"})
            need(artifact["schema"] == "grouped-records.v1", "wrong group artifact schema")
            need(artifact["records"] == case["input"]["records"], "source payload integrity differs")
            need(type(artifact["groups"]) is list, "groups must be list")
            members, partitions = [], []
            for group in artifact["groups"]:
                keys(group, {"key", "members"})
                string(group["key"], "group key", empty=True)
                need(type(group["members"]) is list and bool(group["members"]), "nonempty member list required")
                need(all(type(mid) is str for mid in group["members"]), "invalid group member id")
                members.extend(group["members"])
                partitions.append(frozenset(group["members"]))
            need(len(members) == len(set(members)) and set(members) == {row["id"] for row in case["input"]["records"]}, "group member coverage differs")
            need(len(partitions) == len(set(partitions)) and frozenset(partitions) == expected_partition(case), "requested identity relation differs")
        else:
            keys(artifact, {"schema", "records"})
            need(artifact["schema"] == "sqlite-records.v1", "wrong SQLite artifact schema")
            need(type(artifact["records"]) is list, "store records must be list")
            _records(artifact["records"], "B")
            actual = {row["id"]: row["value"] for row in artifact["records"]}
            need(actual == expected_store(case), "store differs from requested union/payload precedence")
            with sqlite3.connect(f"file:{dest / 'store.sqlite'}?mode=ro", uri=True) as connection:
                db = dict(connection.execute("SELECT id,value FROM records"))
                need(db == actual, "export differs from actual SQLite state")
                need(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed")
    except Exception as exc:
        reasons.append(type(exc).__name__ + ": " + str(exc))
    state_valid = not reasons
    if operation_status != "success":
        reasons.append("operation did not complete successfully")
    return {"accepted": not reasons, "state_valid": state_valid, "process_completed": operation_status == "success", "reasons": reasons, "validation_basis": "independent_requested_contract_and_actual_artifact", "artifact_sha256": sha(dest / "artifact.json") if (dest / "artifact.json").exists() else None}


def execute(config, case, operation, dest):
    """Execute one fixed operation exactly once into a new isolated destination."""
    check_world(config)
    check_case(case, config["mechanism"])
    need(case["version"] in config["versions"] and operation in config["operations"], "unknown operation/version")
    dest = Path(dest)
    need(not dest.exists(), "execution destination already exists; never retry")
    dest.mkdir(parents=True)
    started = utc()
    effect = config["versions"][case["version"]][operation]
    write_new(dest / "input.json", {"case": case, "operation": operation}, dest)
    audit, error, status = [], None, "success"
    if config["mechanism"] == "A":
        grouped = {}
        for row in case["input"]["records"]:
            key = _operation_key(row["key"], effect)
            grouped.setdefault(key, []).append(row["id"])
            audit.append({"id": row["id"], "output_group_key": key})
        artifact = {"schema": "grouped-records.v1", "records": case["input"]["records"], "groups": [{"key": key, "members": members} for key, members in grouped.items()]}
        write_new(dest / "artifact.json", artifact, dest)
    else:
        connection = sqlite3.connect(dest / "store.sqlite")
        connection.set_trace_callback(audit.append)
        connection.execute("CREATE TABLE records (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany("INSERT INTO records (id,value) VALUES (?,?)", [(row["id"], row["value"]) for row in case["input"]["initial_store"]])
        connection.commit()
        write_new(dest / "initial-state.json", {"records": [{"id": rid, "value": value} for rid, value in connection.execute("SELECT id,value FROM records ORDER BY id")]}, dest)
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = case["input"]["records"]
            if effect == "resume_after_checkpoint":
                sql = "INSERT INTO records (id,value) VALUES (?,?)"
                rows = rows[case["input"]["checkpoint"]:]
            elif effect == "replay_skip_existing_key":
                sql = "INSERT INTO records (id,value) VALUES (?,?) ON CONFLICT(id) DO NOTHING"
            else:
                need(effect == "replay_upsert_by_key", "unknown import effect")
                sql = "INSERT INTO records (id,value) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value"
            for row in rows:
                connection.execute(sql, (row["id"], row["value"]))
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            status = "sql_error_rolled_back"
            error = {"type": type(exc).__name__, "message": str(exc), "sqlite_errorcode": getattr(exc, "sqlite_errorcode", None), "sqlite_errorname": getattr(exc, "sqlite_errorname", None)}
        artifact = {"schema": "sqlite-records.v1", "records": [{"id": rid, "value": value} for rid, value in connection.execute("SELECT id,value FROM records ORDER BY id")]}
        connection.close()
        write_new(dest / "artifact.json", artifact, dest)
    write_new(dest / "audit.json", {"schema": "actual-operation-audit.v1", "trace": audit, "error": error}, dest)
    validation = validate_artifact(case, config["mechanism"], dest, operation_status=status)
    result = {"schema": "actual-engine-result.v1", "operation": operation, "version": case["version"], "status": status, "error": error, "started_at_utc": started, "ended_at_utc": utc(), "artifact": artifact, "validation": validation}
    write_new(dest / "result.json", result, dest)
    return result


def calibration_case(mechanism, version):
    """Fixed diagnostic data; never the target case and never a gold mapping."""
    if mechanism == "A":
        return {"case_id": "diagnostic-toy", "version": version, "contract": {"kind": "literal", "text": "Diagnostic only: inspect the resulting groups on these toy records."}, "input": {"records": [{"id": "toy-1", "key": "1", "value": "one"}, {"id": "toy-2", "key": " 1 ", "value": "space"}, {"id": "toy-3", "key": "01", "value": "zero"}, {"id": "toy-4", "key": "+1", "value": "plus"}]}}
    return {"case_id": "diagnostic-toy", "version": version, "contract": {"kind": "preserve", "text": "Diagnostic only: inspect resulting SQLite stores after importing into this partial state."}, "input": {"records": [{"id": "toy-1", "value": "source-one"}, {"id": "toy-2", "value": "source-two"}, {"id": "toy-3", "value": "source-three"}], "initial_store": [{"id": "toy-1", "value": "existing-one"}], "checkpoint": 2}}
