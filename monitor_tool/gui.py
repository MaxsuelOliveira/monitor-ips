"""Janela Tkinter. Apenas a thread principal toca nos widgets."""
import queue
import json
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .models import FEATURES, MonitorError
from .cli import parse_values
from .looks import STRENGTHS


def enable_dpi_awareness():
    """Evita virtualização de coordenadas/fontes no Windows com escala de tela."""
    import sys
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        user = ctypes.WinDLL("user32", use_last_error=True)
        try:
            function = user.SetProcessDpiAwarenessContext
            function.argtypes = [wintypes.HANDLE]
            function.restype = wintypes.BOOL
            function(wintypes.HANDLE(-4))  # PER_MONITOR_AWARE_V2
        except AttributeError:
            user.SetProcessDPIAware()


class App:
    def __init__(self, root, service):
        self.root, self.service = root, service
        self.busy = False
        self.events = queue.Queue()
        self.plan = None
        self.profiles = []
        self.ids = []
        self.controls = []
        self.worker = None
        self.roles = {"demo-ips": "ips", "demo-va": "va"} if service.backend.demo else {}
        if not service.backend.demo:
            path = Path(__file__).resolve().parents[1] / "monitor_roles.json"
            if path.exists():
                try:
                    roles = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(roles, dict):
                        self.roles = {k: v for k, v in roles.items()
                                      if isinstance(k, str) and v in ("ips", "va")}
                except (OSError, ValueError):
                    pass  # Sem classificação: exigir escolha explícita no perfil.
        self.root.title("Monitor IPS" + (" — Demonstração" if service.backend.demo else ""))
        width = min(1120, root.winfo_screenwidth() - 80)
        height = min(900, root.winfo_screenheight() - 100)
        self.root.geometry(f"{width}x{height}+30+30")
        self.root.minsize(min(900, width), min(650, height))
        self.root.configure(background="#f5f5f5")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#f5f5f5", foreground="#202020")
        style.configure("TButton", padding=(12, 7))
        style.configure("Primary.TButton", background="#262626", foreground="white")
        style.map("Primary.TButton", background=[("disabled", "#dedede"), ("active", "#404040")],
                  foreground=[("disabled", "#777777")])
        style.configure("Treeview", background="white", fieldbackground="white", rowheight=35)
        style.configure("Treeview.Heading", background="#f5f5f5", font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", "#dddddd")], foreground=[("selected", "#202020")])
        # A rolagem mantém ações e logs acessíveis em telas pequenas e escala alta.
        canvas = tk.Canvas(root, background="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(canvas, padding=20)
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        root.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units")
                  if not isinstance(event.widget, (tk.Text, ttk.Treeview, ttk.Combobox)) else None)
        self.canvas = canvas
        body.columnconfigure(0, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Monitor IPS", font=("Segoe UI", 21, "bold")).pack(side="left")
        self.button(header, "Atualizar monitores", self.refresh).pack(side="right")
        notice = ("DEMONSTRAÇÃO • Monitores simulados. Nenhuma alteração no hardware."
                  if service.backend.demo else "DDC/CI • Copie ajustes ou prepare um perfil Sabor OLED para cada tela.")
        ttk.Label(body, text=notice).grid(row=1, column=0, sticky="w", pady=(4, 18))
        selectors = ttk.Frame(body)
        selectors.grid(row=2, column=0, sticky="ew")
        selectors.columnconfigure((0, 1), weight=1, uniform="monitor")
        self.source = ttk.Combobox(selectors, state="readonly", width=28)
        self.target = ttk.Combobox(selectors, state="readonly", width=28)
        for col, (label, combo) in enumerate((("Origem / referência para cópia", self.source),
                                             ("Destino / monitor a ajustar", self.target))):
            ttk.Label(selectors, text=label).grid(row=0, column=col, sticky="w", padx=(0, 12))
            combo.grid(row=1, column=col, sticky="ew", padx=(0, 12), pady=(5, 12))
            combo.bind("<<ComboboxSelected>>", self.selection_changed)
            self.controls.append(combo)
        self.tree = ttk.Treeview(body, columns=("control", "source", "target", "planned"),
                                 show="headings", height=5, selectmode="none")
        for key, title, width in (("control", "Controle", 200), ("source", "Origem / máximo", 170),
                                  ("target", "Destino / máximo", 170), ("planned", "Prévia no destino", 190)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w" if key == "control" else "e")
        self.tree.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(body, text="Controles para copiar e ajustes manuais", font=("Segoe UI", 11, "bold")).grid(
            row=4, column=0, sticky="w")
        form = ttk.Frame(body)
        form.grid(row=5, column=0, sticky="ew", pady=8)
        self.selected, self.entries = {}, {}
        for col, (name, (_, label)) in enumerate(FEATURES.items()):
            form.columnconfigure(col, weight=1, uniform="value")
            var = tk.BooleanVar(value=True)
            check = ttk.Checkbutton(form, text=label, variable=var, command=self.invalidate)
            check.grid(row=0, column=col, sticky="w", padx=(0, 6))
            entry_var = tk.StringVar()
            entry = ttk.Entry(form, textvariable=entry_var, width=10)
            entry.grid(row=1, column=col, sticky="ew", padx=(0, 10), pady=5)
            entry_var.trace_add("write", lambda *_: self.invalidate())
            self.selected[name], self.entries[name] = var, entry_var
            self.controls.extend([check, entry])
        ttk.Label(body, text="Valores manuais: de 0 ao máximo mostrado. Controles indisponíveis ficam vazios.",
                  wraplength=760).grid(row=6, column=0, sticky="w")
        look = ttk.LabelFrame(body, text="Sabor OLED • Perfil visual SDR", padding=10)
        look.grid(row=7, column=0, sticky="ew", pady=(8, 0))
        self.panel = ttk.Combobox(look, state="readonly", values=("IPS", "VA"), width=6)
        self.panel.set("")
        self.strength = ttk.Combobox(look, state="readonly", values=[v["label"] for v in STRENGTHS.values()], width=13)
        self.strength.current(1)
        ttk.Label(look, text="Painel do destino").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(look, text="Intensidade").grid(row=0, column=1, sticky="w", padx=(0, 10))
        self.panel.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.strength.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.use_tone = tk.BooleanVar(value=True)
        tone_check = ttk.Checkbutton(look, text="Curva SDR: substituir curva GPU atual", variable=self.use_tone,
                                     command=self.invalidate)
        tone_check.grid(row=1, column=2, sticky="w", padx=(0, 10))
        look.columnconfigure(2, weight=1)
        self.button(look, "Preparar Sabor OLED", self.prepare_oled).grid(row=1, column=3, sticky="e")
        ttk.Label(look, text="Menos luz de fundo e meios-tons mais profundos; contraste e RGB preservados. "
                  "HDR bloqueia a curva. Não é calibração medida.", wraplength=900).grid(
                      row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.panel.bind("<<ComboboxSelected>>", lambda _: self.invalidate())
        self.strength.bind("<<ComboboxSelected>>", lambda _: self.invalidate())
        self.controls.extend([self.panel, self.strength, tone_check])
        actions = ttk.Frame(body)
        actions.grid(row=8, column=0, sticky="ew", pady=(14, 8))
        self.button(actions, "Comparar / preparar cópia", self.prepare_copy).pack(side="left", padx=(0, 8))
        self.button(actions, "Preparar ajustes manuais", self.prepare_manual).pack(side="left", padx=(0, 8))
        self.apply_button = self.button(actions, "Aplicar prévia…", self.apply, style="Primary.TButton")
        self.apply_button.pack(side="right")
        backups = ttk.Frame(body)
        backups.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        self.button(backups, "Backup do destino…", self.backup).pack(side="left", padx=(0, 8))
        self.button(backups, "Restaurar backup…", self.restore).pack(side="left")
        self.button(backups, "Teste visual no destino", self.pattern).pack(side="right")
        self.status = tk.StringVar(value="Pronto para ler monitores.")
        ttk.Label(body, textvariable=self.status, wraplength=900).grid(row=10, column=0, sticky="w", pady=6)
        log_frame = ttk.Frame(body)
        log_frame.grid(row=11, column=0, sticky="nsew")
        body.rowconfigure(11, weight=1)
        self.log = tk.Text(log_frame, height=4, wrap="word", background="white", foreground="#202020",
                           font=("Segoe UI", 10), relief="solid", borderwidth=1, state="disabled")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        ttk.Label(body, text="A cópia usa proporções dos controles; não calibra cores. "
                  "O perfil Sabor OLED é uma aproximação estética, sem o preto físico de um OLED.", wraplength=900).grid(
                      row=12, column=0, sticky="w", pady=(10, 0))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(70, self.poll)
        self.refresh()

    def button(self, parent, text, command, **kwargs):
        widget = ttk.Button(parent, text=text, command=command, **kwargs)
        self.controls.append(widget)
        return widget

    def append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", str(text) + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def invalidate(self):
        self.plan = None
        self.apply_button.configure(state="disabled")
        for row in self.tree.get_children():
            self.tree.set(row, "planned", "—")

    def run(self, label, work, done):
        if self.busy:
            return
        self.busy = True
        self.status.set(label)
        for control in self.controls:
            control.configure(state="disabled")

        def worker():
            try:
                self.events.put((done, work(), None))
            except Exception as exc:
                self.events.put((done, None, exc))

        self.worker = threading.Thread(target=worker, name="monitor-ips-ddc", daemon=False)
        self.worker.start()

    def poll(self):
        try:
            done, value, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.worker.join()
            self.busy = False
            for control in self.controls:
                control.configure(state="readonly" if isinstance(control, ttk.Combobox) else "normal")
            if error:
                self.status.set("Operação não concluída. Veja o detalhe abaixo.")
                self.append(error)
                messagebox.showerror("Monitor IPS", str(error), parent=self.root)
            else:
                self.status.set("Leitura/operação concluída.")
                done(value)
            self.apply_button.configure(state="normal" if self.plan and self.plan.has_changes else "disabled")
        self.root.after(70, self.poll)

    def monitor_id(self, combo):
        index = combo.current()
        if index < 0 or index >= len(self.ids):
            raise MonitorError("Selecione um monitor disponível.")
        return self.ids[index]

    def guard(self, action):
        try:
            action()
        except (MonitorError, ValueError) as exc:
            messagebox.showerror("Monitor IPS", str(exc), parent=self.root)

    def refresh(self):
        self.invalidate()
        self.run("Lendo monitores e controles DDC/CI…", self.service.inspect, self.loaded)

    def loaded(self, data):
        old_source, old_target = self.source.get(), self.target.get()
        self.profiles = data["monitors"]
        self.ids = [p["monitor"]["id"] for p in self.profiles]
        labels = [f"{self.roles.get(p['monitor']['id'], '?').upper()} | {p['monitor']['name']} | "
                  f"{p['monitor']['device']} | {p['monitor']['id']}"
                  for p in self.profiles]
        ips = next((i for i, mid in enumerate(self.ids) if self.roles.get(mid) == "ips"), 0)
        va = next((i for i, mid in enumerate(self.ids) if self.roles.get(mid) == "va"), min(1, len(labels) - 1))
        for combo, previous, default in ((self.source, old_source, ips), (self.target, old_target, va)):
            combo.configure(values=labels)
            if labels:
                combo.current(labels.index(previous) if previous in labels else min(default, len(labels) - 1))
            else:
                combo.set("")
        self.selection_changed()
        self.status.set(f"{len(labels)} monitor(es) enumerado(s). Escolha a origem e o destino antes de preparar.")
        if not labels:
            self.append("Nenhum monitor DDC disponível. Ative DDC/CI no menu, confira o cabo e use uma sessão local.")
        for warning in data["warnings"]:
            self.append(warning)
        for profile in self.profiles:
            if not profile["monitor"]["writable_identity"]:
                self.append(f"{profile['monitor']['name']}: identificação ambígua; escrita bloqueada.")
            for name, reason in profile["unavailable"].items():
                self.append(f"{profile['monitor']['name']} / {FEATURES[name][1]}: {reason}")

    def selection_changed(self, _event=None):
        self.invalidate()
        self.tree.delete(*self.tree.get_children())
        source = self.profiles[self.source.current()]["values"] if self.source.current() >= 0 else {}
        target = self.profiles[self.target.current()]["values"] if self.target.current() >= 0 else {}
        target_id = self.ids[self.target.current()] if self.target.current() >= 0 else None
        self.panel.set(self.roles.get(target_id, "").upper())
        for name, (_, label) in FEATURES.items():
            def formatted(values):
                v = values.get(name)
                return f"{v['current']} / {v['maximum']}" if v else "Indisponível"
            self.tree.insert("", "end", iid=name, values=(label, formatted(source), formatted(target), "—"))
            self.entries[name].set(str(target[name]["current"]) if name in target else "")

    def show_plan(self, plan):
        self.plan = plan
        for change in plan.changes:
            self.tree.set(change.feature, "target", f"{change.before} / {change.maximum}")
            self.tree.set(change.feature, "planned", f"{change.before} → {change.after} / {change.maximum}")
        for name, reason in plan.skipped.items():
            self.tree.set(name, "planned", "Ignorado")
            self.append(f"{FEATURES[name][1]} ignorado: {reason}")
        if plan.tone:
            self.append(f"Curva SDR na prévia: {plan.tone['label']}")
        for note in plan.notes:
            self.append(note)
        count = len(plan.changes) + bool(plan.tone)
        self.status.set(f"Prévia: {count} alteração(ões) em {plan.monitor['name']}. "
                        "Confira a tabela e clique em Aplicar prévia.")

    def prepare_oled(self):
        def start():
            target = self.monitor_id(self.target)
            panel = self.panel.get().lower()
            if panel not in ("ips", "va"):
                raise MonitorError("Escolha se o monitor de destino é IPS ou VA.")
            self.roles[target] = panel
            strength = list(STRENGTHS)[self.strength.current()]
            use_tone = self.use_tone.get()
            self.invalidate()
            self.run("Preparando Sabor OLED e verificando SDR…",
                     lambda: self.service.plan_oled(target, panel, strength, use_tone), self.show_plan)
        self.guard(start)

    def pattern(self):
        def start():
            target = self.monitor_id(self.target)
            from .patterns import show_pattern
            profile = next(p for p in self.profiles if p["monitor"]["id"] == target)
            show_pattern(self.root, profile["monitor"])
        self.guard(start)

    def prepare_copy(self):
        def start():
            source, target = self.monitor_id(self.source), self.monitor_id(self.target)
            names = [n for n, var in self.selected.items() if var.get()]
            self.invalidate()
            self.run("Comparando valores atuais…", lambda: self.service.compare(source, target, names), self.show_plan)
        self.guard(start)

    def prepare_manual(self):
        def start():
            target = self.monitor_id(self.target)
            items = [f"{name}={self.entries[name].get()}" for name, var in self.selected.items()
                     if var.get() and self.entries[name].get().strip()]
            values = parse_values(items)
            if not values:
                raise MonitorError("Preencha ao menos um controle selecionado.")
            self.invalidate()
            self.run("Preparando ajustes manuais…", lambda: self.service.plan_set(target, values), self.show_plan)
        self.guard(start)

    def apply(self):
        if not self.plan or not self.plan.has_changes or self.busy:
            return
        plan = self.plan
        lines = [f"{FEATURES[c.feature][1]}: {c.before} → {c.after}" for c in plan.changes]
        if plan.tone:
            lines.append("Curva GPU SDR: " + plan.tone["label"])
            lines.append("Substitui a curva GPU atual. O backup permitirá restaurá-la.")
        if not messagebox.askyesno("Aplicar no destino?", f"{plan.monitor['name']} [{plan.monitor['id']}]\n\n"
                                  + "\n".join(lines) + "\n\nUm backup automático será salvo antes da alteração.",
                                  parent=self.root):
            return
        self.invalidate()
        self.run("Salvando backup e aplicando ajustes…", lambda: self.service.execute(plan), self.applied)

    def applied(self, result):
        self.append(f"Backup automático: {result['backup']}")
        self.append("Controles verificados: " + (", ".join(result["applied"]) or "nenhum"))
        if not result["ok"]:
            for name, error in result["failed"].items():
                label = FEATURES[name][1] if name in FEATURES else "Curva GPU SDR"
                self.append(f"Falha em {label}: {error}")
            messagebox.showwarning("Aplicação incompleta", "A aplicação parou após uma falha. "
                                   "O controle que falhou pode ter mudado. Veja o log e restaure o backup se necessário.",
                                   parent=self.root)
        self.refresh()

    def backup(self):
        def start():
            target = self.monitor_id(self.target)
            path = filedialog.asksaveasfilename(parent=self.root, title="Salvar backup do destino",
                                                defaultextension=".json", filetypes=[("Backup JSON", "*.json")])
            if path:
                self.run("Salvando backup…", lambda: self.service.backup(target, path),
                         lambda saved: self.append(f"Backup salvo: {saved}"))
        self.guard(start)

    def restore(self):
        def start():
            target = self.monitor_id(self.target)
            path = filedialog.askopenfilename(parent=self.root, title="Restaurar backup do destino",
                                              initialdir=str(self.service.backups),
                                              filetypes=[("Backup JSON", "*.json")])
            if path:
                self.invalidate()
                self.run("Validando backup e preparando restauração…",
                         lambda: self.service.plan_restore(target, path), self.show_plan)
        self.guard(start)

    def close(self):
        if self.busy:
            messagebox.showinfo("Operação em andamento", "Aguarde a operação terminar antes de fechar.", parent=self.root)
            return
        self.root.destroy()


def launch(service):
    enable_dpi_awareness()
    root = tk.Tk()
    App(root, service)
    root.mainloop()
