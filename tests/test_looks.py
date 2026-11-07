from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from monitor_tool.cli import main
from monitor_tool.demo import DemoBackend
from monitor_tool.looks import STRENGTHS, oled_ramp, ramps_match, validate_ramp
from monitor_tool.models import MonitorError, Value
from monitor_tool.service import Service, load_profile


class LookTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.backend = DemoBackend()
        self.service = Service(self.backend, self.folder)

    def test_curves_preserve_extremes_near_black_white_and_monotonicity(self):
        for panel in ("ips", "va"):
            for strength in STRENGTHS:
                with self.subTest(panel=panel, strength=strength):
                    ramp = oled_ramp(panel, strength)
                    validate_ramp(ramp)
                    self.assertEqual(ramp[0], ramp[1])
                    self.assertEqual(ramp[1], ramp[2])
                    for index in list(range(9)) + list(range(240, 256)):
                        self.assertEqual(ramp[0][index], index * 257)
                    self.assertLess(ramp[0][128], 128 * 257)

    def test_strengths_are_ordered_and_va_curve_is_gentler(self):
        subtle, balanced, cinema = [oled_ramp("ips", n)[0][128] for n in STRENGTHS]
        self.assertGreater(subtle, balanced)
        self.assertGreater(balanced, cinema)
        self.assertGreater(oled_ramp("va", "balanced")[0][128], balanced)

    def test_oled_restore_roundtrip_includes_original_curve_and_other_screen_untouched(self):
        before = dict(self.backend.values["demo-ips"])
        original_tone = self.backend.read_tone(self.backend.monitors[0])
        other_tone = self.backend.read_tone(self.backend.monitors[1])
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.assertEqual(plan.changes[0].after, 22)
        result = self.service.execute(plan)
        self.assertTrue(result["ok"])
        self.assertIn("tone_curve", result["applied"])
        saved = load_profile(result["backup"])
        self.assertEqual(saved["schema"], 3)
        self.assertEqual(saved["tone_curve"], original_tone)
        self.assertEqual(other_tone, self.backend.read_tone(self.backend.monitors[1]))
        self.assertEqual(before["contrast"], self.backend.values["demo-ips"]["contrast"])
        self.assertEqual(before["red"], self.backend.values["demo-ips"]["red"])
        again = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.assertFalse(again.has_changes)
        restore = self.service.plan_restore("demo-ips", result["backup"])
        self.assertTrue(restore.tone)
        self.assertTrue(self.service.execute(restore)["ok"])
        self.assertEqual(before, self.backend.values["demo-ips"])
        self.assertEqual(original_tone, self.backend.read_tone(self.backend.monitors[0]))

    def test_already_low_brightness_is_not_raised_and_tone_only_plan_works(self):
        self.backend.values["demo-va"]["brightness"] = Value(5, 200)
        plan = self.service.plan_oled("demo-va", "va", tone_curve=True)
        self.assertFalse(plan.changes)
        self.assertTrue(plan.has_changes)
        result = self.service.execute(plan)
        self.assertTrue(result["ok"])
        self.assertEqual(result["applied"], ["tone_curve"])
        self.assertEqual(self.backend.values["demo-va"]["brightness"].current, 5)

    def test_hdr_blocks_before_any_write_but_ddc_only_remains_available(self):
        self.backend.hdr = True
        with self.assertRaisesRegex(MonitorError, "HDR"):
            self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.assertFalse(list(self.folder.iterdir()))
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=False)
        self.assertFalse(plan.tone)
        self.assertTrue(self.service.execute(plan)["ok"])

    def test_tone_only_monitor_still_has_a_restorable_backup(self):
        self.backend.values["demo-ips"] = {}
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.assertIn("brightness", plan.skipped)
        result = self.service.execute(plan)
        self.assertTrue(result["ok"])
        saved = load_profile(result["backup"])
        self.assertFalse(saved["values"])
        self.assertTrue(saved["tone_curve"])
        restore = self.service.plan_restore("demo-ips", result["backup"])
        self.assertTrue(self.service.execute(restore)["ok"])

    def test_hdr_enabled_after_preview_blocks_even_ddc_changes(self):
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.backend.hdr = True
        with self.assertRaises(MonitorError):
            self.service.execute(plan)
        self.assertEqual(self.backend.values["demo-ips"]["brightness"].current, 35)
        self.assertFalse(list(self.folder.iterdir()))

    def test_tone_preview_is_invalidated_by_external_changes(self):
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        self.backend.tones["demo-ips"] = oled_ramp("ips", "cinema")
        with self.assertRaisesRegex(MonitorError, "mudou"):
            self.service.execute(plan)
        self.assertFalse(list(self.folder.iterdir()))

    def test_silent_gpu_refusal_is_not_success(self):
        self.backend.write_tone = lambda *_: None
        result = self.service.execute(self.service.plan_oled("demo-ips", "ips", tone_curve=True))
        self.assertFalse(result["ok"])
        self.assertIn("tone_curve", result["failed"])
        self.assertTrue(Path(result["backup"]).is_file())

    def test_no_curve_write_when_backup_fails(self):
        plan = self.service.plan_oled("demo-ips", "ips", tone_curve=True)
        with patch("monitor_tool.service.save_json", side_effect=MonitorError("disco")), \
                patch.object(self.backend, "write_tone") as write:
            with self.assertRaises(MonitorError):
                self.service.execute(plan)
            write.assert_not_called()

    def test_bad_schema2_curve_rejected_and_schema1_restore_explains_scope(self):
        path = self.service.backup("demo-ips")
        data = load_profile(path)
        data["tone_curve"][0][100] = -1
        bad = self.folder / "bad.json"
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(MonitorError):
            load_profile(bad)
        data.pop("tone_curve")
        data.pop("color_preset", None)
        data["schema"] = 1
        old = self.folder / "old.json"
        old.write_text(json.dumps(data), encoding="utf-8")
        plan = self.service.plan_restore("demo-ips", old)
        self.assertFalse(plan.tone)
        self.assertTrue(any("somente DDC/CI" in note for note in plan.notes))

    def test_driver_quantization_tolerance(self):
        expected = oled_ramp("ips", "balanced")
        actual = [[(v // 256) * 256 for v in channel] for channel in expected]
        self.assertTrue(ramps_match(actual, expected))
        self.assertFalse(ramps_match(actual, expected, tolerance=0))

    def test_cli_oled_dryrun_does_not_write_and_yes_applies(self):
        args = ["--demo", "--backup-dir", str(self.folder), "oled", "--monitor", "demo-ips",
                "--panel", "ips", "--tone-curve"]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(args + ["--dry-run"]), 0)
            self.assertFalse(list(self.folder.iterdir()))
            self.assertEqual(main(args + ["--yes"]), 0)
        self.assertEqual(len(list(self.folder.glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
