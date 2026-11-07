from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from monitor_tool.bridge import Bridge
from monitor_tool.cli import main
from monitor_tool.demo import DemoBackend
from monitor_tool.looks import validate_ramp
from monitor_tool.models import MonitorError, Value
from monitor_tool.presets import catalog, preset_ramp
from monitor_tool.service import Service, load_profile


class PresetTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.backend = DemoBackend()
        self.service = Service(self.backend, self.folder)

    def test_all_models_on_both_panels_backup_restore_and_preserve_other_screen(self):
        for panel, index in (("ips", 0), ("va", 1)):
            target = self.backend.monitors[index]
            for preset in catalog():
                with self.subTest(panel=panel, preset=preset["id"]):
                    before = deepcopy(self.backend.values)
                    colors = deepcopy(self.backend.colors)
                    tones = deepcopy(self.backend.tones)
                    plan = self.service.plan_preset(target.id, preset["id"], panel)
                    self.assertTrue(plan.has_changes)
                    self.assertTrue(all(c.feature == "brightness" for c in plan.changes))
                    result = self.service.execute(plan)
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(load_profile(result["backup"])["tone_curve"], tones[target.id])
                    self.assertEqual(self.backend.colors, colors)
                    other = self.backend.monitors[1-index].id
                    self.assertEqual(self.backend.values[other], before[other])
                    self.assertEqual(self.backend.tones[other], tones[other])
                    for name, value in before[target.id].items():
                        if name != "brightness":
                            self.assertEqual(self.backend.values[target.id][name], value)
                    self.assertFalse(self.service.plan_preset(target.id, preset["id"], panel).has_changes)
                    self.assertTrue(self.service.execute(self.service.plan_restore(target.id, result["backup"]))["ok"])
                    self.assertEqual(self.backend.values, before)
                    self.assertEqual(self.backend.tones, tones)

    def test_curves_preserve_shadows_highlights_and_are_monotonic(self):
        for panel in ("ips", "va"):
            for preset in catalog():
                ramp = validate_ramp(preset_ramp(preset["id"], panel))
                self.assertEqual(ramp[0], ramp[1])
                for index in [*range(9), *range(240, 256)]:
                    self.assertEqual(ramp[0][index], index * 257)
                self.assertEqual(ramp, preset_ramp(preset["id"], panel))
        self.assertLess(preset_ramp("cinema-dark", "ips")[0][128],
                        preset_ramp("oled-balanced", "ips")[0][128])
        self.assertEqual(preset_ramp("natural", "ips")[0], [i*257 for i in range(256)])

    def test_ceiling_preserves_low_brightness_but_override_can_raise_it(self):
        self.backend.values["demo-va"]["brightness"] = Value(5, 200)
        plan = self.service.plan_preset("demo-va", "oled-balanced", "va")
        self.assertEqual(plan.changes, [])
        plan = self.service.plan_preset("demo-va", "oled-balanced", "va", brightness=25)
        self.assertEqual(plan.changes[0].after, 50)
        self.assertTrue(any("aumenta" in note for note in plan.notes))

    def test_stale_preserved_control_or_preset_is_rejected_before_backup(self):
        plan = self.service.plan_preset("demo-ips", "cinema-dark", "ips")
        self.backend.values["demo-ips"]["red"] = Value(88, 100)
        with self.assertRaisesRegex(MonitorError, "mudou"):
            self.service.execute(plan)
        self.assertFalse(list(self.folder.iterdir()))
        plan = self.service.plan_preset("demo-ips", "cinema-dark", "ips")
        self.backend.colors["demo-ips"]["current"] = 8
        with self.assertRaisesRegex(MonitorError, "mudou"):
            self.service.execute(plan)

    def test_hdr_requires_explicit_no_tone_and_does_not_silently_fallback(self):
        self.backend.hdr = True
        with self.assertRaisesRegex(MonitorError, "HDR"):
            self.service.plan_preset("demo-ips", "natural", "ips")
        self.assertFalse(list(self.folder.iterdir()))
        plan = self.service.plan_preset("demo-ips", "natural", "ips", tone_curve=False)
        self.assertIsNone(plan.tone)
        self.assertTrue(self.service.execute(plan)["ok"])

    def test_driver_quantization_does_not_force_reapplication(self):
        target = self.backend.monitors[0]
        result = self.service.execute(self.service.plan_preset(target.id, "oled-balanced", "ips"))
        self.assertTrue(result["ok"])
        for channel in self.backend.tones[target.id]:
            for i, value in enumerate(channel):
                channel[i] = value & 0xFF00
        plan = self.service.plan_preset(target.id, "oled-balanced", "ips")
        self.assertFalse(plan.has_changes)
        self.assertTrue(self.service.execute(plan)["ok"])

    def test_unavailable_brightness_is_explicit_and_requires_curve(self):
        self.backend.values["demo-ips"].pop("brightness")
        plan = self.service.plan_preset("demo-ips", "cinema-dark", "ips")
        self.assertIn("brightness", plan.skipped)
        self.assertTrue(self.service.execute(plan)["ok"])
        with self.assertRaisesRegex(MonitorError, "brilho"):
            self.service.plan_preset("demo-ips", "cinema-dark", "ips", tone_curve=False)

    def test_invalid_parameters_do_not_write(self):
        for kwargs in ({"brightness": -1}, {"brightness": 101}, {"brightness": True},
                       {"brightness": 1.5}, {"tone_curve": "yes"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(MonitorError):
                self.service.plan_preset("demo-ips", "natural", "ips", **kwargs)
        with self.assertRaises(MonitorError):
            self.service.plan_preset("demo-ips", "fake", "ips")
        self.assertFalse(list(self.folder.iterdir()))

    def test_bridge_catalog_preview_token_and_undo(self):
        bridge = Bridge(self.service)
        self.assertEqual(len(bridge.state()["presets"]), 4)
        before = deepcopy(self.backend.values)
        preview = bridge.dispatch("preview_preset", {"target": "demo-ips", "preset": "oled-balanced", "panel": "ips"})
        self.assertEqual(self.backend.values, before)
        self.assertTrue(bridge.dispatch("apply", {"token": preview["token"]})["ok"])
        with self.assertRaises(MonitorError):
            bridge.dispatch("apply", {"token": preview["token"]})
        undo = bridge.dispatch("preview_undo", {"target": "demo-ips"})
        self.assertTrue(bridge.dispatch("apply", {"token": undo["token"]})["ok"])
        self.assertEqual(self.backend.values, before)

    def test_cli_catalog_dryrun_and_apply(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(["presets", "--json"]), 0)
        self.assertEqual(len(json.loads(stream.getvalue())), 4)
        args = ["--demo", "--backup-dir", str(self.folder), "preset", "--monitor", "demo-ips",
                "--panel", "ips", "--name", "oled-balanced"]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([*args, "--dry-run", "--yes"]), 0)
            self.assertFalse(list(self.folder.iterdir()))
            self.assertEqual(main([*args, "--yes"]), 0)
        self.assertTrue(list(self.folder.glob("*.json")))
