"""Synthetic engineering checks for the deterministic action/feedback harness.

These fixtures exercise the harness contract; they are not research task data.
Run with: PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import action_loop


def canonical_text(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def get(source="fixture", path=None):
    return {"op": "get", "source": source, "path": [] if path is None else path}


def action(item_id="synthetic-1", fields=None, **overrides):
    value = {
        "id": item_id,
        "prediction": "accepted",
        "rationale": "Synthetic engineering fixture.",
        "status": "write",
        "fields": {"answer": get(path=["answer"])} if fields is None else fields,
    }
    value.update(overrides)
    return value


def expected_ok(values):
    return {"status": "ok", "values": values}


class ActionLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix=".engineering-", dir=Path(__file__).resolve().parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.map_path = self.root / "sources.json"
        self.actions_path = self.root / "actions.json"
        self.expected_path = self.root / "expected.json"
        self.out_path = self.root / "output"
        self.write_json(self.root / "fixture.json", {"answer": 7})
        self.write_json(self.map_path, {"fixture": "fixture.json"})

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")

    @staticmethod
    def read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def run_actions(self, actions, expected, out_path=None):
        self.write_json(self.actions_path, actions)
        self.write_json(self.expected_path, expected)
        return action_loop.run_batch(
            self.map_path, self.actions_path, self.expected_path, out_path or self.out_path
        )

    def item_files(self, summary, index=0, out_path=None):
        directory = summary["items"][index]["directory"]
        self.assertEqual(directory, "item-{:04d}".format(index + 1))
        item_dir = (out_path or self.out_path) / directory
        self.assertTrue(item_dir.is_dir())
        return item_dir

    def verdict(self, summary, index=0, out_path=None):
        return self.read_json(self.item_files(summary, index, out_path) / "validation.json")["status"]

    def assert_execution_failure(self, summary, index=0, out_path=None, raw_status=None):
        item_dir = self.item_files(summary, index, out_path)
        self.assertFalse((item_dir / "artifact.json").exists())
        execution = self.read_json(item_dir / "execution.json")
        if raw_status is not None:
            self.assertEqual(execution["raw_status"], raw_status)
        else:
            self.assertIn(execution["raw_status"], ("invalid_action", "execution_error"))
        self.assertIsInstance(execution["error"], dict)
        self.assertTrue(execution["error"]["type"])
        self.assertTrue(execution["error"]["message"])
        self.assertIn("input_hashes", execution)
        self.assertEqual(self.verdict(summary, index, out_path), "rejected")
        return execution

    def assert_fatal(self, out_path=None):
        output = out_path or self.out_path
        with self.assertRaises(action_loop.HarnessError):
            action_loop.run_batch(self.map_path, self.actions_path, self.expected_path, output)
        self.assertTrue((output / "run_summary.json").is_file())
        self.assertEqual(self.read_json(output / "run_summary.json")["status"], "failed")
        self.assertFalse(any(output.glob("item-*")), "Fatal input errors must precede execution")

    def test_relative_sources_nested_get_and_all_arithmetic_operators(self):
        # Resolve against sources.json's parent, including an indexed nested get.
        self.write_json(self.root / "inputs" / "numbers.json", {"rows": [{"n": 12}, {"n": 4}]})
        self.write_json(self.map_path, {"numbers": "inputs/numbers.json"})
        left = get("numbers", ["rows", 0, "n"])
        right = get("numbers", ["rows", 1, "n"])
        fields = {
            "get": right,
            "sum": {"op": "sum", "args": [left, right]},
            "difference": {"op": "sub", "left": left, "right": right},
            "quotient": {"op": "div", "left": left, "right": right},
        }
        item = action(fields=fields)
        expected = expected_ok({"get": 4, "sum": 16, "difference": 8, "quotient": 3.0})
        summary = self.run_actions([item], {item["id"]: expected})
        item_dir = self.item_files(summary)
        self.assertEqual(self.read_json(item_dir / "artifact.json"), expected)
        self.assertEqual(self.verdict(summary), "accepted")
        execution = self.read_json(item_dir / "execution.json")
        self.assertEqual(execution["raw_status"], "ok")
        self.assertIsNone(execution["error"])
        self.assertIsInstance(execution["input_hashes"], dict)
        self.assertTrue(execution["input_hashes"])
        self.assertEqual(execution["action_sha256"], hashlib.sha256(canonical_text(item).encode("utf-8")).hexdigest())
        self.assertEqual(execution["artifact_sha256"], hashlib.sha256((item_dir / "artifact.json").read_bytes()).hexdigest())

    def test_prediction_is_recorded_independently_of_actual_validation(self):
        actions = [action("predicted-rejected", prediction="rejected"), action("predicted-accepted")]
        summary = self.run_actions(actions, {
            "predicted-rejected": expected_ok({"answer": 7}),
            "predicted-accepted": expected_ok({"answer": 999}),
        })
        self.assertEqual(self.verdict(summary, 0), "accepted")
        self.assertEqual(self.verdict(summary, 1), "rejected")

    def test_unavailable_action_matches_unavailable_expectation(self):
        item = action(status="unavailable", fields={}, prediction="uncertain")
        expected = {"status": "unavailable", "values": None}
        summary = self.run_actions([item], {item["id"]: expected})
        item_dir = self.item_files(summary)
        self.assertEqual(self.read_json(item_dir / "artifact.json"), expected)
        self.assertEqual(self.read_json(item_dir / "execution.json")["raw_status"], "unavailable")
        self.assertEqual(self.verdict(summary), "accepted")

    def test_unavailable_action_is_rejected_when_values_are_expected(self):
        item = action(status="unavailable", fields={})
        summary = self.run_actions([item], {item["id"]: expected_ok({"answer": 7})})
        self.assertEqual(self.verdict(summary), "rejected")
        self.assertEqual(self.read_json(self.item_files(summary) / "artifact.json"), {"status": "unavailable", "values": None})

    def test_value_mismatches_and_distinct_scalar_types_are_rejected(self):
        self.write_json(self.root / "fixture.json", {"answer": 7, "flag": True, "float": 7.0})
        actions = [
            action("wrong-value"),
            action("wrong-fields"),
            action("bool-is-not-int", fields={"answer": get(path=["flag"])}),
            action("float-is-not-int", fields={"answer": get(path=["float"])}),
        ]
        summary = self.run_actions(actions, {
            "wrong-value": expected_ok({"answer": 8}),
            "wrong-fields": expected_ok({"answer": 7, "extra": 1}),
            "bool-is-not-int": expected_ok({"answer": 1}),
            "float-is-not-int": expected_ok({"answer": 7}),
        })
        for index in range(len(actions)):
            with self.subTest(index=index):
                self.assertEqual(self.verdict(summary, index), "rejected")
                self.assertEqual(self.read_json(self.item_files(summary, index) / "execution.json")["raw_status"], "ok")
                self.assertTrue((self.item_files(summary, index) / "artifact.json").is_file())

    def test_missing_path_fails_one_item_and_following_item_still_runs(self):
        self.write_json(self.root / "fixture.json", {"answer": 7, "rows": [7]})
        items = [
            action("missing", fields={"answer": get(path=["absent"])}),
            action("negative-index", fields={"answer": get(path=["rows", -1])}),
            action("scalar-traversal", fields={"answer": get(path=["answer", "child"])}),
            action("valid"),
        ]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        for index in range(3):
            with self.subTest(path=items[index]["fields"]["answer"]["path"]):
                self.assert_execution_failure(summary, index, raw_status="execution_error")
        self.assertEqual(self.verdict(summary, 3), "accepted")

    def test_get_validates_source_alias_and_final_leaf_types(self):
        self.write_json(self.root / "fixture.json", {
            "answer": 7, "text": "synthetic text", "flag": True, "nothing": None,
            "object": {"nested": 7}, "list": [7],
        })
        items = [action("unknown-source", fields={"answer": get("not-in-map", ["answer"])})]
        values = {"unknown-source": expected_ok({"answer": 7})}
        leaf_cases = [("text", "synthetic text"), ("flag", True), ("nothing", None)]
        for name, value in leaf_cases:
            items.append(action(name, fields={"answer": get(path=[name])}))
            values[name] = expected_ok({"answer": value})
        for name in ("object", "list"):
            items.append(action(name, fields={"answer": get(path=[name])}))
            values[name] = expected_ok({"answer": None})
        summary = self.run_actions(items, values)
        self.assert_execution_failure(summary, 0)
        for index, (name, _) in enumerate(leaf_cases, start=1):
            with self.subTest(accepted_leaf=name):
                self.assertEqual(self.verdict(summary, index), "accepted")
                self.assertEqual(self.read_json(self.item_files(summary, index) / "artifact.json"), values[name])
        for index in (4, 5):
            with self.subTest(rejected_container=items[index]["id"]):
                self.assert_execution_failure(summary, index, raw_status="execution_error")

    def test_missing_and_malformed_source_files_do_not_poison_unrelated_item(self):
        (self.root / "broken.json").write_text('{"answer":', encoding="utf-8")
        (self.root / "duplicate.json").write_text('{"answer":7,"answer":8}', encoding="utf-8")
        self.write_json(self.map_path, {
            "missing": "missing.json", "broken": "broken.json", "duplicate": "duplicate.json", "fixture": "fixture.json",
        })
        items = [action("missing-file", fields={"answer": get("missing", ["answer"])}),
                 action("malformed-file", fields={"answer": get("broken", ["answer"])}),
                 action("duplicate-key-file", fields={"answer": get("duplicate", ["answer"])}), action("valid")]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        for index in range(3):
            with self.subTest(source_failure=items[index]["id"]):
                self.assert_execution_failure(summary, index)
        self.assertEqual(self.verdict(summary, 3), "accepted")

    def test_nonfinite_values_in_source_json_are_rejected(self):
        for index, token in enumerate(("NaN", "Infinity", "-Infinity", "1e309")):
            with self.subTest(nonfinite_token=token):
                (self.root / "fixture.json").write_text('{"answer":' + token + '}', encoding="utf-8")
                item = action()
                output = self.root / "nonfinite-{}".format(index)
                summary = self.run_actions([item], {item["id"]: expected_ok({"answer": 7})}, out_path=output)
                self.assert_execution_failure(summary, out_path=output)

    def test_arithmetic_rejects_boolean_operands_and_float_overflow(self):
        self.write_json(self.root / "fixture.json", {"answer": 7, "flag": True, "huge": 1e308})
        flag = get(path=["flag"])
        number = get(path=["answer"])
        huge = get(path=["huge"])
        bad_cases = [
            ("sum-bool", {"op": "sum", "args": [flag, number]}),
            ("sub-left-bool", {"op": "sub", "left": flag, "right": number}),
            ("sub-right-bool", {"op": "sub", "left": number, "right": flag}),
            ("div-left-bool", {"op": "div", "left": flag, "right": number}),
            ("div-right-bool", {"op": "div", "left": number, "right": flag}),
            ("sum-overflow", {"op": "sum", "args": [huge, huge]}),
        ]
        items = [action(name, fields={"answer": expression}) for name, expression in bad_cases]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 0}) for item in items})
        for index, (name, _) in enumerate(bad_cases):
            with self.subTest(arithmetic_failure=name):
                self.assert_execution_failure(summary, index, raw_status="execution_error")

    def test_division_by_zero_produces_no_artifact(self):
        self.write_json(self.root / "fixture.json", {"answer": 7, "zero": 0})
        item = action(fields={"answer": {"op": "div", "left": get(path=["answer"]), "right": get(path=["zero"])}})
        summary = self.run_actions([item], {item["id"]: expected_ok({"answer": 0.0})})
        self.assert_execution_failure(summary, raw_status="execution_error")

    def test_expression_schema_rejects_extra_keys_invalid_paths_and_unknown_ops(self):
        bad_expressions = [
            {"op": "get", "source": "fixture", "path": ["answer"], "extra": 1},
            {"op": "get", "source": "fixture", "path": [True]},
            {"op": "get", "source": "fixture", "path": "answer"},
            {"op": "sum", "args": []},
            {"op": "sum", "args": [7]},
            {"op": "sub", "left": get(path=["answer"])},
            {"op": "exec", "command": "synthetic-no-op"},
        ]
        items = [action("bad-expression-{}".format(index), fields={"answer": expr}) for index, expr in enumerate(bad_expressions)]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        for index in range(len(items)):
            with self.subTest(index=index):
                self.assert_execution_failure(summary, index, raw_status="invalid_action")

    def test_action_schema_rejects_wrong_field_types_and_invalid_enums(self):
        items = [
            action("bad-prediction", prediction="maybe"),
            action("bad-status", status="ok"),
            action("bad-rationale", rationale=17),
            action("bad-fields", fields=[]),
            action("unavailable-fields", status="unavailable", fields={"answer": get(path=["answer"])}),
        ]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        for index in range(len(items)):
            with self.subTest(index=index):
                self.assert_execution_failure(summary, index, raw_status="invalid_action")

    def test_float_tolerance_accepts_small_error_and_rejects_larger_error(self):
        self.write_json(self.root / "fixture.json", {"answer": 1.0})
        items = [action("within-tolerance"), action("outside-tolerance")]
        summary = self.run_actions(items, {
            "within-tolerance": expected_ok({"answer": 1.0 + 0.5e-12}),
            "outside-tolerance": expected_ok({"answer": 1.0 + 2e-12}),
        })
        self.assertEqual(self.verdict(summary, 0), "accepted")
        self.assertEqual(self.verdict(summary, 1), "rejected")

    def test_duplicate_action_ids_are_fatal_before_item_execution(self):
        self.write_json(self.actions_path, [action("duplicate"), action("duplicate")])
        self.write_json(self.expected_path, {"duplicate": expected_ok({"answer": 7})})
        self.assert_fatal()

    def test_expected_id_set_mismatch_is_fatal_before_item_execution(self):
        self.write_json(self.actions_path, [action("actual")])
        self.write_json(self.expected_path, {"different": expected_ok({"answer": 7})})
        self.assert_fatal()

    def test_malformed_control_json_saves_failed_run_summary(self):
        paths_and_valid_values = [
            (self.map_path, {"fixture": "fixture.json"}),
            (self.actions_path, [action()]),
            (self.expected_path, {"synthetic-1": expected_ok({"answer": 7})}),
        ]
        for index, (bad_path, _) in enumerate(paths_and_valid_values):
            with self.subTest(file=bad_path.name):
                for path, value in paths_and_valid_values:
                    self.write_json(path, value)
                bad_path.write_text("{invalid-json", encoding="utf-8")
                self.assert_fatal(self.root / "failed-{}".format(index))

    def test_existing_output_root_is_never_overwritten(self):
        self.out_path.mkdir()
        sentinel = self.out_path / "run_summary.json"
        original = b"original output must survive\n"
        sentinel.write_bytes(original)
        self.write_json(self.actions_path, [action()])
        self.write_json(self.expected_path, {"synthetic-1": expected_ok({"answer": 7})})
        with self.assertRaises(action_loop.HarnessError):
            action_loop.run_batch(str(self.map_path), str(self.actions_path), str(self.expected_path), str(self.out_path))
        self.assertEqual(sentinel.read_bytes(), original)
        self.assertEqual(sorted(path.name for path in self.out_path.iterdir()), ["run_summary.json"])

    def test_unicode_canonical_character_budget_flags_without_truncation(self):
        items = []
        for item_id, target_chars in [("at-limit", 6000), ("over-limit", 6001)]:
            item = action(item_id, rationale="")
            item["rationale"] = "測" * (target_chars - len(canonical_text(item)))
            self.assertEqual(len(canonical_text(item)), target_chars)
            items.append(item)
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        self.assertEqual(len(summary["items"]), 2)
        self.assertEqual(len(list(self.out_path.glob("item-*"))), 2)
        for index, target_chars in enumerate((6000, 6001)):
            with self.subTest(canonical_characters=target_chars):
                execution = self.read_json(self.item_files(summary, index) / "execution.json")
                self.assertEqual(execution["canonical_characters"], target_chars)
                self.assertEqual(execution["budget_limit"], 6000)
                self.assertEqual(execution["budget_exceeded"], target_chars > 6000)
                self.assertEqual(summary["items"][index]["budget_exceeded"], target_chars > 6000)
                self.assertEqual(execution["action_sha256"], hashlib.sha256(canonical_text(items[index]).encode("utf-8")).hexdigest())
                self.assertEqual(self.verdict(summary, index), "accepted")
                self.assertEqual(self.read_json(self.item_files(summary, index) / "artifact.json"), expected_ok({"answer": 7}))

    def test_item_directories_use_safe_indices_instead_of_action_ids(self):
        items = [action("../outside"), action("nested/name")]
        summary = self.run_actions(items, {item["id"]: expected_ok({"answer": 7}) for item in items})
        for index in range(len(items)):
            self.assertEqual(self.item_files(summary, index).parent.resolve(), self.out_path.resolve())
        self.assertFalse((self.root / "outside").exists())
        self.assertFalse((self.out_path / "nested").exists())


if __name__ == "__main__":
    unittest.main()
