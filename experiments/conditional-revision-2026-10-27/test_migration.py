"""Synthetic engineering checks; these fixtures are not research tasks.

Run: PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v test_migration
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import action_loop
import migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".migration-engineering-", dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.originals = self.root / "originals"
        self.originals.mkdir()
        self.out = self.root / "environment"
        self.fixtures = {
            "D01": {"id": "条件-α", "values": [True, 1, 1.0, False, 0, 0.0, -0.0, None, "雪☃"]},
            "D02": {"rows": [{"id": "b", "x": 4.25}, {"id": "a", "x": 2}], "empty": []},
            "D03": {"per_query": {"id": "OMIT-ME", "n": 91}, "provenance": [{"id": "ALSO-OMIT"}], "ok": {}},
        }
        for alias, value in self.fixtures.items():
            self.write_original(alias, value)

    def write_original(self, alias, value):
        (self.originals / (alias + ".json")).write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"
        )

    def read(self, name):
        return action_loop.parse_json((self.out / name).read_bytes())

    def build(self):
        return migration.build_environment(self.originals, self.out)

    def test_exact_payload_types_unicode_and_original_bytes(self):
        original_bytes = {p.name: p.read_bytes() for p in self.originals.iterdir()}
        self.build()
        for alias, fixture in self.fixtures.items():
            wrapped = self.read("migrated/" + alias + ".json")
            self.assertEqual(set(wrapped), {"schema_version", "payload"})
            self.assertEqual(wrapped["schema_version"], "artifact-container.v2")
            self.assertTrue(migration.exact_json_equal(wrapped["payload"], fixture))
        self.assertEqual(original_bytes, {p.name: p.read_bytes() for p in self.originals.iterdir()})
        for left, right in ((True, 1), (1, 1.0), (0.0, -0.0), (1.0, 1.0000000000000002)):
            with self.subTest(left=left, right=right):
                self.assertFalse(migration.exact_json_equal(left, right))

    def test_required_inputs_and_unrelated_invalid_file(self):
        (self.originals / "unrelated.json").write_bytes(b"not JSON")
        self.build()
        self.assertEqual(set(self.read("source_map_v1.json")), set(migration.ALIASES))
        for alias in migration.ALIASES:
            with self.subTest(missing=alias):
                path = self.originals / (alias + ".json")
                saved = path.read_bytes()
                path.unlink()
                candidate = self.root / ("missing-" + alias)
                with self.assertRaises(migration.MigrationError):
                    migration.build_environment(self.originals, candidate)
                self.assertFalse(candidate.exists())
                path.write_bytes(saved)

    def test_strict_parsing_rejects_malformed_duplicate_nonfinite_and_unicode(self):
        cases = [b'{"x":', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                 b'{"x":-Infinity}', b'{"x":1e309}', b'{"x":"\xff"}',
                 b'{"x":"\\ud800"}', b'{"\\ud800":1}']
        for index, raw in enumerate(cases):
            with self.subTest(raw=raw):
                (self.originals / "D02.json").write_bytes(raw)
                candidate = self.root / ("invalid-" + str(index))
                with self.assertRaises(migration.MigrationError):
                    migration.build_environment(self.originals, candidate)
                self.assertFalse(candidate.exists())

    def test_relative_maps_and_path_free_catalog(self):
        self.build()
        v1 = self.read("source_map_v1.json")
        v2 = self.read("source_map_v2.json")
        later = self.read("source_map_later.json")
        catalog = self.read("catalog.json")
        self.assertEqual(v1, {a: "../originals/" + a + ".json" for a in migration.ALIASES})
        self.assertEqual(v2, {a: "migrated/" + a + ".json" for a in migration.ALIASES})
        self.assertEqual(set(later), {"S01", "S02", "S03", "S04", "S05", "S06"})
        for index, alias in enumerate(migration.ALIASES):
            for offset, source_map, format_name in ((1, v1, "legacy_root"), (2, v2, "wrapped_v2")):
                source_alias = "S%02d" % (index * 2 + offset)
                self.assertEqual(later[source_alias], source_map[alias])
                self.assertFalse(Path(later[source_alias]).is_absolute())
                self.assertTrue((self.out / later[source_alias]).is_file())
                self.assertEqual(catalog[source_alias], {"origin_alias": alias, "format": format_name})
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        with self.assertRaises(migration.MigrationError):
            migration.build_environment(self.originals, elsewhere / "environment")

    def test_structural_projection_retains_keys_array_order_and_exact_types(self):
        value = {"nested": [True, 5, 5.0, "secret", None, {}, [], {"id": "keep"}],
                 "$type": 7, "$omitted": False, "observed_value": "hide"}
        expected = {"nested": [{"$type": "boolean"}, {"$type": "integer"}, {"$type": "number"},
                               {"$type": "string"}, {"$type": "null"}, {}, [],
                               {"id": {"$type": "string", "observed_value": "keep"}}],
                    "$type": {"$type": "integer"}, "$omitted": {"$type": "boolean"},
                    "observed_value": {"$type": "string"}}
        self.assertEqual(migration.structural_projection(value), expected)

    def test_only_string_id_values_survive_and_omissions_precede_recursion(self):
        value = {"id": ["not-authorized", {"id": "authorized"}], "number": 8675309,
                 "flag": True, "text": "secret", "numeric_id": {"id": 12},
                 "boolean_id": {"id": False}, "per_query": {"id": "hidden-id"},
                 "nested": {"provenance": [{"id": "hidden-again"}], "id": "visible"},
                 "provenance": None}
        projection = migration.structural_projection(value)
        self.assertEqual(projection["per_query"], {"$omitted": True, "$type": "object"})
        self.assertEqual(projection["nested"]["provenance"], {"$omitted": True, "$type": "array"})
        self.assertEqual(projection["provenance"], {"$omitted": True, "$type": "null"})
        observed_values = []
        def check(node):
            if type(node) is dict:
                for key, child in node.items():
                    if key == "$type":
                        self.assertIn(child, {"object", "array", "string", "integer", "number", "boolean", "null"})
                    elif key == "$omitted":
                        self.assertIs(child, True)
                    elif key == "observed_value":
                        self.assertIs(type(child), str)
                        observed_values.append(child)
                    else:
                        check(child)
            elif type(node) is list:
                for child in node:
                    check(child)
            else:
                self.fail("unmasked source scalar: " + repr(node))
        check(projection)
        self.assertEqual(observed_values, ["authorized", "visible"])

    def test_hash_evidence_and_projection_use_actual_written_readbacks(self):
        real_parse = migration.parse_json
        real_read = migration._read_json
        written_readbacks = []
        projected_reads = []
        real_projection = migration.structural_projection
        def observed_read(path):
            raw, value = real_read(path)
            if path.parent == self.out / "migrated":
                self.assertEqual(raw, path.read_bytes())
                written_readbacks.append(value)
            return raw, value
        def observed_projection(value, member_key=None):
            if member_key is None and type(value) is dict and set(value) == {"schema_version", "payload"}:
                self.assertTrue(any(value is readback for readback in written_readbacks))
                projected_reads.append(value)
            return real_projection(value, member_key)
        with patch.object(migration, "_read_json", side_effect=observed_read), patch.object(migration, "structural_projection", side_effect=observed_projection):
            invariants = self.build()
        self.assertEqual(len(projected_reads), 3)
        self.assertEqual(len(written_readbacks), 3)
        self.assertEqual(invariants, self.read("INVARIANTS.json"))
        timestamp = datetime.fromisoformat(invariants["created_at_utc"].replace("Z", "+00:00"))
        self.assertEqual(timestamp.tzinfo, timezone.utc)
        observations = self.read("observations.json")
        self.assertIn("observation_metadata", observations)
        self.assertEqual(invariants["observations_file_sha256"], hashlib.sha256((self.out / "observations.json").read_bytes()).hexdigest())
        for alias in migration.ALIASES:
            record = invariants["files"][alias]
            raw = (self.originals / (alias + ".json")).read_bytes()
            wrapped_raw = (self.out / "migrated" / (alias + ".json")).read_bytes()
            wrapped = real_parse(wrapped_raw)
            projection = real_projection(wrapped)
            self.assertEqual(observations["observations"][alias], projection)
            self.assertEqual(record["original_sha256_before"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["original_sha256_after"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["wrapped_sha256"], hashlib.sha256(wrapped_raw).hexdigest())
            self.assertEqual(record["canonical_payload_sha256"], hashlib.sha256(action_loop.canonical_json(wrapped["payload"]).encode()).hexdigest())
            self.assertEqual(record["observation_sha256"], hashlib.sha256(action_loop.canonical_json(projection).encode()).hexdigest())
            self.assertIs(record["payload_matches_original_including_types"], True)
            self.assertIs(record["original_bytes_unchanged"], True)

    def test_existing_output_file_directory_symlink_and_cli_never_overwrite(self):
        self.out.mkdir()
        sentinel = self.out / "sentinel"
        sentinel.write_bytes(b"keep directory bytes")
        file_path = self.root / "existing-file"
        file_path.write_bytes(b"keep file bytes")
        link_path = self.root / "existing-link"
        link_path.symlink_to(file_path)
        broken_link = self.root / "broken-link"
        broken_link.symlink_to(self.root / "missing-target")
        before = {p.name: p.read_bytes() for p in self.originals.iterdir()}
        for candidate in (self.out, file_path, link_path, broken_link):
            with self.subTest(candidate=candidate.name):
                with self.assertRaises(migration.MigrationError):
                    migration.build_environment(self.originals, candidate)
        self.assertEqual(sentinel.read_bytes(), b"keep directory bytes")
        self.assertEqual(file_path.read_bytes(), b"keep file bytes")
        self.assertTrue(link_path.is_symlink())
        self.assertTrue(broken_link.is_symlink())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.originals.iterdir()})
        result = subprocess.run([sys.executable, "-B", str(Path(migration.__file__)), "build", "--originals", str(self.originals), "--out", str(self.out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("output already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()
