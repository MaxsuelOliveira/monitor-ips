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

    @property
    def has_changes(self):
        return bool(self.changes or self.tone)

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
        if (not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] not in (1, 2)
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
        if data["schema"] == 2:
            validate_ramp(data.get("tone_curve"))
        elif "tone_curve" in data:
            raise MonitorError("Backup de curva SDR exige schema 2.")
        if not data["values"] and "tone_curve" not in data:
            raise MonitorError("Backup vazio: nenhum controle ou curva SDR.")
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

    def snapshot(self, monitor, include_tone=False):
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
        return profile

    def inspect(self):
        with self.session() as monitors:
            profiles = [self.snapshot(m) for m in monitors]
            return {"demo": self.backend.demo, "monitors": profiles,
                    "warnings": list(getattr(self.backend, "warnings", []))}

    def backup(self, monitor_id, path=None):
        with self.session() as monitors:
            monitor = self.find(monitors, monitor_id)
            profile = self.snapshot(monitor, include_tone=True)
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
            return Plan(target.public(), changes, {}, self.backend.demo, tone, notes)

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
            profile = self.snapshot(target, include_tone=True)
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
            if not plan.has_changes:
                return {"ok": True, "backup": None, "applied": [], "failed": {}}
            # Salvar e confirmar o fechamento do arquivo antes da primeira escrita DDC.
            backup = save_json(self.new_backup_path(target.id), profile)
            applied, failed = [], {}
            for change in plan.changes:
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
                for change in plan.changes:
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
            intended = [c.feature for c in plan.changes] + (["tone_curve"] if plan.tone else [])
            return {"ok": not failed, "backup": str(backup), "applied": applied,
                    "failed": failed, "not_attempted": [name for name in intended
                    if name not in applied and name not in failed]}
