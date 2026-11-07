"""Catálogo de modelos estéticos. Percentuais DDC não são luminância medida."""
from copy import deepcopy

from .looks import oled_ramp
from .models import MonitorError

PRESETS = {
    "oled-balanced": {
        "name": "OLED equilibrado", "environment": "Luz moderada",
        "description": "Mais profundidade nos meios-tons, com sombras e realces preservados.",
        "brightness": {"ips": 22, "va": 16}, "brightness_mode": "ceiling", "curve": "balanced",
    },
    "cinema-dark": {
        "name": "Cinema escuro", "environment": "Ambiente escuro",
        "description": "Luz de fundo contida e meios-tons mais profundos para filmes.",
        "brightness": {"ips": 16, "va": 12}, "brightness_mode": "ceiling", "curve": "cinema",
    },
    "natural": {
        "name": "Cores naturais", "environment": "Uso diário SDR",
        "description": "Curva neutra, mantendo seus ganhos RGB e contraste atuais.",
        "brightness": {"ips": 32, "va": 28}, "brightness_mode": "target", "curve": "neutral",
    },
    "bright-room": {
        "name": "Ambiente claro", "environment": "Sala iluminada",
        "description": "Mais luz de fundo e curva neutra, sem aumentar ganhos RGB.",
        "brightness": {"ips": 55, "va": 45}, "brightness_mode": "target", "curve": "neutral",
    },
}


def catalog():
    return [{"id": key, **deepcopy(value)} for key, value in PRESETS.items()]


def get_preset(name, panel):
    if name not in PRESETS or panel not in ("ips", "va"):
        raise MonitorError("Escolha um modelo válido e o painel ips ou va.")
    return deepcopy(PRESETS[name])


def preset_ramp(name, panel):
    preset = get_preset(name, panel)
    if preset["curve"] == "neutral":
        return [[index * 257 for index in range(256)] for _ in range(3)]
    return oled_ramp(panel, preset["curve"])
