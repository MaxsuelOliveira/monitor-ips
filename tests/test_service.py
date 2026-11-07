import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from monitor_tool.cli import main
from monitor_tool.demo import DemoBackend
from monitor_tool.models import MonitorError, Value
from monitor_tool.service import Change, Plan, Service, load_profile


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.backend = DemoBackend()
        self.service = Service(self.backend, self.folder)

    def test_proportional_copy_skips_unavailable_and_restore_roundtrip(self):
        original = dict(self.backend.values["demo-va"])
        plan = self.service.compare("demo-ips", "demo-va")
        self.assertEqual(next(c.after for c in plan.changes if c.feature == "brightness"), 70)
        self.assertIn("blue", plan.skipped)
        result = self.service.execute(plan)
        self.assertTrue(result["ok"])
        saved = load_profile(result["backup"])
        self.assertEqual(saved["values"]["brightness"]["current"], 140)
        restore = self.service.plan_restore("demo-va", result["backup"])
        restored = self.service.execute(restore)
        self.assertTrue(restored["ok"])
        self.assertNotEqual(result["backup"], restored["backup"])
        self.assertEqual(original, self.backend.values["demo-va"])

    def test_stale_preview_never_writes(self):
        plan = self.service.compare("demo-ips", "demo-va")
        self.backend.values["demo-va"]["brightness"] = Value(145, 200)
        with self.assertRaisesRegex(MonitorError, "mudaram"):
            self.service.execute(plan)
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertEqual(self.backend.values["demo-va"]["contrast"].current, 60)

    def test_backup_failure_prevents_all_writes(self):
        plan = self.service.compare("demo-ips", "demo-va")
        with patch("monitor_tool.service.save_json", side_effect=MonitorError("disco cheio")):
            with self.assertRaisesRegex(MonitorError, "disco cheio"):
                self.service.execute(plan)
        self.assertEqual(self.backend.values["demo-va"]["brightness"].current, 140)

    def test_partial_failure_stops_and_keeps_original_backup(self):
        actual_write = self.backend.write

        def write(monitor, feature, value):
            if feature == "contrast":
                raise MonitorError("não gravável")
            actual_write(monitor, feature, value)

        self.backend.write = write
        result = self.service.execute(self.service.compare("demo-ips", "demo-va"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["applied"], ["brightness"])
        self.assertIn("contrast", result["failed"])
        self.assertIn("red", result["not_attempted"])
        self.assertEqual(load_profile(result["backup"])["values"]["brightness"]["current"], 140)

    def test_readback_mismatch_is_reported(self):
        self.backend.write = lambda *_: None
        result = self.service.execute(self.service.plan_set("demo-va", {"brightness": 20}))
        self.assertFalse(result["ok"])
        self.assertIn("brightness", result["failed"])

    def test_later_write_cannot_silently_undo_previous_control(self):
        write = self.backend.write

        def with_side_effect(monitor, feature, value):
            write(monitor, feature, value)
            if feature == "contrast":
                self.backend.values[monitor.id]["brightness"] = Value(140, 200)

        self.backend.write = with_side_effect
        plan = self.service.plan_set("demo-va", {"brightness": 70, "contrast": 80})
        result = self.service.execute(plan)
        self.assertFalse(result["ok"])
        self.assertIn("brightness", result["failed"])
        self.assertNotIn("brightness", result["applied"])

    def test_wrong_monitor_mode_or_range_rejected(self):
        path = self.service.backup("demo-va")
        with self.assertRaisesRegex(MonitorError, "outro monitor"):
            self.service.plan_restore("demo-ips", path)
        self.backend.values["demo-va"]["brightness"] = Value(20, 100)
        with self.assertRaisesRegex(MonitorError, "Intervalo"):
            self.service.plan_restore("demo-va", path)
        data = load_profile(path)
        data["demo"] = False
        altered = self.folder / "real.json"
        altered.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MonitorError, "misturados"):
            self.service.plan_restore("demo-va", altered)

    def test_invalid_profile_controls_types_and_ranges_rejected(self):
        path = self.service.backup("demo-va")
        data = load_profile(path)
        cases = [dict(data, values={"reset": {"current": 1, "maximum": 100}}),
                 dict(data, values={"brightness": {"current": True, "maximum": 100}}),
                 dict(data, values={"brightness": {"current": -1, "maximum": 100}}),
                 dict(data, values={"brightness": {"current": 200, "maximum": 100}}),
                 dict(data, values={"brightness": {"current": 0, "maximum": 0}}),
                 dict(data, values={"brightness": []}), [], dict(data, values={}, schema=1)]
        for index, invalid in enumerate(cases):
            with self.subTest(invalid=invalid):
                altered = self.folder / f"invalid-{index}.json"
                altered.write_text(json.dumps(invalid), encoding="utf-8")
                with self.assertRaises(MonitorError):
                    load_profile(altered)

    def test_no_overwrite_of_backup(self):
        path = self.folder / "backup.json"
        self.service.backup("demo-va", path)
        old = path.read_bytes()
        with self.assertRaises(MonitorError):
            self.service.backup("demo-ips", path)
        self.assertEqual(old, path.read_bytes())
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_manual_ranges_same_monitor_and_ambiguous_target(self):
        for value in (-1, 201, True):
            with self.subTest(value=value), self.assertRaises(MonitorError):
                self.service.plan_set("demo-va", {"brightness": value})
        with self.assertRaises(MonitorError):
            self.service.compare("demo-va", "demo-va")
        self.backend.monitors[1].writable_identity = False
        with self.assertRaisesRegex(MonitorError, "ambígua"):
            self.service.plan_set("demo-va", {"brightness": 20})

    def test_invalid_plan_cannot_escape_allowlist(self):
        plan = Plan(self.backend.monitors[1].public(), [Change("reset", 0, 1, 100)], {}, True)
        with self.assertRaises(MonitorError):
            self.service.execute(plan)
        self.assertFalse(list(self.folder.iterdir()))

    def test_changed_identity_and_removed_monitor_rejected(self):
        plan = self.service.plan_set("demo-va", {"brightness": 20})
        self.backend.monitors[1].identity = "other"
        with self.assertRaises(MonitorError):
            self.service.execute(plan)
        self.backend.monitors.pop()
        with self.assertRaises(MonitorError):
            self.service.execute(plan)

    def test_noop_does_not_write_backup(self):
        result = self.service.execute(self.service.plan_set("demo-va", {"brightness": 140}))
        self.assertIsNone(result["backup"])
        self.assertTrue(result["ok"])
        self.assertFalse(list(self.folder.iterdir()))

    def test_cli_json_dry_run_and_explicit_confirmation(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--demo", "list", "--json"]), 0)
        self.assertTrue(json.loads(out.getvalue())["demo"])
        args = ["--demo", "--backup-dir", str(self.folder), "set", "--monitor", "demo-va", "brightness=30"]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args + ["--dry-run"]), 0)
            with patch("sys.stdin.isatty", return_value=False):
                self.assertEqual(main(args), 1)
            self.assertFalse(list(self.folder.iterdir()))
            self.assertEqual(main(args + ["--yes"]), 0)
            self.assertEqual(main(args + ["brightness=20", "--yes"]), 1)
        self.assertEqual(len(list(self.folder.glob("*.json"))), 1)

    def test_session_is_released_after_failure(self):
        with self.assertRaises(MonitorError):
            self.service.plan_set("absent", {"brightness": 20})
        self.assertEqual(len(self.service.inspect()["monitors"]), 2)


if __name__ == "__main__":
    unittest.main()
