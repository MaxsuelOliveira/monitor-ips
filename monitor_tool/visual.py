"""Curva SDR manual, limitada e absoluta. Não mede nem corrige a luz preta do painel."""
import math
from .models import MonitorError
from .looks import validate_ramp


def manual_ramp(gamma=1.0, black_point=0.0):
    for value in (gamma, black_point):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise MonitorError("Ajustes da curva precisam ser números finitos.")
    if not 0.85 <= gamma <= 1.15 or not 0 <= black_point <= 4:
        raise MonitorError("Meios-tons devem ficar entre 0,85 e 1,15; corte de sombras entre 0 e 4.")
    values = [round((max(0.0, (index - black_point) / (255 - black_point)) ** gamma) * 65535)
              for index in range(256)]
    return validate_ramp([values.copy() for _ in range(3)])
