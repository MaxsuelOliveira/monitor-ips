"""Bindings Win32 com assinaturas explícitas (inclusive handles de 64 bits)."""
import ctypes as C
from ctypes import wintypes as W
from contextlib import contextmanager
import hashlib
import sys
import time

from .models import FEATURES, Monitor, MonitorError, Value


class PhysicalMonitor(C.Structure):
    _fields_ = [("handle", W.HANDLE), ("description", W.WCHAR * 128)]


class MonitorInfo(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("monitor", W.RECT), ("work", W.RECT),
                ("flags", W.DWORD), ("device", W.WCHAR * 32)]


class DisplayDevice(C.Structure):
    _fields_ = [("cb", W.DWORD), ("name", W.WCHAR * 32),
                ("description", W.WCHAR * 128), ("flags", W.DWORD),
                ("device_id", W.WCHAR * 128), ("key", W.WCHAR * 128)]


class WindowsBackend:
    demo = False

    def __init__(self):
        if sys.platform != "win32":
            raise MonitorError("DDC/CI nativo requer Windows. Use --demo para experimentar.")
        self.user = C.WinDLL("user32", use_last_error=True)
        self.dx = C.WinDLL("dxva2", use_last_error=True)
        self.callback_type = C.WINFUNCTYPE(W.BOOL, W.HMONITOR, W.HDC,
                                          C.POINTER(W.RECT), W.LPARAM)
        signatures = [
            (self.user.EnumDisplayMonitors, [W.HDC, C.POINTER(W.RECT), self.callback_type, W.LPARAM]),
            (self.user.GetMonitorInfoW, [W.HMONITOR, C.POINTER(MonitorInfo)]),
            (self.user.EnumDisplayDevicesW, [W.LPCWSTR, W.DWORD, C.POINTER(DisplayDevice), W.DWORD]),
            (self.dx.GetNumberOfPhysicalMonitorsFromHMONITOR, [W.HMONITOR, C.POINTER(W.DWORD)]),
            (self.dx.GetPhysicalMonitorsFromHMONITOR, [W.HMONITOR, W.DWORD, C.POINTER(PhysicalMonitor)]),
            (self.dx.DestroyPhysicalMonitors, [W.DWORD, C.POINTER(PhysicalMonitor)]),
            (self.dx.GetVCPFeatureAndVCPFeatureReply,
             [W.HANDLE, W.BYTE, C.POINTER(C.c_int), C.POINTER(W.DWORD), C.POINTER(W.DWORD)]),
            (self.dx.SetVCPFeature, [W.HANDLE, W.BYTE, W.DWORD]),
        ]
        for function, args in signatures:
            function.argtypes = args
            function.restype = W.BOOL

    @staticmethod
    def error(action):
        code = C.get_last_error()
        return MonitorError(f"{action}: Windows {code} ({C.FormatError(code).strip()}). "
                            "Confira DDC/CI no menu do monitor, cabo e modo de imagem.")

    @contextmanager
    def session(self):
        arrays, monitors, errors = [], [], []

        def visit(hmonitor, _hdc, _rect, _data):
            # Exceções não podem atravessar um callback ctypes.
            try:
                info = MonitorInfo()
                info.cbSize = C.sizeof(info)
                if not self.user.GetMonitorInfoW(hmonitor, C.byref(info)):
                    raise self.error("Identificar tela")
                count = W.DWORD()
                if not self.dx.GetNumberOfPhysicalMonitorsFromHMONITOR(hmonitor, C.byref(count)):
                    errors.append(f"{info.device}: enumeração DDC indisponível")
                    return True
                if not count.value:
                    errors.append(f"{info.device}: nenhum monitor físico DDC")
                    return True
                physical = (PhysicalMonitor * count.value)()
                if not self.dx.GetPhysicalMonitorsFromHMONITOR(hmonitor, count, physical):
                    raise self.error("Enumerar monitores físicos")
                arrays.append(physical)
                devices = []
                index = 0
                while True:
                    device = DisplayDevice()
                    device.cb = C.sizeof(device)
                    if not self.user.EnumDisplayDevicesW(info.device, index, C.byref(device), 1):
                        break
                    if device.flags & 1:  # DISPLAY_DEVICE_ACTIVE
                        devices.append(device.device_id)
                    index += 1
                # Win32 não documenta correspondência de ordem entre as duas listas.
                # Bloquear escrita em agrupamentos ambíguos, mantendo leitura disponível.
                certain = len(devices) == 1 and count.value == 1 and bool(devices[0])
                for index, item in enumerate(physical):
                    identity = devices[0] if certain else f"ambiguous:{info.device}:{index}"
                    short = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
                    model = identity.split("#")[1] if certain and "#" in identity else ""
                    name = f"{item.description} ({model})" if model else item.description
                    monitors.append(Monitor(short, name, info.device,
                                            identity, index, certain, item.handle,
                                            (info.monitor.left, info.monitor.top,
                                             info.monitor.right, info.monitor.bottom)))
                return True
            except Exception as exc:
                errors.append(str(exc))
                return True

        callback = self.callback_type(visit)
        try:
            if not self.user.EnumDisplayMonitors(None, None, callback, 0):
                raise self.error("Enumerar telas")
            ids = [m.id for m in monitors]
            if len(ids) != len(set(ids)):
                raise MonitorError("Identificadores duplicados; escrita bloqueada. Reveja conexões.")
            self.warnings = errors
            yield monitors
        finally:
            failures = []
            for array in arrays:
                if not self.dx.DestroyPhysicalMonitors(len(array), array):
                    failures.append("Windows não confirmou liberação dos handles DDC.")
            if failures:
                import warnings
                warnings.warn(" ".join(failures), RuntimeWarning, stacklevel=2)

    def read(self, monitor, feature):
        current, maximum, kind = W.DWORD(), W.DWORD(), C.c_int()
        if not self.dx.GetVCPFeatureAndVCPFeatureReply(
                monitor.handle, FEATURES[feature][0], C.byref(kind),
                C.byref(current), C.byref(maximum)):
            raise self.error(f"Ler {FEATURES[feature][1]}")
        if kind.value != 1:  # MC_SET_PARAMETER; MC_MOMENTARY = 0
            raise MonitorError("Controle não é um parâmetro ajustável.")
        return Value(current.value, maximum.value)

    def write(self, monitor, feature, value):
        if not self.dx.SetVCPFeature(monitor.handle, FEATURES[feature][0], value):
            raise self.error(f"Ajustar {FEATURES[feature][1]}")
        time.sleep(0.15)

    def read_tone(self, monitor):
        from .tone import WindowsTone
        return WindowsTone().read(monitor)

    def write_tone(self, monitor, values):
        from .tone import WindowsTone
        WindowsTone().write(monitor, values)
