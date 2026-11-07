"""RPC local via stdin/stdout. Não abre porta e não aceita código/comandos de shell."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import uuid

from .models import FEATURES, MonitorError
from .service import Service


class Bridge:
    def __init__(self, service):
        self.service = service
        self.pending = {}
        self.last_backups = {}

    def state(self):
        data = self.service.inspect(include_tone=True)
        roles = {"demo-ips": "ips", "demo-va": "va"} if self.service.backend.demo else {}
        roles_file = Path(__file__).resolve().parents[1] / "monitor_roles.json"
        if not self.service.backend.demo and roles_file.exists():
            try:
                loaded = json.loads(roles_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    roles = {key: value for key, value in loaded.items() if value in ("ips", "va")}
            except (OSError, ValueError):
                pass
        data["roles"] = roles
        from .presets import catalog
        data["presets"] = catalog()
        data["backup_dir"] = str(self.service.backups.resolve())
        for profile in data["monitors"]:
            profile["tone_available"] = "tone_curve" in profile
            profile["can_undo"] = profile["monitor"]["id"] in self.last_backups
        return data

    def preview(self, plan):
        self.pending.clear()
        token = uuid.uuid4().hex
        self.pending[token] = plan
        return {"token": token, "monitor": plan.monitor,
                "changes": [asdict(c) for c in plan.changes], "skipped": plan.skipped,
                "tone": plan.tone["label"] if plan.tone else None,
                "color": plan.color,
                "color_target": plan.expected_target.get("color_preset") if plan.expected_target else None,
                "notes": plan.notes, "has_changes": plan.has_changes}

    def dispatch(self, method, params):
        if not isinstance(params, dict):
            raise MonitorError("Parâmetros inválidos.")
        if method == "state":
            return self.state()
        if method == "preview_match":
            return self.preview(self.service.plan_match(params["source"], params["target"],
                                 params.get("mode", "exact"), params.get("tone", True), params.get("color_mode", "auto")))
        if method == "preview_set":
            return self.preview(self.service.plan_set(params["target"], params["values"]))
        if method == "preview_visual":
            return self.preview(self.service.plan_visual(params["target"], params.get("values", {}), params.get("tone")))
        if method == "preview_preset":
            return self.preview(self.service.plan_preset(params["target"], params["preset"], params["panel"],
                                                        params.get("tone", True), params.get("brightness")))
        if method == "preview_undo":
            path = self.last_backups.get(params["target"])
            if not path:
                raise MonitorError("Nenhum ajuste desta sessão para desfazer neste monitor.")
            return self.preview(self.service.plan_restore(params["target"], path))
        if method == "diagnostics":
            with self.service.session() as monitors:
                monitor = self.service.find(monitors, params["target"])
                if self.service.backend.demo:
                    output = {"vendor": "NVIDIA (simulado)", "format": "RGB", "range": "full", "bits": 8, "read_only": True}
                else:
                    from .diagnostics import nvidia_output
                    try:
                        output = nvidia_output(monitor.device)
                    except MonitorError as exc:
                        output = {"range": "unknown", "error": str(exc), "read_only": True}
                return {"monitor": monitor.public(), "output": output,
                        "physical_black": "Não mensurado. Capturas de tela não medem a luz do painel."}
        if method == "preview_restore":
            return self.preview(self.service.plan_restore(params["target"], params["path"]))
        if method == "apply":
            plan = self.pending.pop(params["token"], None)
            if not plan:
                raise MonitorError("Prévia expirada. Compare novamente.")
            result = self.service.execute(plan)
            if result.get("backup"):
                self.last_backups[plan.monitor["id"]] = result["backup"]
            return result
        if method == "backup":
            return {"path": str(self.service.backup(params["target"], params.get("path")))}
        if method == "discard":
            self.pending.clear()
            return {"ok": True}
        raise MonitorError("Operação não permitida.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if args.demo:
        from .demo import DemoBackend
        backend = DemoBackend()
    else:
        from .windows import WindowsBackend
        backend = WindowsBackend()
    bridge = Bridge(Service(backend, args.backup_dir))
    for line in sys.stdin:
        request_id = None
        try:
            if len(line) > 1_000_000:
                raise MonitorError("Requisição muito grande.")
            request = json.loads(line)
            request_id = request["id"]
            result = bridge.dispatch(request["method"], request.get("params", {}))
            response = {"id": request_id, "result": result}
        except Exception as exc:
            response = {"id": request_id, "error": str(exc)}
        print(json.dumps(response, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
