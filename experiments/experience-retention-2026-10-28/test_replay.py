"""Synthetic replay bundles only; no study or delayed task/gold content reads."""

import contextlib
import copy
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import experience_io
import replay


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".replay-engineering-", dir=Path(__file__).parent.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        originals = self.bundle / "input/originals"
        originals.mkdir(parents=True)
        for name in (*replay.PINNED_CODE, "replay.py"):
            shutil.copyfile(Path(__file__).parent / name, self.bundle / name)
        for alias in experience_io.ALIASES:
            self.write("input/originals/" + alias + ".json", {"sample": {"id": "雪", "n": 7}, "other": 999})
        environment = self.bundle / "input/environment"
        experience_io.build_environment(originals, environment)
        action_one = self.action("T01", "X01", ["sample", "n"])
        action_two = self.action("P01", "A01", ["payload", "sample", "missing"])
        self.write("actions/array.json", [action_one])
        self.write("actions/object.json", action_two)
        self.write("policies/array.json", [{"id": "T01", "decision": "submit", "action": action_one}])
        self.write("policies/object.json", {"id": "P01", "decision": "inspect", "rationale": "Synthetic choice."})
        artifact = {"status": "ok", "values": {"answer": 7}}
        self.write("input/gold.json", {"T01": artifact, "P01": artifact})
        inspection_path = self.bundle / "inspections/requested.json"
        inspection_path.parent.mkdir()
        experience_io.inspect_source(environment / "source_map_probes.json", "A01", inspection_path)
        self.expected_artifact_hash = replay.sha256((replay.canonical_json(artifact) + "\n").encode("utf-8"))
        self.plan = {"schema_version": 1, "entries": [
            {"key": "training-T01", "task_id": "T01", "source": "X01", "map": "original", "action_file": "actions/array.json",
             "action_selector": 0, "policy_file": "policies/array.json", "policy_selector": 0, "expected_file": "input/gold.json",
             "expected_result": {"id": "T01", "execution_status": "ok", "validation_status": "accepted", "artifact_sha256": self.expected_artifact_hash, "error": None}, "inspection_file": None},
            {"key": "probe-P01", "task_id": "P01", "source": "A01", "map": "probes", "action_file": "actions/object.json",
             "action_selector": None, "policy_file": "policies/object.json", "policy_selector": None, "expected_file": "input/gold.json",
             "expected_result": {"id": "P01", "execution_status": "execution_error", "validation_status": "rejected", "artifact_sha256": None,
                                 "error": {"type": "ActionError", "message": "object path key is missing"}}, "inspection_file": "inspections/requested.json"}
        ]}
        self.write("replay_plan.json", self.plan)
        self.refresh_manifest()

    @staticmethod
    def action(task_id, source, path):
        return {"id": task_id, "prediction": "uncertain", "rationale": "Synthetic fixture.", "status": "write",
                "fields": {"answer": {"op": "get", "source": source, "path": path}}}

    def write(self, name, value):
        path = self.bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(replay.canonical_json(value) + "\n", encoding="utf-8")

    def refresh_manifest(self):
        files = {}
        for path in self.bundle.rglob("*"):
            if path.is_file() and path.name != replay.MANIFEST_NAME:
                raw = path.read_bytes()
                files[path.relative_to(self.bundle).as_posix()] = {"sha256": replay.sha256(raw), "bytes": len(raw)}
        self.write(replay.MANIFEST_NAME, {"schema_version": 1, "files": files})

    def reject_before_import(self, pattern):
        with patch.object(replay, "load_modules") as loader:
            with self.assertRaisesRegex(replay.ReplayError, pattern):
                replay.replay(self.bundle, self.root / "unused", {})
            loader.assert_not_called()

    def run_replay(self, name):
        output = self.root / name
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = replay.main(["--bundle", str(self.bundle), "--out", str(output)])
        report = replay.read_json(output / "replay_verification.json")
        self.assertEqual(stdout.getvalue().strip(), replay.canonical_json(report))
        return status, report, output

    def test_arrays_objects_zero_repairs_one_alias_and_actual_inspection_costs(self):
        status, report, output = self.run_replay("success")
        self.assertEqual(status, 0)
        self.assertEqual(report["items_compared"], 2)
        self.assertEqual(report["items_matching"], 2)
        self.assertEqual(report["generated_artifact_sha256_match_count"], 1)
        self.assertEqual(report["expected_errors_preserved"], 1)
        self.assertEqual(report["inspections_matching"], 1)
        self.assertIs(report["fresh_ai_choices_generated"], False)
        saved = replay.read_json(self.bundle / "inspections/requested.json")
        self.assertEqual(report["actual_inspection_raw_bytes"], saved["raw_bytes_read"])
        self.assertEqual(report["actual_inspection_returned_characters"], saved["returned_canonical_characters"])
        self.assertEqual((output / "inspections/probe-P01.json").read_bytes(), (self.bundle / "inspections/requested.json").read_bytes())
        for entry in self.plan["entries"]:
            assigned = replay.read_json(output / "assigned_inputs" / (entry["key"] + "-map.json"))
            self.assertEqual(set(assigned), {entry["source"]})
        self.assertFalse(any("repair" in p.name for p in output.rglob("*")))

    def test_missing_extra_sha_size_and_pinned_code_fail_before_import(self):
        path = self.bundle / "input/gold.json"
        raw = path.read_bytes()
        path.unlink()
        self.reject_before_import("file set differs")
        path.write_bytes(raw)
        self.write("extra.json", {"x": 1})
        self.reject_before_import("file set differs")
        (self.bundle / "extra.json").unlink()
        path.write_bytes(raw.replace(b'7', b'8', 1))
        self.reject_before_import("SHA256/size")
        path.write_bytes(raw)
        manifest = replay.read_json(self.bundle / replay.MANIFEST_NAME)
        manifest["files"]["input/gold.json"]["bytes"] += 1
        self.write(replay.MANIFEST_NAME, manifest)
        self.reject_before_import("SHA256/size")
        engine = self.bundle / "action_loop.py"
        engine.write_bytes(engine.read_bytes() + b"\n")
        self.refresh_manifest()
        self.reject_before_import("pinned code differs")

    def test_symlinks_unsafe_paths_and_manifest_duplicates_fail_before_import(self):
        link = self.bundle / "link"
        link.symlink_to(self.root, target_is_directory=True)
        self.reject_before_import("symlinks")
        link.unlink()
        manifest = replay.read_json(self.bundle / replay.MANIFEST_NAME)
        for name in (".", "../escape", "/absolute", "a//b", "a/./b", "C:/drive", "bad\\path", replay.MANIFEST_NAME):
            with self.subTest(name=name):
                changed = copy.deepcopy(manifest)
                changed["files"][name] = {"bytes": 0, "sha256": "0" * 64}
                self.write(replay.MANIFEST_NAME, changed)
                self.reject_before_import("invalid manifest|except itself")
        (self.bundle / replay.MANIFEST_NAME).write_bytes(b'{"schema_version":1,"schema_version":1,"files":{}}')
        self.reject_before_import("duplicate JSON")

    def test_plan_selectors_ids_inspection_choice_and_source_binding_are_strict(self):
        mutations = [lambda p: p["entries"][0].update(action_selector=True),
                     lambda p: p["entries"][1].update(policy_selector=0),
                     lambda p: p["entries"][0].update(task_id="different"),
                     lambda p: p["entries"][1].update(inspection_file=None),
                     lambda p: p["entries"][0].update(inspection_file="inspections/requested.json"),
                     lambda p: p["entries"][1].update(source="A02"),
                     lambda p: p["entries"][1].update(key=p["entries"][0]["key"]),
                     lambda p: p["entries"][0].update(action_file="../outside.json")]
        for mutate in mutations:
            changed = copy.deepcopy(self.plan)
            mutate(changed)
            self.write("replay_plan.json", changed)
            self.refresh_manifest()
            self.reject_before_import("selector|id must match|inspection|duplicate|manifest-listed")
        self.write("replay_plan.json", self.plan)
        policy = replay.read_json(self.bundle / "policies/array.json")
        policy[0]["action"]["rationale"] = "different locked action"
        self.write("policies/array.json", policy)
        self.refresh_manifest()
        self.reject_before_import("lock the saved action")

    def test_exact_error_artifact_and_inspection_cost_mismatches_return_nonzero(self):
        for field in ("error", "artifact", "inspection"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.plan)
                if field == "error": changed["entries"][1]["expected_result"]["error"]["message"] = "different"
                if field == "artifact": changed["entries"][0]["expected_result"]["artifact_sha256"] = "0" * 64
                original_inspection = (self.bundle / "inspections/requested.json").read_bytes()
                if field == "inspection":
                    saved = replay.read_json(self.bundle / "inspections/requested.json")
                    saved["returned_canonical_characters"] += 1
                    self.write("inspections/requested.json", saved)
                self.write("replay_plan.json", changed)
                self.refresh_manifest()
                status, report, _ = self.run_replay("mismatch-" + field)
                self.assertEqual(status, 1)
                self.assertEqual(report["status"], "failed")
                if field == "inspection":
                    self.assertEqual(report["inspections_matching"], 0)
                    self.assertEqual(report["items_matching"], 2)
                else: self.assertEqual(report["items_matching"], 1)
                (self.bundle / "inspections/requested.json").write_bytes(original_inspection)

    def test_existing_output_never_overwrites_and_source_escape_is_rejected(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "sentinel"
        sentinel.write_bytes(b"keep")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(replay.main(["--bundle", str(self.bundle), "--out", str(output)]), 1)
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertEqual(set(output.iterdir()), {sentinel})
        self.write("input/environment/source_map_original.json", {"X01": "../../../outside.json"})
        (self.root / "outside.json").write_text('{}\n')
        self.refresh_manifest()
        self.reject_before_import("escapes bundle")


if __name__ == "__main__":
    unittest.main()
