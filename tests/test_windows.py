"""Simula a API Win32 para testar posse/liberação dos handles sem hardware."""
import ctypes as C
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from monitor_tool.windows import DisplayDevice, MonitorInfo, WindowsBackend
from ctypes import wintypes as W


class WindowsLifecycleTests(unittest.TestCase):
    def backend(self, physical_count=1):
        backend = WindowsBackend.__new__(WindowsBackend)
        backend.callback_type = lambda function: function

        def info(handle, ptr):
            C.cast(ptr, C.POINTER(MonitorInfo)).contents.device = f"DISPLAY{handle}"
            return True

        def count(_handle, ptr):
            C.cast(ptr, C.POINTER(W.DWORD)).contents.value = physical_count
            return True

        def monitors(handle, _count, array):
            for index in range(physical_count):
                array[index].handle = handle * 10 + index
                array[index].description = "Monitor de teste"
            return True

        def devices(name, index, ptr, flags):
            self.assertEqual(flags, 1)
            if index:
                return False
            device = C.cast(ptr, C.POINTER(DisplayDevice)).contents
            device.device_id = f"interface:{name}"
            device.flags = 1
            return True

        def enum(_hdc, _rect, callback, _data):
            callback(1, None, None, 0)
            callback(2, None, None, 0)
            return True

        backend.user = SimpleNamespace(GetMonitorInfoW=info, EnumDisplayDevicesW=devices,
                                       EnumDisplayMonitors=enum)
        backend.dx = SimpleNamespace(GetNumberOfPhysicalMonitorsFromHMONITOR=count,
                                     GetPhysicalMonitorsFromHMONITOR=monitors,
                                     DestroyPhysicalMonitors=Mock(return_value=True))
        return backend

    def test_all_handles_closed_after_success_and_exception(self):
        backend = self.backend()
        with backend.session() as monitors:
            self.assertEqual(len(monitors), 2)
            self.assertTrue(all(m.writable_identity for m in monitors))
            self.assertEqual(monitors[0].handle, 10)
        self.assertEqual(backend.dx.DestroyPhysicalMonitors.call_count, 2)
        backend.dx.DestroyPhysicalMonitors.reset_mock()
        with self.assertRaises(RuntimeError):
            with backend.session():
                raise RuntimeError("erro posterior à enumeração")
        self.assertEqual(backend.dx.DestroyPhysicalMonitors.call_count, 2)

    def test_multiple_physical_monitors_never_assume_identity_order(self):
        backend = self.backend(physical_count=2)
        with backend.session() as monitors:
            self.assertEqual(len(monitors), 4)
            self.assertTrue(all(not m.writable_identity for m in monitors))
            self.assertEqual(len({m.id for m in monitors}), 4)
        self.assertEqual(backend.dx.DestroyPhysicalMonitors.call_count, 2)
        self.assertEqual(backend.dx.DestroyPhysicalMonitors.call_args.args[0], 2)

    def test_cleanup_failure_is_observable(self):
        backend = self.backend()
        backend.dx.DestroyPhysicalMonitors.return_value = False
        with self.assertWarns(RuntimeWarning):
            with backend.session():
                pass


if __name__ == "__main__":
    unittest.main()
