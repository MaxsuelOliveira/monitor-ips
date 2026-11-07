from dataclasses import dataclass, field


# Apenas controles contínuos de imagem; nunca reset, energia ou entrada de vídeo.
FEATURES = {
    "brightness": (0x10, "Brilho"),
    "contrast": (0x12, "Contraste"),
    "red": (0x16, "Ganho vermelho"),
    "green": (0x18, "Ganho verde"),
    "blue": (0x1A, "Ganho azul"),
}

CONTROL_LABELS = {name: label for name, (_, label) in FEATURES.items()}
CONTROL_LABELS.update(color_preset="Modo de cor", tone_curve="Curva SDR")


class MonitorError(Exception):
    """Erro apresentável sem traceback na interface/CLI."""


@dataclass(frozen=True)
class Value:
    current: int
    maximum: int

    def __post_init__(self):
        if (type(self.current) is not int or type(self.maximum) is not int
                or not 0 <= self.current <= self.maximum <= 0xFFFFFFFF
                or self.maximum == 0):
            raise MonitorError("Leitura VCP inválida: valor ou máximo fora do intervalo.")


@dataclass
class Monitor:
    id: str
    name: str
    device: str
    identity: str
    physical_index: int = 0
    writable_identity: bool = True
    handle: int = field(default=0, repr=False)
    bounds: tuple[int, int, int, int] | None = None

    def public(self):
        return {k: getattr(self, k) for k in (
            "id", "name", "device", "identity", "physical_index", "writable_identity", "bounds")}
