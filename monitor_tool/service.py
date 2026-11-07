"""Regras compartilhadas por GUI e CLI; nenhuma escrita sem backup prévio."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid

from .models import FEATURES, MonitorError, Value
from .looks import oled_ramp, parameters, ramps_match, STRENGTHS, validate_ramp

_LOCK = threading.Lock()


def backup_directory(demo=False):
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "MonitorIPS" / ("demo-backups" if demo else "backups")


@dataclass(frozen=True)
class Change:
    feature: str
    before: int
    after: int
    maximum: int


@dataclass
class Plan:
    monitor: dict
    changes: list[Change]
    skipped: dict
    demo: bool
    tone: dict | None = None
    notes: list[str] = field(default_factory=list)
    reference: dict | None = None
    expected_target: dict | None = None
    color: dict | None = None

    @property
    def has_changes(self):
        return bool(self.changes or self.tone or self.color)

    def public(self):
        return {"monitor": self.monitor, "changes": [asdict(c) for c in self.changes],
                "skipped": self.skipped, "demo": self.demo, "tone": self.tone, "notes": self.notes}


def save_json(path, data):
    """Publica arquivo completo sem sobrescrever um backup existente."""
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".monitor-", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard link é publicação atômica e falha se o destino já existir (Windows/NTFS).
        os.link(temp, path)
        return path
    except OSError as exc:
        raise MonitorError(f"Não foi possível salvar {path}: {exc}") from exc
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def load_profile(path):
    try:
        path = Path(path)
        if path.stat().st_size > 1_000_000:
            raise MonitorError("Backup excede o tamanho permitido.")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if (not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] not in (1, 2, 3)
                or type(data.get("demo")) is not bool
                or not isinstance(data.get("monitor"), dict)
                or not isinstance(data["monitor"].get("identity"), str)
                or not isinstance(data["monitor"].get("id"), str)
                or not isinstance(data.get("values"), dict)):
            raise MonitorError("Formato de backup inválido ou versão incompatível.")
        for name, value in data["values"].items():
            if name not in FEATURES or not isinstance(value, dict):
                raise MonitorError("Backup contém controle não permitido.")
            Value(value.get("current"), value.get("maximum"))
        if data["schema"] == 2 or "tone_curve" in data and data["schema"] == 3:
            validate_ramp(data.get("tone_curve"))
        elif "tone_curve" in data:
            raise MonitorError("Backup de curva SDR exige schema 2.")
        if not data["values"] and "tone_curve" not in data:
            raise MonitorError("Backup vazio: nenhum controle ou curva SDR.")
        if data["schema"] == 3:
            color = data.get("color_preset")
            if (not isinstance(color, dict) or type(color.get("current")) is not int
                    or not isinstance(color.get("supported"), list)
                    or any(type(v) is not int or not 1 <= v <= 0x0D for v in color["supported"])
                    or color["current"] not in color["supported"]):
                raise MonitorError("Backup contém modo de cor inválido.")
        elif "color_preset" in data:
            raise MonitorError("Backup com modo de cor exige schema 3.")
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise MonitorError(f"Não foi possível ler o backup: {exc}") from exc


class Service:
    def __init__(self, backend, backups=None):
        self.backend = backend
        self.backups = Path(backups) if backups else backup_directory(backend.demo)

    @contextmanager
    def session(self):
        # Coordena instâncias desta ferramenta (GUI/CLI); não controla OSD nem outros apps.
        if not _LOCK.acquire(blocking=False):
            raise MonitorError("Outra operação está em andamento.")
        stream = None
        locked = False
        try:
            if not self.backend.demo and os.name == "nt":
                import msvcrt
                lock_path = backup_directory().parent / "ddc.lock"
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                stream = lock_path.open("a+b")
                if stream.seek(0, 2) == 0:
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                except OSError:
                    raise MonitorError("Outra instância está acessando os monitores.") from None
            with self.backend.session() as monitors:
                yield monitors
        finally:
            try:
                if stream is not None:
                    try:
                        if locked:
                            stream.seek(0)
                            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    finally:
                        stream.close()
            finally:
                _LOCK.release()

    @staticmethod
    def find(monitors, monitor_id):
        matches = [m for m in monitors if m.id == monitor_id]
        if len(matches) != 1:
            raise MonitorError(f"Monitor '{monitor_id}' ausente ou ambíguo. Atualize a lista.")
        return matches[0]

    def snapshot(self, monitor, include_tone=False, include_color=False):
        values, errors = {}, {}
        for name in FEATURES:
            try:
                values[name] = asdict(self.backend.read(monitor, name))
            except MonitorError as exc:
                errors[name] = str(exc)
        profile = {"schema": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                   "demo": self.backend.demo, "monitor": monitor.public(),
                   "values": values, "unavailable": errors}
        if include_tone:
            try:
                profile["tone_curve"] = self.backend.read_tone(monitor)
                profile["schema"] = 2
            except MonitorError as exc:
                profile["tone_unavailable"] = str(exc)
        if include_color:
            try:
                profile["color_preset"] = self.backend.read_color(monitor)
                profile["schema"] = 3
            except MonitorError as exc:
                profile["color_unavailable"] = str(exc)
        return profile

    def inspect(self, include_tone=False):
        with self.session() as monitors:
            profiles = [self.snapshot(m, include_tone, include_color=True) for m in monitors]
            return {"demo": self.backend.demo, "monitors": profiles,
                    "warnings": list(getattr(self.backend, "warnings", []))}

    def backup(self, monitor_id, path=None):
        with self.session() as monitors:
            monitor = self.find(monitors, monitor_id)
            profile = self.snapshot(monitor, include_tone=True, include_color=True)
            if not profile["values"] and "tone_curve" not in profile:
                raise MonitorError("Nenhum dos cinco controles pôde ser lido; backup não criado.")
            return save_json(path or self.new_backup_path(monitor.id), profile)

    def new_backup_path(self, monitor_id):
        # IDs vêm do backend, mas o nome nunca incorpora dados arbitrários do monitor.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self.backups / f"{stamp}-{uuid.uuid4().hex}.json"

    @staticmethod
    def check_target(monitor):
        if not monitor.writable_identity:
            raise MonitorError("Identificação física ambígua. Use modo estendido e conexão direta.")

    def compare(self, source_id, target_id, features=None):
        names = list(FEATURES) if features is None else list(features)
        if not names or any(n not in FEATURES for n in names) or len(names) != len(set(names)):
            raise MonitorError("Selecione controles válidos, sem repetições.")
        if source_id == target_id:
            raise MonitorError("Origem e destino devem ser monitores diferentes.")
        with self.session() as monitors:
            source = self.find(monitors, source_id)
            target = self.find(monitors, target_id)
            self.check_target(target)
            changes, skipped = [], {}
            for name in names:
                try:
                    a, b = self.backend.read(source, name), self.backend.read(target, name)
                    # Proporção do intervalo nativo, não equivalência fotométrica.
                    after = (a.current * b.maximum + a.maximum // 2) // a.maximum
                    if b.current != after:
                        changes.append(Change(name, b.current, after, b.maximum))
                except MonitorError as exc:
                    skipped[name] = str(exc)
            return Plan(target.public(), changes, skipped, self.backend.demo)

    def plan_match(self, source_id, target_id, mode="exact", include_tone=True, color_mode="auto"):
        """Copia os controles/curva da referência, com guarda de ambas as telas."""
        if source_id == target_id or mode not in ("exact", "relative") or color_mode not in ("auto", "source", "user1", "user2"):
            raise MonitorError("Escolha monitores diferentes e modo exact ou relative.")
        with self.session() as monitors:
            source, target = self.find(monitors, source_id), self.find(monitors, target_id)
            self.check_target(source)
            self.check_target(target)
            a = self.snapshot(source, include_tone, include_color=True)
            b = self.snapshot(target, include_tone, include_color=True)
            changes, skipped, expected = [], {}, {}
            for name in FEATURES:
                if name not in a["values"] or name not in b["values"]:
                    skipped[name] = "Controle indisponível na origem ou no destino."
                    continue
                source_value, target_value = a["values"][name], b["values"][name]
                value = source_value["current"]
                if mode == "relative":
                    value = (value * target_value["maximum"] + source_value["maximum"] // 2) // source_value["maximum"]
                if value > target_value["maximum"]:
                    skipped[name] = "O valor do IPS excede o máximo do destino; use o modo proporcional."
                    continue
                expected[name] = {"current": value, "maximum": target_value["maximum"]}
                if value != target_value["current"]:
                    changes.append(Change(name, target_value["current"], value, target_value["maximum"]))
            tone = None
            if include_tone:
                for profile in (a, b):
                    if "tone_curve" not in profile:
                        raise MonitorError("Não foi possível copiar a curva SDR: " +
                                           profile.get("tone_unavailable", "curva indisponível") +
                                           " Desmarque a curva para copiar somente controles DDC.")
                if not ramps_match(b["tone_curve"], a["tone_curve"], tolerance=0):
                    tone = {"before": b["tone_curve"], "after": a["tone_curve"],
                            "label": "Copiar curva SDR atual do IPS"}
            if not expected and not include_tone:
                raise MonitorError("Nenhum controle em comum pôde ser lido.")
            notes = ["Cópia dos mesmos valores nativos." if mode == "exact" else "Cópia proporcional aos máximos.",
                     "Apenas o destino será ajustado. A aparência pode variar entre IPS e VA."]
            plan = Plan(target.public(), changes, skipped, self.backend.demo, tone, notes)
            plan.reference = a
            plan.expected_target = {"values": expected}
            if "color_preset" in a and "color_preset" in b:
                desired = a["color_preset"]["current"]
                rgb_differs = any(name in expected and b["values"][name]["current"] != expected[name]["current"]
                                  for name in ("red", "green", "blue"))
                # Presets de temperatura podem ter ganhos fixos de fábrica distintos.
                # User 1 é explicitamente anunciado nas capacidades antes de habilitar RGB.
                if color_mode in ("user1", "user2"):
                    desired = {"user1": 0x0B, "user2": 0x0C}[color_mode]
                elif color_mode == "auto" and desired not in (0x0B, 0x0C, 0x0D):
                    current_mode = b["color_preset"]["current"]
                    if current_mode in (0x0B, 0x0C, 0x0D):
                        desired = current_mode
                    elif rgb_differs:
                        # User 2 foi verificado no VA local; nunca enviar se não anunciado.
                        desired = next((v for v in (0x0C, 0x0B) if v in b["color_preset"]["supported"]), desired)
                if desired != a["color_preset"]["current"]:
                    notes.append(f"Destino em modo Usuário (0x{desired:02X}) para permitir RGB editável; "
                                 "o preset nominal pode diferir do IPS, mas os ganhos copiados serão verificados.")
                if desired in b["color_preset"]["supported"]:
                    plan.expected_target["color_preset"] = desired
                    if desired != b["color_preset"]["current"]:
                        plan.color = {"before": b["color_preset"]["current"], "after": desired}
                else:
                    skipped["color_preset"] = "Modo de cor da origem não suportado no destino."
            else:
                skipped["color_preset"] = "Modo de cor não informado por uma das telas."
            if include_tone:
                plan.expected_target["tone_curve"] = a["tone_curve"]
            return plan

    def plan_set(self, target_id, values):
        if not values or any(n not in FEATURES or type(v) is not int for n, v in values.items()):
            raise MonitorError("Forneça controles válidos e valores inteiros.")
        with self.session() as monitors:
            target = self.find(monitors, target_id)
            self.check_target(target)
            changes = []
            for name, after in values.items():
                before = self.backend.read(target, name)
                if not 0 <= after <= before.maximum:
                    raise MonitorError(f"{FEATURES[name][1]} deve estar entre 0 e {before.maximum}.")
                if before.current != after:
                    changes.append(Change(name, before.current, after, before.maximum))
            return Plan(target.public(), changes, {}, self.backend.demo)

    def plan_visual(self, target_id, values, tone=None):
        """Ajustes DDC manuais e curva SDR explícita, sem inventar calibração física."""
        if tone is None:
            return self.plan_set(target_id, values)
        if not isinstance(tone, dict) or any(k not in ("gamma", "black_point") for k in tone):
            raise MonitorError("A curva aceita apenas meios-tons e corte de sombras.")
        from .visual import manual_ramp
        after_tone = manual_ramp(tone.get("gamma", 1.0), tone.get("black_point", 0.0))
        if values:
            plan = self.plan_set(target_id, values)
        else:
            with self.session() as monitors:
                target = self.find(monitors, target_id)
                self.check_target(target)
                plan = Plan(target.public(), [], {}, self.backend.demo)
        with self.session() as monitors:
            target = self.find(monitors, target_id)
            self.check_target(target)
            before_tone = self.backend.read_tone(target)
            expected = {}
            for name, value in values.items():
                current = self.backend.read(target, name)
                expected[name] = asdict(Value(value, current.maximum))
            plan.expected_target = {"values": expected, "tone_curve": after_tone}
            if before_tone != after_tone:
                plan.tone = {"before": before_tone, "after": after_tone,
                             "label": f"Curva manual SDR: meios-tons {tone.get('gamma', 1):.2f}; corte {tone.get('black_point', 0):g}/255"}
            plan.notes.extend(["A curva substitui a curva GPU atual e será salva no backup. Não altera o preto físico do painel.",
                               "Corte de sombras pode esconder detalhes próximos do preto; confira o padrão antes de manter."])
            return plan

    def plan_restore(self, target_id, path):
        profile = load_profile(path)
        if profile["demo"] != self.backend.demo:
            raise MonitorError("Backups de demonstração e reais não podem ser misturados.")
        with self.session() as monitors:
            target = self.find(monitors, target_id)
            self.check_target(target)
            if (profile["monitor"]["identity"] != target.identity
                    or profile["monitor"]["id"] != target.id):
                raise MonitorError("Este backup pertence a outro monitor ou conexão.")
            changes = []
            for name, saved in profile["values"].items():
                before = self.backend.read(target, name)
                if before.maximum != saved["maximum"]:
                    raise MonitorError(f"Intervalo de {name} mudou. Confira o modo de imagem.")
                if before.current != saved["current"]:
                    changes.append(Change(name, before.current, saved["current"], before.maximum))
            tone, notes = None, []
            if "tone_curve" in profile:
                before_tone = self.backend.read_tone(target)
                if not ramps_match(before_tone, profile["tone_curve"], tolerance=0):
                    tone = {"before": before_tone, "after": profile["tone_curve"],
                            "label": "Restaurar curva SDR do backup"}
            else:
                notes.append("Este backup contém somente DDC/CI; não altera a curva de tons da GPU.")
            plan = Plan(target.public(), changes, {}, self.backend.demo, tone, notes)
            if "color_preset" in profile:
                color = self.backend.read_color(target)
                desired = profile["color_preset"]["current"]
                if desired not in color["supported"]:
                    raise MonitorError("Modo de cor do backup não é mais suportado.")
                if color["current"] != desired:
                    plan.color = {"before": color["current"], "after": desired}
                plan.expected_target = {"values": profile["values"], "color_preset": desired}
                if "tone_curve" in profile:
                    plan.expected_target["tone_curve"] = profile["tone_curve"]
            return plan

    def plan_preset(self, target_id, preset_id, panel, tone_curve=True, brightness=None):
        from .presets import get_preset, preset_ramp
        preset = get_preset(preset_id, panel)
        if type(tone_curve) is not bool:
            raise MonitorError("A opção de curva SDR precisa ser booleana.")
        if brightness is not None and (type(brightness) is not int or not 0 <= brightness <= 100):
            raise MonitorError("Brilho personalizado deve ser inteiro de 0 a 100% da escala DDC.")
        with self.session() as monitors:
            target = self.find(monitors, target_id)
            self.check_target(target)
            profile = self.snapshot(target, include_color=True)
            expected = {name: value.copy() for name, value in profile["values"].items()}
            changes, skipped, tone = [], {}, None
            percent = preset["brightness"][panel] if brightness is None else brightness
            ceiling = brightness is None and preset["brightness_mode"] == "ceiling"
            before = profile["values"].get("brightness")
            if before:
                after = (before["maximum"] * percent + 50) // 100
                if ceiling:
                    after = min(before["current"], after)
                expected["brightness"] = {"current": after, "maximum": before["maximum"]}
                if before["current"] != after:
                    changes.append(Change("brightness", before["current"], after, before["maximum"]))
            elif not tone_curve:
                raise MonitorError("Sem curva SDR, o modelo exige controle de brilho disponível.")
            else:
                skipped["brightness"] = profile["unavailable"].get("brightness", "Indisponível.")
            notes = [f"Modelo: {preset['name']} / {panel.upper()}. "
                     f"{'Teto de' if ceiling else 'Alvo de'} brilho {percent}% da escala DDC; não é cd/m².",
                     "Modelo estético ajustável, sem calibração medida. IPS/VA não se tornam idênticos a OLED.",
                     "Contraste, ganhos RGB e modo de cor atuais serão preservados e verificados."]
            desired = {"values": expected}
            if "color_preset" in profile:
                desired["color_preset"] = profile["color_preset"]["current"]
            if tone_curve:
                before_tone = self.backend.read_tone(target)
                after_tone = preset_ramp(preset_id, panel)
                equivalent = ramps_match(before_tone, after_tone, tolerance=256)
                desired["tone_curve"] = before_tone if equivalent else after_tone
                if not equivalent:
                    tone = {"before": before_tone, "after": after_tone,
                            "label": f"{preset['name']} / {panel.upper()} / curva SDR absoluta"}
                notes.append("A curva SDR substitui a curva atual dos três canais; o backup permite restaurá-la. "
                             "Sombras 0–8 e realces 240–255 preservados; sem corte de sombras. "
                             "Não certifica gamma 2,2, D65 ou gamut sRGB e não altera ICC.")
            else:
                notes.append("Sem curva SDR: somente o brilho é ajustado; não aplica a aparência tonal do modelo.")
            if before and expected["brightness"]["current"] > before["current"]:
                notes.append("Este modelo aumenta o brilho atual. Confira o conforto visual antes de manter.")
            return Plan(target.public(), changes, skipped, self.backend.demo, tone, notes,
                        expected_target=desired)

    def plan_oled(self, target_id, panel, strength="balanced", tone_curve=False):
        percent, _ = parameters(panel, strength)
        with self.session() as monitors:
            target = self.find(monitors, target_id)
            self.check_target(target)
            changes, skipped, tone = [], {}, None
            try:
                before = self.backend.read(target, "brightness")
                # Não aumentar a luz de fundo que o usuário já deixou baixa.
                after = min(before.current, max(1, (before.maximum * percent + 50) // 100))
                if before.current != after:
                    changes.append(Change("brightness", before.current, after, before.maximum))
            except MonitorError as exc:
                skipped["brightness"] = str(exc)
                if not tone_curve:
                    raise MonitorError("O perfil sem curva SDR exige leitura de brilho: " + str(exc)) from exc
            notes = [f"Sabor OLED / {panel.upper()} / {STRENGTHS[strength]['label']}: "
                     f"teto de brilho {percent}% (não aumenta brilho já menor). Contraste e RGB preservados.",
                     "Perfil estético heurístico: não transforma o painel em OLED nem é calibração medida."]
            if tone_curve:
                before_tone = self.backend.read_tone(target)  # Falhar antes de qualquer escrita em HDR.
                after_tone = oled_ramp(panel, strength)
                if not ramps_match(before_tone, after_tone, tolerance=256):
                    tone = {"before": before_tone, "after": after_tone,
                            "label": f"Sabor OLED SDR / {panel.upper()} / {STRENGTHS[strength]['label']}"}
                notes.append("A curva SDR substitui a curva GPU atual; backup inclui os 3 canais. "
                             "Não reescreve ICC. Outros apps/Windows podem substituir a curva depois.")
            else:
                notes.append("Sem curva SDR: ajusta apenas a luz de fundo. Para meios-tons mais profundos, "
                             "ative a opção de curva SDR (substitui a curva GPU atual).")
            return Plan(target.public(), changes, skipped, self.backend.demo, tone, notes)

    def execute(self, plan):
        if plan.demo != self.backend.demo:
            raise MonitorError("Plano pertence a outro modo de execução.")
        with self.session() as monitors:
            target = self.find(monitors, plan.monitor["id"])
            self.check_target(target)
            if target.identity != plan.monitor["identity"]:
                raise MonitorError("Monitor mudou desde a prévia. Atualize a comparação.")
            profile = self.snapshot(target, include_tone=True, include_color=True)
            if plan.reference:
                ref = self.find(monitors, plan.reference["monitor"]["id"])
                if ref.identity != plan.reference["monitor"]["identity"]:
                    raise MonitorError("A referência mudou. Prepare novamente.")
                actual_ref = self.snapshot(ref, "tone_curve" in plan.reference, "color_preset" in plan.reference)
                if (actual_ref["values"] != plan.reference["values"]
                        or actual_ref.get("tone_curve") != plan.reference.get("tone_curve")
                        or actual_ref.get("color_preset") != plan.reference.get("color_preset")):
                    raise MonitorError("Os valores do IPS mudaram desde a prévia. Prepare novamente.")
            if plan.expected_target:
                # Controles já iguais também participam da guarda; podem mudar depois da prévia.
                changed = {c.feature for c in plan.changes}
                for name, expected in plan.expected_target["values"].items():
                    if name not in changed and profile["values"].get(name) != expected:
                        raise MonitorError("O destino mudou desde a prévia. Prepare novamente.")
                if "tone_curve" in plan.expected_target and not plan.tone:
                    if profile.get("tone_curve") != plan.expected_target["tone_curve"]:
                        raise MonitorError("A curva do destino mudou desde a prévia. Prepare novamente.")
                if "color_preset" in plan.expected_target and not plan.color:
                    if profile.get("color_preset", {}).get("current") != plan.expected_target["color_preset"]:
                        raise MonitorError("O modo de cor mudou desde a prévia. Prepare novamente.")
            seen = set()
            for change in plan.changes:
                if change.feature not in FEATURES or change.feature in seen:
                    raise MonitorError("Plano contém controle inválido ou repetido.")
                seen.add(change.feature)
                expected = {"current": change.before, "maximum": change.maximum}
                if profile["values"].get(change.feature) != expected:
                    raise MonitorError("Valores mudaram desde a prévia. Gere uma nova comparação.")
                if type(change.after) is not int or not 0 <= change.after <= change.maximum:
                    raise MonitorError("Plano contém valor fora do intervalo.")
            if plan.tone:
                validate_ramp(plan.tone["before"])
                validate_ramp(plan.tone["after"])
                if "tone_curve" not in profile:
                    raise MonitorError(profile.get("tone_unavailable", "Curva SDR indisponível."))
                if not ramps_match(profile["tone_curve"], plan.tone["before"], tolerance=0):
                    raise MonitorError("Curva SDR mudou desde a prévia. Prepare novamente.")
            if plan.color:
                current_color = profile.get("color_preset", {})
                if (current_color.get("current") != plan.color["before"]
                        or plan.color["after"] not in current_color.get("supported", [])):
                    raise MonitorError("O modo de cor mudou ou não é suportado. Prepare novamente.")
            if not plan.has_changes:
                return {"ok": True, "backup": None, "applied": [], "failed": {}}
            # Salvar e confirmar o fechamento do arquivo antes da primeira escrita DDC.
            backup = save_json(self.new_backup_path(target.id), profile)
            applied, failed = [], {}
            if plan.color:
                try:
                    self.backend.write_color(target, plan.color["after"])
                    if self.backend.read_color(target)["current"] != plan.color["after"]:
                        raise MonitorError("Monitor não confirmou a mudança do modo de cor.")
                    applied.append("color_preset")
                except Exception as exc:
                    failed["color_preset"] = str(exc)
            writes = list(plan.changes)
            if plan.color and not failed:
                # Presets podem mudar outros controles, inclusive os antes iguais.
                writes = []
                for name, expected in plan.expected_target["values"].items():
                    try:
                        current = self.backend.read(target, name)
                        if current.current != expected["current"]:
                            writes.append(Change(name, current.current, expected["current"], expected["maximum"]))
                    except MonitorError as exc:
                        failed[name] = str(exc)
                        break
            for change in writes if not failed else []:
                try:
                    self.backend.write(target, change.feature, change.after)
                    actual = self.backend.read(target, change.feature)
                    if actual.current != change.after or actual.maximum != change.maximum:
                        raise MonitorError(f"Leitura após escrita retornou {actual.current}/{actual.maximum}; "
                                           f"esperado {change.after}/{change.maximum}.")
                    applied.append(change.feature)
                except Exception as exc:
                    # Interromper: não acumular efeitos após uma falha parcial.
                    failed[change.feature] = str(exc)
                    break
            if not failed:
                # Uma escrita posterior pode alterar um controle já verificado (presets RGB).
                for change in writes:
                    try:
                        actual = self.backend.read(target, change.feature)
                        if actual != Value(change.after, change.maximum):
                            raise MonitorError("Valor mudou após os demais ajustes; confira o modo de imagem.")
                    except Exception as exc:
                        failed[change.feature] = str(exc)
                        applied.remove(change.feature)
            if plan.tone and not failed:
                try:
                    self.backend.write_tone(target, plan.tone["after"])
                    actual = self.backend.read_tone(target)
                    if not ramps_match(actual, plan.tone["after"]):
                        raise MonitorError("Driver não confirmou a curva SDR. Pode haver bloqueio ou outro app de cor.")
                    applied.append("tone_curve")
                except Exception as exc:
                    failed["tone_curve"] = str(exc)
            if plan.expected_target and not failed:
                final = self.snapshot(target, "tone_curve" in plan.expected_target,
                                      "color_preset" in plan.expected_target)
                for name, expected in plan.expected_target["values"].items():
                    if final["values"].get(name) != expected:
                        failed[name] = "O valor final não corresponde ao IPS. Confira o modo de imagem."
                        if name in applied:
                            applied.remove(name)
                if "tone_curve" in plan.expected_target:
                    if "tone_curve" not in final or not ramps_match(final["tone_curve"], plan.expected_target["tone_curve"]):
                        failed["tone_curve"] = "A curva final não corresponde à referência."
                        if "tone_curve" in applied:
                            applied.remove("tone_curve")
                if "color_preset" in plan.expected_target:
                    if final.get("color_preset", {}).get("current") != plan.expected_target["color_preset"]:
                        failed["color_preset"] = "Modo de cor final difere da referência."
            intended = [c.feature for c in plan.changes] + (["tone_curve"] if plan.tone else []) + (["color_preset"] if plan.color else [])
            return {"ok": not failed, "backup": str(backup), "applied": applied,
                    "failed": failed, "not_attempted": [name for name in intended
                    if name not in applied and name not in failed]}
