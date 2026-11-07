"""Simulação explícita: nunca acessa hardware; estado dura somente este processo."""
from contextlib import contextmanager
from .models import Monitor, MonitorError, Value


class DemoBackend:
    demo = True
    warnings = []

    def __init__(self):
        self.hdr = False
        self.tones = {name: [[i * 257 for i in range(256)] for _ in range(3)]
                      for name in ("demo-ips", "demo-va")}
        self.monitors = [Monitor("demo-ips", "IPS de demonstração", "DEMO 1", "demo:ips"),
                         Monitor("demo-va", "VA de demonstração", "DEMO 2", "demo:va")]
        self.values = {
            "demo-ips": {"brightness": Value(35, 100), "contrast": Value(70, 100),
                         "red": Value(95, 100), "green": Value(90, 100), "blue": Value(88, 100)},
            "demo-va": {"brightness": Value(140, 200), "contrast": Value(60, 100),
                        "red": Value(100, 100), "green": Value(100, 100)},
        }

    @contextmanager
    def session(self):
        yield self.monitors

    def read(self, monitor, feature):
        try:
            return self.values[monitor.id][feature]
        except KeyError:
            raise MonitorError("Controle não disponível na demonstração.") from None

    def write(self, monitor, feature, value):
        old = self.read(monitor, feature)
        self.values[monitor.id][feature] = Value(value, old.maximum)

    def read_tone(self, monitor):
        if self.hdr:
            raise MonitorError("HDR ativo; curva SDR bloqueada na demonstração.")
        return [channel.copy() for channel in self.tones[monitor.id]]

    def write_tone(self, monitor, values):
        self.read_tone(monitor)  # Confere SDR também na escrita.
        self.tones[monitor.id] = [channel.copy() for channel in values]
