"""Diagnóstico somente leitura da saída NVIDIA. Sem escrever no driver.

ABI NV_COLOR_DATA_V5 e IDs públicos de NVIDIA/nvapi (MIT), consultados em 07/11/2026.
Não conclui o nível físico de preto nem a configuração do OSD a partir da GPU.
"""
import ctypes as C
import os
from pathlib import Path
import sys

from .models import MonitorError


class ColorFields(C.Structure):
    _fields_ = [("format", C.c_uint8), ("colorimetry", C.c_uint8),
                ("dynamic_range", C.c_uint8), ("bpc", C.c_int),
                ("policy", C.c_int), ("depth", C.c_int)]


class ColorData(C.Structure):
    _fields_ = [("version", C.c_uint32), ("size", C.c_uint16),
                ("command", C.c_uint8), ("data", ColorFields)]


def nvidia_output(device):
    if sys.platform != "win32" or C.sizeof(C.c_void_p) != 8:
        raise MonitorError("Diagnóstico NVIDIA requer Windows/Python de 64 bits.")
    library = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "nvapi64.dll"
    try:
        dll = C.CDLL(str(library))
        query = dll.nvapi_QueryInterface
        query.argtypes, query.restype = [C.c_uint32], C.c_void_p

        def function(identifier, *args):
            pointer = query(identifier)
            if not pointer:
                raise MonitorError("Driver não expõe esta consulta NVIDIA.")
            return C.CFUNCTYPE(C.c_int, *args)(pointer)

        if function(0x0150E828)() != 0:
            raise MonitorError("Não foi possível iniciar a consulta NVIDIA.")
        try:
            display = C.c_uint32()
            status = function(0xAE457190, C.c_char_p, C.POINTER(C.c_uint32))(
                device.encode("ascii"), C.byref(display))
            if status:
                raise MonitorError(f"Saída não localizada pela NVIDIA ({status}).")
            color = ColorData()
            color.size = C.sizeof(color)
            color.version = C.sizeof(color) | (5 << 16)
            color.command = 1  # NV_COLOR_CMD_GET. Não há SET neste módulo.
            status = function(0x92F9D80D, C.c_uint32, C.POINTER(ColorData))(display, C.byref(color))
            if status:
                raise MonitorError(f"Driver não informou a faixa RGB ({status}).")
            rgb = color.data.format == 0
            return {"vendor": "NVIDIA", "format": {0: "RGB", 1: "YCbCr 4:2:2", 2: "YCbCr 4:4:4", 3: "YCbCr 4:2:0"}.get(color.data.format, "Não informado"),
                    "range": {0: "full", 1: "limited"}.get(color.data.dynamic_range, "unknown") if rgb else "not_rgb",
                    "bits": {1: 6, 2: 8, 3: 10, 4: 12, 5: 16}.get(color.data.bpc),
                    "read_only": True}
        finally:
            function(0xD22BDD7E)()
    except (OSError, AttributeError, UnicodeError) as exc:
        raise MonitorError("Diagnóstico NVIDIA indisponível neste driver.") from exc
