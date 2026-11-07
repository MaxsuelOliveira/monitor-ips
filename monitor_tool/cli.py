import argparse
import json
import sys

from .models import FEATURES, CONTROL_LABELS, MonitorError
from .service import Service
from .looks import STRENGTHS


def parser():
    p = argparse.ArgumentParser(description="Monitor IPS — comparação e ajustes DDC/CI no Windows.")
    p.add_argument("--demo", action="store_true", help="Simula dois monitores; não acessa hardware.")
    p.add_argument("--backup-dir", help="Pasta para backups automáticos.")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("gui", help="Abre a janela Electron (padrão).")
    sub.add_parser("gui-tk", help="Abre a janela Tkinter anterior (compatibilidade).")
    match = sub.add_parser("match", help="Iguala o destino à referência: valores nativos e curva SDR.")
    match.add_argument("--source", required=True)
    match.add_argument("--target", required=True)
    match.add_argument("--mode", choices=["exact", "relative"], default="exact")
    match.add_argument("--no-tone", action="store_true", help="Copia somente DDC, sem curva GPU.")
    match.add_argument("--color-mode", choices=["auto", "source", "user1", "user2"], default="auto",
                       help="auto usa modo Usuário para RGB editável quando necessário; source copia o preset literal.")
    match.add_argument("--yes", action="store_true")
    match.add_argument("--dry-run", action="store_true")
    ls = sub.add_parser("list", help="Lista monitores e lê os cinco controles permitidos.")
    ls.add_argument("--json", action="store_true", help="Saída estruturada.")
    backup = sub.add_parser("backup", help="Salva valores atuais em JSON.")
    backup.add_argument("--monitor", required=True)
    backup.add_argument("--output", help="Arquivo novo; nunca sobrescreve backups.")
    for cmd in ("compare", "apply"):
        child = sub.add_parser(cmd, help="Compara proporções dos controles." if cmd == "compare"
                               else "Copia proporções dos controles com backup automático.")
        child.add_argument("--source", required=True, help="ID do IPS selecionado por você.")
        child.add_argument("--target", required=True, help="ID do VA selecionado por você.")
        child.add_argument("--features", nargs="+", choices=list(FEATURES),
                           help="Padrão: todos os cinco controles.")
        if cmd == "apply":
            child.add_argument("--yes", action="store_true", help="Confirma a escrita sem pergunta.")
            child.add_argument("--dry-run", action="store_true", help="Só mostra a prévia.")
    fine = sub.add_parser("set", help="Ajusta controles em unidades nativas, ex.: brightness=35.")
    fine.add_argument("--monitor", required=True)
    fine.add_argument("values", nargs="+", metavar="CONTROLE=VALOR")
    tune = sub.add_parser("tune", help="Ajustes manuais de imagem e curva SDR opcional.")
    tune.add_argument("--monitor", required=True)
    for feature in FEATURES:
        tune.add_argument("--" + feature, type=int)
    tune.add_argument("--gamma", type=float, help="Meios-tons entre 0.85 e 1.15; substitui a curva GPU.")
    tune.add_argument("--black-point", type=float, help="Corte de sombras 0 a 4 (pode esconder detalhes).")
    diagnose = sub.add_parser("diagnose", help="Consulta faixa RGB NVIDIA, sem alterar o driver.")
    diagnose.add_argument("--monitor", required=True)
    restore = sub.add_parser("restore", help="Restaura backup do mesmo monitor/conexão.")
    restore.add_argument("--monitor", required=True)
    restore.add_argument("--file", required=True)
    oled = sub.add_parser("oled", help="Prepara/aplica Sabor OLED para um painel IPS ou VA (perfil estético SDR).")
    oled.add_argument("--monitor", required=True)
    oled.add_argument("--panel", required=True, choices=["ips", "va"])
    oled.add_argument("--strength", choices=list(STRENGTHS), default="balanced")
    oled.add_argument("--tone-curve", action="store_true",
                      help="Também substitui a curva GPU SDR; exige HDR desligado e cria backup da curva.")
    pattern = sub.add_parser("pattern", help="Abre padrão visual de sombras, realces e gradientes na tela escolhida.")
    pattern.add_argument("--monitor", required=True)
    for child in (fine, restore, oled, tune):
        child.add_argument("--yes", action="store_true")
        child.add_argument("--dry-run", action="store_true")
    return p


def parse_values(items):
    result = {}
    for item in items:
        try:
            name, value = item.split("=", 1)
            if name not in FEATURES or name in result:
                raise ValueError
            result[name] = int(value)
        except ValueError:
            raise MonitorError(f"Ajuste inválido: {item}. Use brightness=35, contrast=70, red=95, "
                               "green=90 ou blue=88, sem duplicar controles.") from None
    return result


def print_plan(plan):
    print(f"Destino: {plan.monitor['name']} [{plan.monitor['id']}]")
    for change in plan.changes:
        print(f"  {FEATURES[change.feature][1]}: {change.before} -> {change.after} / {change.maximum}")
    if plan.tone:
        print(f"  Curva SDR: {plan.tone['label']}")
    if plan.color:
        print(f"  Modo de cor: 0x{plan.color['before']:02X} -> 0x{plan.color['after']:02X}")
    if not plan.has_changes:
        print("Nenhuma alteração aplicável.")
    for name, reason in plan.skipped.items():
        print(f"  Ignorado — {CONTROL_LABELS.get(name, name)}: {reason}")
    for note in plan.notes:
        print(f"  Nota: {note}")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.demo:
            from .demo import DemoBackend
            backend = DemoBackend()
        else:
            from .windows import WindowsBackend
            backend = WindowsBackend()
        service = Service(backend, args.backup_dir)
        command = args.command or "gui"
        if command == "gui":
            from .desktop import launch
            return launch(args.demo, args.backup_dir)
        if command == "gui-tk":
            from .gui import launch
            launch(service)
            return 0
        if command == "pattern":
            from .patterns import launch_pattern
            with service.session() as monitors:
                monitor = service.find(monitors, args.monitor).public()
            launch_pattern(monitor)
            return 0
        if command == "diagnose":
            from .bridge import Bridge
            print(json.dumps(Bridge(service).dispatch("diagnostics", {"target": args.monitor}), ensure_ascii=False, indent=2))
            return 0
        if args.demo and not (command == "list" and args.json):
            print("DEMONSTRAÇÃO — nenhum monitor real será alterado; estado dura este processo.")
        if command == "list":
            data = service.inspect()
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                for item in data["monitors"]:
                    m = item["monitor"]
                    print(f"{m['id']} | {m['name']} | {m['device']}")
                    if not m["writable_identity"]:
                        print("  Escrita bloqueada: identificação física ambígua.")
                    for name in FEATURES:
                        v = item["values"].get(name)
                        print(f"  {FEATURES[name][1]}: " + (f"{v['current']}/{v['maximum']}" if v
                              else item["unavailable"].get(name, "Indisponível")))
                for warning in data["warnings"]:
                    print(f"Aviso: {warning}", file=sys.stderr)
                if not data["monitors"]:
                    print("Nenhum monitor DDC enumerado. Confira DDC/CI, cabo e sessão local.")
            return 0
        if command == "backup":
            print(service.backup(args.monitor, args.output))
            return 0
        if command == "match":
            plan = service.plan_match(args.source, args.target, args.mode, not args.no_tone, args.color_mode)
        elif command in ("compare", "apply"):
            plan = service.compare(args.source, args.target, args.features)
        elif command == "set":
            plan = service.plan_set(args.monitor, parse_values(args.values))
        elif command == "tune":
            values = {name: getattr(args, name) for name in FEATURES if getattr(args, name) is not None}
            tone = None if args.gamma is None and args.black_point is None else {"gamma": args.gamma if args.gamma is not None else 1.0, "black_point": args.black_point if args.black_point is not None else 0.0}
            plan = service.plan_visual(args.monitor, values, tone)
        elif command == "oled":
            plan = service.plan_oled(args.monitor, args.panel, args.strength, args.tone_curve)
        else:
            plan = service.plan_restore(args.monitor, args.file)
        print_plan(plan)
        if command == "compare" or args.dry_run or not plan.has_changes:
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise MonitorError("Escrita exige --yes em execução não interativa. Use --dry-run para revisar.")
            if input("Criar backup e aplicar? [s/N] ").strip().lower() not in ("s", "sim"):
                print("Cancelado; nenhum valor alterado.")
                return 0
        result = service.execute(plan)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["ok"]:
            print("Aplicação incompleta. Use o backup informado para restaurar.", file=sys.stderr)
            return 2
        return 0
    except (MonitorError, OSError, ImportError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido. Se havia uma escrita em andamento, confira os backups automáticos.", file=sys.stderr)
        return 130
