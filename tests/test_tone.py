import ctypes as C
from ctypes import wintypes as W
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from monitor_tool.models import Monitor, MonitorError
from monitor_tool.tone import ColorInfo, DisplayPath, Mode, SourceName, WindowsTone


@unittest.skipUnless(sys.platform == "win32", "ABI Win32")
class ToneBackendTests(unittest.TestCase):
    def backend(self, flags=0, clones=1, query_error=0):
        backend = WindowsTone.__new__(WindowsTone)

        def sizes(_flags, paths, modes):
            C.cast(paths, C.POINTER(W.UINT)).contents.value = clones
            C.cast(modes, C.POINTER(W.UINT)).contents.value = clones
            return 0

        def query(_flags, count, paths, _mcount, _modes, _topology):
            for i in range(clones):
                paths[i].source.id = 1
                paths[i].target.id = i
            return query_error

        def info(ptr):
            # Os dois registros começam pelo mesmo header com tipo/size.
            kind = C.cast(ptr, C.POINTER(W.UINT)).contents.value
            if kind == 1:
                C.cast(ptr, C.POINTER(SourceName)).contents.name = "DISPLAY1"
            else:
                C.cast(ptr, C.POINTER(ColorInfo)).contents.flags = flags
            return 0

        backend.user = SimpleNamespace(GetDisplayConfigBufferSizes=sizes, QueryDisplayConfig=query,
                                       DisplayConfigGetDeviceInfo=info)
        backend.gdi = SimpleNamespace(CreateDCW=Mock(return_value=123), DeleteDC=Mock(return_value=True))
        return backend

    def test_win32_struct_sizes(self):
        self.assertEqual(C.sizeof(DisplayPath), 72)
        self.assertEqual(C.sizeof(Mode), 64)
        self.assertEqual(C.sizeof(ColorInfo), 32)

    def test_sdr_is_required_and_hdr_flag_blocks(self):
        self.backend(flags=1).require_sdr("DISPLAY1")  # HDR suportado, mas desligado.
        with self.assertRaisesRegex(MonitorError, "HDR"):
            self.backend(flags=3).require_sdr("DISPLAY1")

    def test_cloned_targets_and_unknown_device_are_blocked(self):
        with self.assertRaisesRegex(MonitorError, "único"):
            self.backend(clones=2).require_sdr("DISPLAY1")
        with self.assertRaises(MonitorError):
            self.backend().require_sdr("DISPLAY2")

    def test_query_failure_never_opens_dc(self):
        backend = self.backend(query_error=5)
        with self.assertRaises(MonitorError):
            with backend.dc(Monitor("x", "Test", "DISPLAY1", "x")):
                pass
        backend.gdi.CreateDCW.assert_not_called()

    def test_dc_is_released_after_failure(self):
        backend = self.backend()
        with self.assertRaises(RuntimeError):
            with backend.dc(Monitor("x", "Test", "DISPLAY1", "x")) as dc:
                self.assertEqual(dc, 123)
                raise RuntimeError("leitura falhou")
        backend.gdi.DeleteDC.assert_called_once_with(123)

    def test_topology_race_is_bounded_and_blocks(self):
        backend = self.backend(query_error=122)
        with self.assertRaisesRegex(MonitorError, "mudaram"):
            backend.require_sdr("DISPLAY1")


if __name__ == "__main__":
    unittest.main()
