"""Byte-level checks shared by the judgment-transfer engineering adapter.

These gates are reproducibility checks on a shared filesystem, not OS isolation
or proof of an actor's identity. Meaning and choices must come from actual AIs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re


def need(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def loads(raw):
    def pairs(rows):
        out = {}
        for key, value in rows:
            need(key not in out, "duplicate JSON key: " + key)
            out[key] = value
        return out
    def nonfinite(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def keys(value, required, optional=()):
    need(type(value) is dict and set(required) <= value.keys() and value.keys() <= set(required) | set(optional), "invalid object keys")


def string(value, label="string", maximum=1000000, *, empty=False):
    need(type(value) is str and (empty or bool(value)) and len(value) <= maximum, "invalid " + label)
    return value


def identifier(value):
    need(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value), "invalid identifier")
    return value


def sha_string(value):
    need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "invalid SHA256")
    return value


def safe(path, root):
    path = Path(os.path.abspath(path))
    root = Path(os.path.abspath(root))
    need(path == root or root in path.parents, "path outside experiment root")
    need(path.resolve() == path and not any(p.is_symlink() for p in (path, *path.parents)), "symlink or aliased path rejected")
    return path


def relative(path, root):
    return str(safe(path, root).relative_to(root))


def write_new(path, value, root, *, raw=False):
    path = safe(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = value if raw else (canonical(value) + "\n").encode("utf-8")
    need(type(body) is bytes, "raw content must be bytes")
    with path.open("xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o444)
    return path


def tree_hashes(folder):
    folder = Path(folder)
    out = {}
    if folder.exists():
        for path in sorted(folder.rglob("*")):
            safe(path, folder)
            if path.is_file():
                out[str(path.relative_to(folder))] = sha(path)
    return out


PROTOCOL_KEYS = {"schema", "mode", "worlds_path", "worlds_sha256", "preregistration_path", "preregistration_sha256", "code_sha256", "world_count", "teacher_round_size", "probe_phase_size", "arms", "phases", "source_read_limit", "diagnostic_call_limit", "receipt_count"}
ARMS = ("raw_only", "raw_plus_judgment", "all_raw_upfront")
PHASES = ("same_version", "changed_version")


def verify_pins(root, expected_protocol_sha256):
    root = safe(root, root)
    sha_string(expected_protocol_sha256)
    protocol_path = safe(root / "PROTOCOL.json", root)
    need(sha(protocol_path) == expected_protocol_sha256, "frozen protocol bytes differ")
    protocol = loads(protocol_path.read_bytes())
    keys(protocol, PROTOCOL_KEYS)
    need(protocol["schema"] == "judgment-transfer-protocol.v1", "unknown protocol schema")
    need(protocol["mode"] in {"actual_pilot", "synthetic_engineering"}, "invalid protocol mode")
    need(protocol["world_count"] == 6 and protocol["teacher_round_size"] == 6 and protocol["probe_phase_size"] == 18, "fixed design sizes differ")
    need(protocol["arms"] == list(ARMS) and protocol["phases"] == list(PHASES), "fixed design conditions differ")
    need(protocol["source_read_limit"] == 6 and protocol["diagnostic_call_limit"] == 1 and protocol["receipt_count"] == 6, "fixed evidence budgets differ")
    need(protocol["worlds_path"] == "input/WORLDS.json", "fixed worlds path differs")
    need(sha(safe(root / protocol["worlds_path"], root)) == protocol["worlds_sha256"], "frozen world bytes differ")
    need(protocol["preregistration_path"] == "PREREGISTRATION.json", "fixed preregistration path differs")
    sha_string(protocol["preregistration_sha256"])
    need(sha(safe(root / protocol["preregistration_path"], root)) == protocol["preregistration_sha256"], "frozen preregistration bytes differ")
    preregistration = loads((root / protocol["preregistration_path"]).read_bytes())
    input_pins = preregistration.get("input_sha256")
    need(type(input_pins) is dict, "preregistration input_sha256 map required")
    if protocol["mode"] == "actual_pilot":
        need({"input/WORLDS.json", "input/ASSIGNMENTS.json"} <= set(input_pins), "actual preregistration must bind worlds and assignment schedule")
        need(input_pins["input/WORLDS.json"] == protocol["worlds_sha256"], "world/preregistration pin differs")
    for name, expected in input_pins.items():
        need(type(name) is str and not Path(name).is_absolute(), "input pin must be root relative")
        sha_string(expected)
        need(sha(safe(root / name, root)) == expected, "preregistered input bytes differ: " + name)
    code_pins = protocol["code_sha256"]
    need(type(code_pins) is dict and set(code_pins) == {"code/common.py", "code/world_engine.py", "code/transport.py", "code/worker.py"}, "complete code pins required")
    for name, expected in code_pins.items():
        sha_string(expected)
        need(sha(safe(root / name, root)) == expected, "frozen code bytes differ: " + name)
    return protocol
