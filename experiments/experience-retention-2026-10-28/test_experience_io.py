"""Synthetic apparatus checks only; no study actions, tasks, or gold are read."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import action_loop
import experience_io as io


class ExperienceIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".experience-engineering-", dir=Path(__file__).parent.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.originals = self.root / "input/originals"
        self.originals.mkdir(parents=True)
        self.environment = self.root / "input/environment"
        self.fixtures = {
            "X01": {"sample": {"id": "条件-雪", "types": [True, 1, 1.0, False, 0, 0.0, -0.0, None, "秘密"]}, "unretained": {"id": "hide-root"}},
            "X02": {"conditions": [{"id": "b", "n": 4.25}, {"id": "a", "n": 2}], "other": "hide"},
            "X03": {"sample": {}, "conditions": [], "per_query": {"id": "omit"}, "provenance": ["omit"]},
        }
        for alias, value in self.fixtures.items():
            self.write(self.originals / (alias + ".json"), value)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def read(path):
        return action_loop.parse_json(path.read_bytes())

    @staticmethod
    def action(item_id="P01", **changes):
        value = {"id": item_id, "prediction": "uncertain", "rationale": "Synthetic fixture.", "status": "write",
                 "fields": {"answer": {"op": "get", "source": "A01", "path": ["sample", "value"]}}}
        value.update(changes)
        return value

    def build(self):
        return io.build_environment(self.originals, self.environment)

    def test_build_fixed_maps_neutral_catalogs_and_no_presupplied_observations(self):
        self.build()
        maps = {stage: self.read(self.environment / ("source_map_" + stage + ".json")) for stage in ("original", "changed", "probes")}
        self.assertEqual(maps["original"], {a: "../originals/" + a + ".json" for a in io.ALIASES})
        self.assertEqual(maps["changed"], {a: "migrated/" + a + ".json" for a in io.ALIASES})
        self.assertEqual(maps["probes"], {"A01": "migrated/X02.json", "A02": "../originals/X01.json", "A03": "migrated/X03.json",
                                          "A04": "../originals/X02.json", "A05": "migrated/X01.json", "A06": "../originals/X03.json"})
        for stage, mapping in maps.items():
            catalog = self.read(self.environment / ("catalog_" + stage + ".json"))
            self.assertEqual(set(catalog), set(mapping))
            for alias, relative in mapping.items():
                record = catalog[alias]
                self.assertEqual(set(record), {"family", "raw_sha256"})
                self.assertEqual(record["family"], Path(relative).stem)
                self.assertEqual(record["raw_sha256"], hashlib.sha256((self.environment / relative).read_bytes()).hexdigest())
        self.assertFalse(any("observation" in p.name for p in self.environment.rglob("*")))
        self.assertEqual(len([p for p in self.environment.rglob("*") if p.is_file()]), 10)

    def test_exact_payload_types_unicode_hashes_and_unchanged_original_bytes(self):
        before = {a: (self.originals / (a + ".json")).read_bytes() for a in io.ALIASES}
        invariants = self.build()
        self.assertEqual(invariants, self.read(self.environment / "INVARIANTS.json"))
        for alias in io.ALIASES:
            path = self.environment / "migrated" / (alias + ".json")
            wrapped = self.read(path)
            self.assertEqual(set(wrapped), {"schema_version", "payload"})
            self.assertEqual(wrapped["schema_version"], "artifact-container.v2")
            self.assertTrue(io.exact_json_equal(wrapped["payload"], self.fixtures[alias]))
            raw = (self.originals / (alias + ".json")).read_bytes()
            self.assertEqual(raw, before[alias])
            record = invariants["files"][alias]
            self.assertEqual(record["original_sha256_before"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["original_sha256_after"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["changed_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(record["canonical_payload_sha256"], hashlib.sha256(action_loop.canonical_json(wrapped["payload"]).encode()).hexdigest())
            self.assertIs(record["payload_matches_original_including_types"], True)
        for left, right in ((True, 1), (1, 1.0), (0.0, -0.0), (1.0, 1.0000000000000002)):
            self.assertFalse(io.exact_json_equal(left, right))

    def test_strict_parsing_missing_sources_and_original_symlinks_fail_before_build(self):
        path = self.originals / "X02.json"
        saved = path.read_bytes()
        cases = [b'{"a":', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e309}', b'{"a":"\xff"}', b'{"a":"\\ud800"}']
        for raw in cases:
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaises(io.ExperienceIOError): self.build()
                self.assertFalse(self.environment.exists())
        path.unlink()
        with self.assertRaises(io.ExperienceIOError): self.build()
        target = self.root / "original-real.json"
        target.write_bytes(saved)
        path.symlink_to(target)
        with self.assertRaisesRegex(io.ExperienceIOError, "symlinks"): self.build()
        self.assertFalse(self.environment.exists())

    def test_boundary_projection_only_enters_sample_conditions_and_payload_containers(self):
        value = {"id": "hide", "sample": {"id": "keep", "deep": {"value": 9}}, "metadata": {"sample": {"id": "hidden"}},
                 "payload": {"payload": [{"conditions": [{"id": "yes", "n": 4}], "unrelated": [1, 2]}, 7]}, "schema_version": "secret"}
        projected = io.structural_projection(value)
        self.assertEqual(set(projected), set(value))
        self.assertEqual(projected["id"], {"$omitted": True, "$type": "string"})
        self.assertEqual(projected["schema_version"], {"$omitted": True, "$type": "string"})
        self.assertEqual(projected["metadata"], {"$omitted": True, "$type": "object"})
        self.assertEqual(projected["sample"]["id"], {"$type": "string", "observed_value": "keep"})
        self.assertEqual(projected["sample"]["deep"], {"value": {"$type": "integer"}})
        self.assertEqual(projected["payload"]["payload"][0]["conditions"][0]["id"]["observed_value"], "yes")
        self.assertEqual(projected["payload"]["payload"][0]["unrelated"], {"$omitted": True, "$type": "array"})
        self.assertEqual(projected["payload"]["payload"][1], {"$omitted": True, "$type": "integer"})
        self.assertEqual(io.structural_projection({"payload": "hide"}), {"payload": {"$omitted": True, "$type": "string"}})

    def test_retained_projection_omits_reserved_branches_and_masks_all_other_scalars(self):
        value = {"per_query": {"id": "root-hidden"}, "sample": {"id": ["not-inherited", {"id": "visible"}],
                 "types": [True, 3, 3.0, "secret", None, {}, []], "per_query": {"id": "hidden"},
                 "deep": {"provenance": [{"id": "hidden-again"}], "id": False}, "$type": "source-key"}, "provenance": None}
        p = io.structural_projection(value)
        self.assertEqual(p["per_query"], {"$omitted": True, "$type": "object"})
        self.assertEqual(p["provenance"], {"$omitted": True, "$type": "null"})
        self.assertEqual(p["sample"]["per_query"], {"$omitted": True, "$type": "object"})
        self.assertEqual(p["sample"]["deep"]["provenance"], {"$omitted": True, "$type": "array"})
        self.assertEqual(p["sample"]["id"], [{"$type": "string"}, {"id": {"$type": "string", "observed_value": "visible"}}])
        self.assertEqual(p["sample"]["types"], [{"$type": "boolean"}, {"$type": "integer"}, {"$type": "number"}, {"$type": "string"}, {"$type": "null"}, {}, []])
        self.assertEqual(p["sample"]["deep"]["id"], {"$type": "boolean"})
        self.assertEqual(p["sample"]["$type"], {"$type": "string"})

    def test_selected_only_inspection_reads_actual_bytes_and_reports_character_cost(self):
        self.build()
        mapping = self.environment / "source_map_original.json"
        selected = self.originals / "X01.json"
        self.write(selected, {"sample": {"id": "実際に変更した雪", "value": 888}, "other": 999})
        selected_raw = selected.read_bytes()
        (self.originals / "X02.json").write_bytes(b"unreadable JSON")
        (self.originals / "X03.json").unlink()
        actual_reads = []
        real_read = Path.read_bytes
        def read_spy(path):
            actual_reads.append(path.resolve())
            return real_read(path)
        output = self.root / "inspection.json"
        with patch.object(Path, "read_bytes", read_spy):
            record = io.inspect_source(mapping, "X01", output)
        self.assertEqual(actual_reads, [mapping.resolve(), selected.resolve()])
        self.assertEqual(record, self.read(output))
        self.assertEqual(record["source"], "X01")
        self.assertEqual(record["raw_sha256"], hashlib.sha256(selected_raw).hexdigest())
        self.assertEqual(record["raw_bytes_read"], len(selected_raw))
        self.assertEqual(record["observation"]["sample"]["id"]["observed_value"], "実際に変更した雪")
        self.assertEqual(record["returned_canonical_characters"], len(action_loop.canonical_json(record["observation"])))
        self.assertGreater(len(action_loop.canonical_json(record["observation"]).encode()), record["returned_canonical_characters"])
        self.assertIn("excluding this metadata", record["observation_metadata"]["character_accounting"])

    def test_inspection_path_safety_and_build_inspect_outputs_never_overwrite(self):
        self.build()
        unchanged = (self.environment / "INVARIANTS.json").read_bytes()
        with self.assertRaises(io.ExperienceIOError): self.build()
        self.assertEqual((self.environment / "INVARIANTS.json").read_bytes(), unchanged)
        mapping = self.environment / "source_map_original.json"
        output = self.root / "inspection.json"
        output.write_bytes(b"sentinel")
        with self.assertRaises(io.ExperienceIOError): io.inspect_source(mapping, "X01", output)
        self.assertEqual(output.read_bytes(), b"sentinel")
        output.unlink()
        with self.assertRaises(io.ExperienceIOError): io.inspect_source(mapping, "unknown", output)
        self.write(mapping, {"X01": "../../outside.json"})
        self.write(self.root / "outside.json", {"sample": {"id": "escape"}})
        with self.assertRaisesRegex(io.ExperienceIOError, "escapes"): io.inspect_source(mapping, "X01", output)
        self.write(mapping, {"X01": "../originals/X01.json"})
        selected = self.originals / "X01.json"
        saved = selected.read_bytes()
        selected.unlink()
        target = self.root / "source-target.json"
        target.write_bytes(saved)
        selected.symlink_to(target)
        with self.assertRaisesRegex(io.ExperienceIOError, "symlinks"): io.inspect_source(mapping, "X01", output)
        self.assertFalse(output.exists())

    def test_policy_exact_shapes_task_ids_and_copied_action_validation_without_execution(self):
        inspect = {"id": "P01", "decision": "inspect", "rationale": "Actual choice supplied by caller."}
        self.assertIsNone(io.validate_policy(inspect, "P01")["canonical_action_characters"])
        unavailable = self.action(status="unavailable", fields={})
        with patch.object(action_loop, "execute_action", side_effect=AssertionError("must not execute")):
            self.assertFalse(io.validate_policy({"id": "P01", "decision": "submit", "action": unavailable}, "P01")["budget_exceeded"])
        cases = [dict(inspect, extra=True), {"id": "P01", "decision": "inspect"}, dict(inspect, rationale=4),
                 dict(inspect, id="P02"), {"id": "P01", "decision": "other"},
                 {"id": "P01", "decision": "submit", "action": self.action("P02")},
                 {"id": "P01", "decision": "submit", "action": self.action(prediction="invalid")},
                 {"id": "P01", "decision": "submit", "action": self.action(fields={"x": {"op": "get", "source": "A01", "path": [True]}})},
                 {"id": "P01", "decision": "submit", "action": self.action(), "rationale": "extra"}]
        for policy in cases:
            with self.subTest(policy=policy):
                with self.assertRaises(io.ExperienceIOError): io.validate_policy(policy, "P01")

    def test_policy_budget_boundary_flags_and_retains_oversize_action(self):
        for length, exceeded in ((6000, False), (6001, True)):
            action = self.action(rationale="")
            action["rationale"] = "雪" * (length - len(action_loop.canonical_json(action)))
            policy = {"id": "P01", "decision": "submit", "action": action}
            before = copy.deepcopy(policy)
            result = io.validate_policy(policy, "P01")
            self.assertEqual(result["canonical_action_characters"], length)
            self.assertEqual(result["budget_limit"], 6000)
            self.assertIs(result["budget_exceeded"], exceeded)
            self.assertEqual(policy, before)

    def test_delayed_guard_before_exact_after_actual_default_and_invalid_clock(self):
        freeze = self.root / "memory-freeze.json"
        self.write(freeze, {"frozen_at_unix": 1000, "other_frozen_metadata": "allowed"})
        with self.assertRaises(io.DelayedNotDueError): io.check_delayed_due(freeze, 87399.999)
        for now, elapsed in ((87400, 86400), (87400.25, 86400.25)):
            result = io.check_delayed_due(freeze, now)
            self.assertEqual(result["elapsed_seconds"], elapsed)
            self.assertEqual(result["due_unix"], 87400)
            self.assertIs(result["due"], True)
        with patch.object(io.time, "time", return_value=87401) as actual_clock:
            self.assertEqual(io.check_delayed_due(freeze)["checked_at_unix"], 87401)
            actual_clock.assert_called_once_with()
        for value in (True, "1000", -1, 10 ** 1000):
            self.write(freeze, {"frozen_at_unix": value})
            with self.assertRaises(io.ExperienceIOError): io.check_delayed_due(freeze, 87400)
        self.write(freeze, {"frozen_at_unix": 1000})
        for value in (True, float("nan"), float("inf"), -1):
            with self.assertRaises(io.ExperienceIOError): io.check_delayed_due(freeze, value)
        # At extreme finite floats, adding one day may round to the same value;
        # an elapsed-time check must still refuse zero elapsed seconds.
        self.write(freeze, {"frozen_at_unix": 1e308})
        with self.assertRaises(io.DelayedNotDueError): io.check_delayed_due(freeze, 1e308)
        self.write(freeze, {"missing": 1000})
        with self.assertRaises(io.ExperienceIOError): io.check_delayed_due(freeze, 87400)


if __name__ == "__main__":
    unittest.main()
