"""Synthetic bundle checks; no study sources, actions, or outcomes are read."""

import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import migration
import replay


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".replay-engineering-", dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        originals = self.bundle / "input/originals"
        originals.mkdir(parents=True)
        for name in (*replay.FROZEN_CODE_SHA256, "replay.py"):
            shutil.copyfile(Path(__file__).parent / name, self.bundle / name)
        for index, alias in enumerate(replay.ALIASES, 1):
            self.write("input/originals/" + alias + ".json", {
                "id": "synthetic-" + alias, "value": index * 4,
                "per_query": {"id": "synthetic-hidden", "value": 999},
            })
        migration.build_environment(originals, self.bundle / "input/environment")
        self.write("protocol.json", {"scope": "synthetic engineering fixture"})
        self.write("memory/conditional_review.json", {"scope": "synthetic fixture"})
        self.saved_ids = ("P01", "P03", "P05")
        saved = [self.action(item_id, alias, ["value"]) for item_id, alias in zip(self.saved_ids, replay.ALIASES)]
        repair = [self.action(item_id, alias, ["payload", "value"]) for item_id, alias in zip(self.saved_ids, replay.ALIASES)]
        self.write("input/saved_actions.json", saved)
        self.write("actions/repair.json", repair)
        self.write("input/saved_gold.json", {item_id: self.artifact(index * 4) for index, item_id in enumerate(self.saved_ids, 1)})
        later = [self.action("T%02d" % index, "S%02d" % index, ["value"] if index % 2 else ["payload", "value"])
                 for index in range(1, 7)]
        self.write("input/later_tasks.json", [{"id": action["id"]} for action in later])
        self.write("input/later_gold.json", {action["id"]: self.artifact(((index + 1) // 2) * 4) for index, action in enumerate(later, 1)})
        self.write("actions/raw_observations.json", later)
        self.write("actions/raw_observations_and_conditional_review.json", later)
        for condition, _, _, _, count in replay.CONDITIONS:
            outcomes = []
            for index in range(count):
                item_id = self.saved_ids[index] if count == 3 else "T%02d" % (index + 1)
                if condition == "wrapped":
                    outcomes.append({"id": item_id, "execution_status": "execution_error", "validation_status": "rejected",
                                     "artifact_sha256": None, "error": {"type": "ActionError", "message": "object path key is missing"}})
                else:
                    value = (index + 1) * 4 if count == 3 else ((index + 2) // 2) * 4
                    artifact_name = "expected_artifacts/" + condition + "/" + item_id + ".json"
                    self.write(artifact_name, self.artifact(value))
                    outcomes.append({"id": item_id, "execution_status": "ok", "validation_status": "accepted",
                                     "artifact_sha256": replay.sha256((self.bundle / artifact_name).read_bytes()), "error": None})
            self.write("expected_runs/" + condition + ".json", outcomes)
        self.refresh_manifest()

    @staticmethod
    def action(item_id, alias, path):
        return {"id": item_id, "prediction": "uncertain", "rationale": "Synthetic engineering fixture.",
                "status": "write", "fields": {"answer": {"op": "get", "source": alias, "path": path}}}

    @staticmethod
    def artifact(value):
        return {"status": "ok", "values": {"answer": value}}

    def write(self, name, value):
        path = self.bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(replay.canonical_json(value) + "\n", encoding="utf-8")

    def refresh_manifest(self):
        files = {}
        for path in self.bundle.rglob("*"):
            if path.is_file() and path.name != "manifest.json":
                raw = path.read_bytes()
                files[path.relative_to(self.bundle).as_posix()] = {"sha256": replay.sha256(raw), "bytes": len(raw)}
        self.write("manifest.json", {"schema_version": 1, "files": files})

    def assert_preimport_rejection(self, message):
        with patch.object(replay, "load_engine") as loader:
            with self.assertRaisesRegex(replay.ReplayError, message):
                replay.replay(self.bundle, self.root / "unused-output", {})
            loader.assert_not_called()

    def run_cli(self, name):
        output = self.root / name
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = replay.main(["--bundle", str(self.bundle), "--out", str(output)])
        report = replay.read_json(output / "replay_verification.json")
        self.assertEqual(replay.canonical_json(report), stdout.getvalue().strip())
        return code, report

    def test_missing_manifest_file_is_rejected_before_import(self):
        (self.bundle / "protocol.json").unlink()
        self.assert_preimport_rejection("bundle files differ.*missing")

    def test_extra_nested_file_is_rejected_before_import(self):
        self.write("unexpected/nested.json", {"extra": True})
        self.assert_preimport_rejection("bundle files differ.*extra")

    def test_sha_size_and_frozen_code_tampering_are_rejected_before_import(self):
        protocol = self.bundle / "protocol.json"
        original = protocol.read_bytes()
        protocol.write_bytes(original.replace(b"synthetic", b"Synthetic", 1))
        self.assertEqual(len(protocol.read_bytes()), len(original))
        self.assert_preimport_rejection("SHA256/size mismatch")
        protocol.write_bytes(original)
        manifest = replay.read_json(self.bundle / "manifest.json")
        manifest["files"]["protocol.json"]["bytes"] += 1
        self.write("manifest.json", manifest)
        self.assert_preimport_rejection("SHA256/size mismatch")
        self.refresh_manifest()
        copied_code = self.bundle / "action_loop.py"
        copied_code.write_bytes(copied_code.read_bytes() + b"\n")
        self.refresh_manifest()
        self.assert_preimport_rejection("copied frozen code differs")

    def test_symlinks_unsafe_manifest_paths_and_existing_output_are_rejected(self):
        protocol = self.bundle / "protocol.json"
        saved = protocol.read_bytes()
        outside = self.root / "outside.json"
        outside.write_bytes(saved)
        protocol.unlink()
        protocol.symlink_to(outside)
        self.assert_preimport_rejection("symlinks")
        protocol.unlink()
        protocol.write_bytes(saved)
        link = self.bundle / "unlisted-link"
        link.symlink_to(self.root, target_is_directory=True)
        self.assert_preimport_rejection("symlinks")
        link.unlink()
        manifest = replay.read_json(self.bundle / "manifest.json")
        for unsafe in (".", "../escape", "/absolute", "a/./b", "a//b", "C:/drive", "bad\\path", "manifest.json"):
            with self.subTest(unsafe=unsafe):
                changed = {"schema_version": 1, "files": dict(manifest["files"])}
                changed["files"][unsafe] = {"sha256": "0" * 64, "bytes": 0}
                self.write("manifest.json", changed)
                self.assert_preimport_rejection("invalid manifest|excluding itself")
        self.write("manifest.json", manifest)
        output = self.root / "existing-output"
        output.mkdir()
        sentinel = output / "sentinel"
        sentinel.write_bytes(b"unchanged")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(replay.main(["--bundle", str(self.bundle), "--out", str(output)]), 1)
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        self.assertEqual(set(output.iterdir()), {sentinel})

    def test_saved_choices_replay_and_exact_error_mismatches_fail(self):
        code, report = self.run_cli("matching")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["choices_source"], "saved_bundle_actions")
        self.assertIs(report["fresh_ai_choices_generated"], False)
        self.assertEqual(report["items_compared"], 21)
        self.assertEqual(report["items_matching"], 21)
        self.assertEqual(report["generated_artifact_sha256_match_count"], 18)
        self.assertEqual(report["expected_errors_preserved"], 3)
        self.assertEqual(report["expected_errors"], 3)
        self.assertFalse(any((self.root / "matching/wrapped").glob("item-*/artifact.json")))
        original = replay.read_json(self.bundle / "expected_runs/wrapped.json")
        for field in ("type", "message"):
            with self.subTest(field=field):
                modified = replay.read_json(self.bundle / "expected_runs/wrapped.json")
                modified[0]["error"][field] = "deliberately different"
                self.write("expected_runs/wrapped.json", modified)
                self.refresh_manifest()
                code, report = self.run_cli("mismatch-" + field)
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["items_compared"], 21)
                self.assertEqual(report["items_matching"], 20)
                self.assertEqual(report["expected_errors_preserved"], 2)
                self.assertEqual(report["generated_artifact_sha256_match_count"], 18)
                self.write("expected_runs/wrapped.json", original)


if __name__ == "__main__":
    unittest.main()
