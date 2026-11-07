"""Perfis estéticos SDR; parâmetros heurísticos, sem alegação de calibração."""
import math

from .models import MonitorError

STRENGTHS = {
    "subtle": {"label": "Suave", "ips": (28, 0.015), "va": (22, 0.010)},
    "balanced": {"label": "Equilibrado", "ips": (22, 0.035), "va": (16, 0.025)},
    "cinema": {"label": "Cinema", "ips": (16, 0.055), "va": (12, 0.040)},
}


def parameters(panel, strength):
    if panel not in ("ips", "va") or strength not in STRENGTHS:
        raise MonitorError("Escolha painel ips/va e intensidade subtle, balanced ou cinema.")
    return STRENGTHS[strength][panel]


def validate_ramp(ramp):
    if (not isinstance(ramp, list) or len(ramp) != 3
            or any(not isinstance(channel, list) or len(channel) != 256 for channel in ramp)):
        raise MonitorError("Curva SDR inválida: são necessários 3 canais com 256 valores.")
    for channel in ramp:
        if any(type(v) is not int or not 0 <= v <= 65535 for v in channel):
            raise MonitorError("Curva SDR contém valores inválidos.")
        if any(a > b for a, b in zip(channel, channel[1:])):
            raise MonitorError("Curva SDR precisa ser monotônica.")
    return ramp


def oled_ramp(panel, strength):
    """Escurece meios-tons, preserva códigos 0..8 e 240..255 e os extremos.

    É uma curva absoluta/neutra: repetir o perfil não acumula o efeito. Não
    sobrepõe recursivamente a curva atual, nem fabrica saturação por clipping RGB.
    """
    _, amount = parameters(panel, strength)
    channel = []
    for index in range(256):
        x = index / 255
        t = (index - 8) / (240 - 8)
        y = x - amount * math.sin(math.pi * t) ** 2 if 0 < t < 1 else x
        channel.append(round(y * 65535))
    return validate_ramp([channel.copy() for _ in range(3)])


def ramps_match(actual, expected, tolerance=256):
    validate_ramp(actual)
    validate_ramp(expected)
    return all(abs(a - b) <= tolerance for c1, c2 in zip(actual, expected)
               for a, b in zip(c1, c2))
