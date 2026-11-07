from contextlib import redirect_stdout, redirect_stderr
import ctypes as C
import io
from pathlib import Path
import tempfile
import unittest

from monitor_tool.bridge import Bridge
from monitor_tool.cli import main
from monitor_tool.demo import DemoBackend
from monitor_tool.diagnostics import ColorData
from monitor_tool.models import MonitorError
from monitor_tool.service import Service, load_profile
from monitor_tool.visual import manual_ramp


class VisualTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.backend = DemoBackend()
        self.service = Service(self.backend, self.folder)

    def test_manual_curve_is_monotonic_bounded_and_absolute(self):
        for gamma in (.85, 1., 1.15):
            for black in (0., .5, 4.):
                with self.subTest(gamma=gamma, black=black):
                    ramp = manual_ramp(gamma, black)
                    self.assertEqual(ramp[0][0], 0)
                    self.assertEqual(ramp[0][-1], 65535)
                    self.assertTrue(all(a <= b for a,b in zip(ramp[0],ramp[0][1:])))
                    self.assertEqual(ramp[0], ramp[1])
        self.assertEqual(manual_ramp()[0], [i * 257 for i in range(256)])
        self.assertEqual(manual_ramp(1., 4.)[0][4], 0)
        self.assertGreater(manual_ramp(1., 4.)[0][5], 0)

    def test_invalid_params_never_touch_hardware(self):
        for tone in ({"gamma": True}, {"gamma": float('nan')}, {"black_point": -1},
                     {"gamma": 2}, {"black_point": 5}, {"unknown": 1}, []):
            with self.subTest(tone=tone), self.assertRaises(MonitorError):
                self.service.plan_visual("demo-va", {"brightness": 30}, tone)
        self.assertFalse(list(self.folder.iterdir()))

    def test_visual_undo_restores_ddc_and_curve_only_on_destination(self):
        bridge = Bridge(self.service)
        before = self.backend.read_tone(self.backend.monitors[1])
        preview = bridge.dispatch("preview_visual", {"target": "demo-va", "values": {"brightness": 40},
                                                      "tone": {"gamma": 1.06, "black_point": .5}})
        applied = bridge.dispatch("apply", {"token": preview["token"]})
        self.assertTrue(applied["ok"])
        self.assertEqual(load_profile(applied["backup"])["tone_curve"], before)
        self.assertEqual(self.backend.values["demo-ips"]["brightness"].current, 35)
        self.assertNotEqual(self.backend.tones["demo-va"], before)
        self.assertTrue(bridge.state()["monitors"][1]["can_undo"])
        undo = bridge.dispatch("preview_undo", {"target": "demo-va"})
        self.assertTrue(bridge.dispatch("apply", {"token": undo["token"]})["ok"])
        self.assertEqual(self.backend.values["demo-va"]["brightness"].current, 140)
        self.assertEqual(self.backend.tones["demo-va"], before)

    def test_curve_requires_sdr_and_stale_preview_is_rejected(self):
        self.backend.hdr = True
        with self.assertRaises(MonitorError):
            self.service.plan_visual("demo-va", {}, {"gamma": 1.06})
        self.backend.hdr = False
        plan = self.service.plan_visual("demo-va", {}, {"gamma": 1.06})
        self.backend.tones["demo-va"] = manual_ramp(.9, 0)
        with self.assertRaisesRegex(MonitorError, "mudou"):
            self.service.execute(plan)

    def test_repeated_manual_curve_does_not_compound(self):
        self.assertTrue(self.service.execute(self.service.plan_visual("demo-va", {}, {"gamma": 1.06}))["ok"])
        self.assertFalse(self.service.plan_visual("demo-va", {}, {"gamma": 1.06}).has_changes)

    def test_undo_without_session_backup_is_rejected(self):
        with self.assertRaises(MonitorError):
            Bridge(self.service).dispatch("preview_undo", {"target": "demo-va"})

    def test_diagnostic_does_not_write_and_does_not_claim_physical_measurement(self):
        result = Bridge(self.service).dispatch("diagnostics", {"target": "demo-va"})
        self.assertTrue(result["output"]["read_only"])
        self.assertEqual(result["output"]["range"], "full")
        self.assertIn("Não mensurado", result["physical_black"])
        self.assertFalse(list(self.folder.iterdir()))
        self.assertEqual(C.sizeof(ColorData), 24)

    def test_cli_tune_dryrun_and_apply(self):
        args = ["--demo", "--backup-dir", str(self.folder), "tune", "--monitor", "demo-va",
                "--brightness", "40", "--gamma", "1.06", "--black-point", ".5"]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(args + ["--dry-run"]), 0)
            self.assertFalse(list(self.folder.iterdir()))
            self.assertEqual(main(args + ["--yes"]), 0)


if __name__ == "__main__":
    unittest.main()
