from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from monitor_tool.bridge import Bridge
from monitor_tool.demo import DemoBackend
from monitor_tool.looks import oled_ramp
from monitor_tool.models import MonitorError, Value
from monitor_tool.service import Service


class MatchTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.backend = DemoBackend()
        self.service = Service(self.backend, self.folder)

    def test_exact_copy_and_curve_without_touching_ips(self):
        self.backend.tones["demo-ips"] = oled_ramp("ips", "balanced")
        reference = deepcopy(self.backend.values["demo-ips"])
        tone = deepcopy(self.backend.tones["demo-ips"])
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.assertEqual(next(c.after for c in plan.changes if c.feature == "brightness"), 35)
        self.assertIn("blue", plan.skipped)
        self.assertTrue(plan.tone)
        result = self.service.execute(plan)
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["backup"]).is_file())
        for key, value in reference.items():
            if key in self.backend.values["demo-va"]:
                self.assertEqual(value.current, self.backend.values["demo-va"][key].current)
        self.assertEqual(reference, self.backend.values["demo-ips"])
        self.assertEqual(tone, self.backend.tones["demo-ips"])
        self.assertEqual(tone, self.backend.tones["demo-va"])

    def test_relative_mode_remains_explicit(self):
        plan = self.service.plan_match("demo-ips", "demo-va", mode="relative", include_tone=False)
        self.assertEqual(next(c.after for c in plan.changes if c.feature == "brightness"), 70)

    def test_changed_reference_blocks_before_backup(self):
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.backend.values["demo-ips"]["contrast"] = Value(71, 100)
        with self.assertRaisesRegex(MonitorError, "IPS mudaram"):
            self.service.execute(plan)
        self.assertFalse(list(self.folder.iterdir()))

    def test_changed_reference_tone_blocks(self):
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.backend.tones["demo-ips"] = oled_ramp("ips", "balanced")
        with self.assertRaises(MonitorError):
            self.service.execute(plan)

    def test_already_equal_control_is_guarded(self):
        self.backend.values["demo-va"]["contrast"] = Value(70, 100)
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.backend.values["demo-va"]["contrast"] = Value(75, 100)
        with self.assertRaisesRegex(MonitorError, "destino mudou"):
            self.service.execute(plan)

    def test_already_equal_tone_is_guarded(self):
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.assertFalse(plan.tone)
        self.backend.tones["demo-va"] = oled_ramp("va", "balanced")
        with self.assertRaisesRegex(MonitorError, "curva do destino"):
            self.service.execute(plan)

    def test_out_of_range_is_skipped_not_silently_rescaled(self):
        self.backend.values["demo-ips"]["brightness"] = Value(180, 200)
        self.backend.values["demo-va"]["brightness"] = Value(80, 100)
        plan = self.service.plan_match("demo-ips", "demo-va", include_tone=False)
        self.assertIn("brightness", plan.skipped)
        self.assertNotIn("brightness", [c.feature for c in plan.changes])

    def test_hdr_requires_explicit_no_tone(self):
        self.backend.hdr = True
        with self.assertRaisesRegex(MonitorError, "Desmarque"):
            self.service.plan_match("demo-ips", "demo-va")
        plan = self.service.plan_match("demo-ips", "demo-va", include_tone=False)
        self.assertTrue(self.service.execute(plan)["ok"])

    def test_noop_after_match(self):
        self.assertTrue(self.service.execute(self.service.plan_match("demo-ips", "demo-va"))["ok"])
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.assertFalse(plan.has_changes)
        self.assertIsNone(self.service.execute(plan)["backup"])

    def test_auto_uses_advertised_user2_before_adjusting_locked_rgb(self):
        write = self.backend.write

        def locked(monitor, name, value):
            if name not in ("red", "green", "blue") or self.backend.colors[monitor.id]["current"] == 12:
                write(monitor, name, value)

        self.backend.write = locked
        plan = self.service.plan_match("demo-ips", "demo-va")
        self.assertEqual(plan.color["after"], 12)
        self.assertTrue(self.service.execute(plan)["ok"])
        self.assertFalse(self.service.plan_match("demo-ips", "demo-va").has_changes)
        self.assertEqual(self.backend.colors["demo-ips"]["current"], 5)

    def test_source_mode_is_explicit_and_user1_or_unsupported_modes_are_reported(self):
        plan = self.service.plan_match("demo-ips", "demo-va", color_mode="source")
        self.assertEqual(plan.color["after"], 5)
        user1 = self.service.plan_match("demo-ips", "demo-va", color_mode="user1")
        self.assertEqual(user1.color["after"], 11)
        self.backend.colors["demo-va"]["supported"] = [5, 8]
        unsupported = self.service.plan_match("demo-ips", "demo-va", color_mode="user2")
        self.assertIn("color_preset", unsupported.skipped)
        self.assertFalse(unsupported.color)

    def test_schema3_restore_restores_mode_and_values_after_preset_side_effects(self):
        original_color = self.backend.read_color(self.backend.monitors[1])
        original_values = deepcopy(self.backend.values["demo-va"])
        path = self.service.backup("demo-va")
        self.assertTrue(self.service.execute(self.service.plan_match("demo-ips", "demo-va"))["ok"])
        write_color = self.backend.write_color

        def side_effect(monitor, value):
            write_color(monitor, value)
            self.backend.values[monitor.id]["contrast"] = Value(20, 100)

        self.backend.write_color = side_effect
        restore = self.service.plan_restore("demo-va", path)
        self.assertTrue(restore.color)
        self.assertTrue(self.service.execute(restore)["ok"])
        self.assertEqual(self.backend.read_color(self.backend.monitors[1]), original_color)
        self.assertEqual(self.backend.values["demo-va"], original_values)

    def test_color_failure_stops_without_writing_rgb(self):
        plan = self.service.plan_match("demo-ips", "demo-va")
        original = deepcopy(self.backend.values["demo-va"])
        self.backend.write_color = lambda *_: None
        result = self.service.execute(plan)
        self.assertFalse(result["ok"])
        self.assertIn("color_preset", result["failed"])
        self.assertEqual(original, self.backend.values["demo-va"])

    def test_cross_control_side_effect_is_detected_in_unchanged_values(self):
        self.backend.values["demo-va"]["contrast"] = Value(70, 100)
        write = self.backend.write

        def side_effect(monitor, feature, value):
            write(monitor, feature, value)
            if feature == "green":
                self.backend.values[monitor.id]["contrast"] = Value(72, 100)

        self.backend.write = side_effect
        result = self.service.execute(self.service.plan_match("demo-ips", "demo-va"))
        self.assertFalse(result["ok"])
        self.assertIn("contrast", result["failed"])

    def test_bridge_uses_one_time_server_side_preview_tokens(self):
        bridge = Bridge(self.service)
        preview = bridge.dispatch("preview_match", {"source": "demo-ips", "target": "demo-va"})
        self.assertNotIn("before", preview.get("tone") or "")
        self.assertTrue(bridge.dispatch("apply", {"token": preview["token"]})["ok"])
        with self.assertRaisesRegex(MonitorError, "expirada"):
            bridge.dispatch("apply", {"token": preview["token"]})
        with self.assertRaisesRegex(MonitorError, "não permitida"):
            bridge.dispatch("shell", {"command": "anything"})

    def test_bridge_new_preview_invalidates_old_token(self):
        bridge = Bridge(self.service)
        first = bridge.dispatch("preview_match", {"source": "demo-ips", "target": "demo-va"})
        bridge.dispatch("preview_set", {"target": "demo-va", "values": {"brightness": 20}})
        with self.assertRaises(MonitorError):
            bridge.dispatch("apply", {"token": first["token"]})


if __name__ == "__main__":
    unittest.main()
