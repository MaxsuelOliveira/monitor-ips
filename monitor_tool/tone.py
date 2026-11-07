"""Curva GPU por dispositivo GDI, exclusivamente após confirmar SDR/um destino.

SetDeviceGammaRamp é legado e pode ser substituído pelo Windows ou outros apps.
Não é um gerenciador ICC; toda escrita exige leitura/verificação e backup no serviço.
"""
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import time

from .looks import validate_ramp
from .models import MonitorError


class Luid(C.Structure):
    _fields_ = [("low", W.DWORD), ("high", W.LONG)]


class Source(C.Structure):
    _fields_ = [("adapter", Luid), ("id", W.UINT), ("mode", W.UINT), ("status", W.UINT)]


class Rational(C.Structure):
    _fields_ = [("numerator", W.UINT), ("denominator", W.UINT)]


class Target(C.Structure):
    _fields_ = [("adapter", Luid), ("id", W.UINT), ("mode", W.UINT),
                ("technology", W.UINT), ("rotation", W.UINT), ("scaling", W.UINT),
                ("refresh", Rational), ("scanline", W.UINT),
                ("available", W.BOOL), ("status", W.UINT)]


class DisplayPath(C.Structure):
    _fields_ = [("source", Source), ("target", Target), ("flags", W.UINT)]


class Mode(C.Structure):
    # União Win32 tem 48 bytes e alinhamento de 8 (contém UINT64 pixelRate).
    _fields_ = [("type", W.UINT), ("id", W.UINT), ("adapter", Luid),
                ("payload", C.c_uint64 * 6)]


class Header(C.Structure):
    _fields_ = [("type", W.UINT), ("size", W.UINT), ("adapter", Luid), ("id", W.UINT)]


class SourceName(C.Structure):
    _fields_ = [("header", Header), ("name", W.WCHAR * 32)]


class ColorInfo(C.Structure):
    _fields_ = [("header", Header), ("flags", W.UINT),
                ("encoding", W.UINT), ("bits", W.UINT)]


Ramp = (W.WORD * 256) * 3


class WindowsTone:
    def __init__(self):
        self.user = C.WinDLL("user32", use_last_error=True)
        self.gdi = C.WinDLL("gdi32", use_last_error=True)
        bindings = [
            (self.user.GetDisplayConfigBufferSizes, [W.UINT, C.POINTER(W.UINT), C.POINTER(W.UINT)], W.LONG),
            (self.user.QueryDisplayConfig, [W.UINT, C.POINTER(W.UINT), C.POINTER(DisplayPath),
                                           C.POINTER(W.UINT), C.POINTER(Mode), C.c_void_p], W.LONG),
            (self.user.DisplayConfigGetDeviceInfo, [C.c_void_p], W.LONG),
            (self.gdi.CreateDCW, [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, C.c_void_p], W.HDC),
            (self.gdi.DeleteDC, [W.HDC], W.BOOL),
            (self.gdi.GetDeviceGammaRamp, [W.HDC, C.c_void_p], W.BOOL),
            (self.gdi.SetDeviceGammaRamp, [W.HDC, C.c_void_p], W.BOOL),
        ]
        for function, args, result in bindings:
            function.argtypes, function.restype = args, result

    def require_sdr(self, device):
        for _ in range(3):
            count, modes = W.UINT(), W.UINT()
            status = self.user.GetDisplayConfigBufferSizes(2, C.byref(count), C.byref(modes))
            if status:
                raise MonitorError(f"Não foi possível verificar HDR/SDR (Windows {status}).")
            paths, mode_array = (DisplayPath * count.value)(), (Mode * modes.value)()
            status = self.user.QueryDisplayConfig(2, C.byref(count), paths,
                                                 C.byref(modes), mode_array, None)
            if status == 122:  # ERROR_INSUFFICIENT_BUFFER: topologia mudou; reler.
                continue
            if status:
                raise MonitorError(f"Consulta de topologia falhou (Windows {status}).")
            matches = []
            for path in paths[:count.value]:
                name = SourceName()
                name.header = Header(1, C.sizeof(SourceName), path.source.adapter, path.source.id)
                status = self.user.DisplayConfigGetDeviceInfo(C.byref(name))
                if status:
                    raise MonitorError(f"Identificar SDR falhou (Windows {status}).")
                if name.name.casefold() == device.casefold():
                    matches.append(path)
            if len(matches) != 1:
                raise MonitorError("Curva SDR exige um único destino físico em modo estendido.")
            path = matches[0]
            color = ColorInfo()
            color.header = Header(9, C.sizeof(ColorInfo), path.target.adapter, path.target.id)
            status = self.user.DisplayConfigGetDeviceInfo(C.byref(color))
            if status:
                raise MonitorError(f"Não foi possível confirmar SDR (Windows {status}); curva bloqueada.")
            if color.flags & 2:  # advancedColorEnabled (HDR ou WCG)
                raise MonitorError("HDR/Advanced Color está ativo. Desative-o no Windows para usar a curva SDR.")
            return
        raise MonitorError("As conexões de tela mudaram durante a consulta. Tente novamente.")

    @contextmanager
    def dc(self, monitor):
        self.require_sdr(monitor.device)
        dc = self.gdi.CreateDCW("DISPLAY", monitor.device, None, None)
        if not dc:
            raise MonitorError("Não foi possível abrir o dispositivo de cor da tela.")
        try:
            yield dc
        finally:
            if not self.gdi.DeleteDC(dc):
                import warnings
                warnings.warn("Windows não confirmou liberação do DC de cor.", RuntimeWarning, stacklevel=2)

    def read(self, monitor):
        with self.dc(monitor) as dc:
            ramp = Ramp()
            if not self.gdi.GetDeviceGammaRamp(dc, C.byref(ramp)):
                raise MonitorError("Driver não permite ler a curva SDR deste monitor.")
            return validate_ramp([list(channel) for channel in ramp])

    def write(self, monitor, values):
        validate_ramp(values)
        ramp = Ramp(*( (W.WORD * 256)(*channel) for channel in values ))
        with self.dc(monitor) as dc:
            if not self.gdi.SetDeviceGammaRamp(dc, C.byref(ramp)):
                raise MonitorError("Driver recusou a curva SDR. O backup permanece disponível.")
        time.sleep(0.15)
