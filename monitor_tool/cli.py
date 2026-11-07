import argparse
import json
import sys

from .models import FEATURES, MonitorError
from .service import Service


def parser():
    p = argparse.ArgumentParser(description="Monitor IPS — comparação e ajustes DDC/CI no Windows.")
    p.add_argument("--demo", action="store_true", help="Simula dois monitores; não acessa hardware.")
    p.add_argument("--backup-dir", help="Pasta para backups automáticos.")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("gui", help="Abre a janela (padrão quando nenhum comando é informado).")
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
    restore = sub.add_parser("restore", help="Restaura backup do mesmo monitor/conexão.")
    restore.add_argument("--monitor", required=True)
    restore.add_argument("--file", required=True)
    for child in (fine, restore):
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
    if not plan.changes:
        print("Nenhuma alteração aplicável.")
    for name, reason in plan.skipped.items():
        print(f"  Ignorado — {FEATURES[name][1]}: {reason}")


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
            from .gui import launch
            launch(service)
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
        if command in ("compare", "apply"):
            plan = service.compare(args.source, args.target, args.features)
        elif command == "set":
            plan = service.plan_set(args.monitor, parse_values(args.values))
        else:
            plan = service.plan_restore(args.monitor, args.file)
        print_plan(plan)
        if command == "compare" or args.dry_run or not plan.changes:
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
