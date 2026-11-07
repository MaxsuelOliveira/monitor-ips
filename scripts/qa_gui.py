"""QA de janela nativa, sem hardware. Não deixa processo ou janela ativo."""
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor_tool.demo import DemoBackend
from monitor_tool.gui import App, enable_dpi_awareness
from monitor_tool.service import Service


def wait(root, app):
    deadline = time.monotonic() + 10
    while app.busy:
        if time.monotonic() > deadline:
            raise RuntimeError("Worker de demonstração não terminou")
        root.update()
        time.sleep(0.02)
    root.update()


def capture(window, path):
    """Captura somente o HWND próprio, mesmo com outro app em primeiro plano."""
    from PIL import ImageGrab
    import ctypes as C
    from ctypes import wintypes as W
    window.update_idletasks()
    user = C.WinDLL("user32", use_last_error=True)
    user.GetAncestor.argtypes, user.GetAncestor.restype = [W.HWND, W.UINT], W.HWND
    hwnd = user.GetAncestor(window.winfo_id(), 2)
    ImageGrab.grab(window=hwnd).save(path)


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    try:
        with tempfile.TemporaryDirectory() as folder:
            service = Service(DemoBackend(), folder)
            app = App(root, service)
            wait(root, app)
            assert len(app.ids) == 2
            assert app.tree.set("brightness", "target") == "140 / 200"
            app.prepare_copy()
            wait(root, app)
            assert app.plan.changes
            assert app.tree.set("brightness", "planned") == "140 → 70 / 200"
            assert app.apply_button["state"] != "disabled"
            root.update_idletasks()
            output = Path(__file__).resolve().parents[1] / "output"
            output.mkdir(exist_ok=True)
            try:
                from PIL import ImageGrab
            except ImportError:
                print("Pillow indisponível: screenshot opcional não capturada.")
            else:
                capture(root, output / "gui-demo.png")
            with patch("monitor_tool.gui.messagebox.askyesno", return_value=True):
                app.apply()
            wait(root, app)
            assert service.backend.values["demo-va"]["brightness"].current == 70
            backups = list(Path(folder).glob("*.json"))
            assert len(backups) == 1
            with patch("monitor_tool.gui.filedialog.askopenfilename", return_value=str(backups[0])):
                app.restore()
            wait(root, app)
            with patch("monitor_tool.gui.messagebox.askyesno", return_value=True):
                app.apply()
            wait(root, app)
            assert service.backend.values["demo-va"]["brightness"].current == 140
            app.entries["brightness"].set("60")
            app.prepare_manual()
            wait(root, app)
            assert any(c.feature == "brightness" and c.after == 60 for c in app.plan.changes)
            app.source.current(1)
            app.selection_changed()
            assert app.plan is None
            app.target.current(0)
            app.selection_changed()
            assert app.panel.get() == "IPS"
            app.prepare_oled()
            wait(root, app)
            assert app.plan.tone
            assert app.plan.has_changes
            with patch("monitor_tool.gui.messagebox.askyesno", return_value=True):
                app.apply()
            wait(root, app)
            assert service.backend.values["demo-ips"]["brightness"].current == 22
            from monitor_tool.looks import oled_ramp
            assert service.backend.tones["demo-ips"] == oled_ramp("ips", "balanced")
            previous_windows = set(root.winfo_children())
            app.pattern()
            root.update()
            created = [w for w in root.winfo_children() if w not in previous_windows]
            assert len(created) == 1
            pattern_window = created[0]
            root.update_idletasks()
            if "ImageGrab" in locals():
                capture(pattern_window, output / "pattern-demo.png")
            pattern_window.destroy()
            app.prepare_oled()
            wait(root, app)
            assert not app.plan.has_changes
            root.geometry("850x720")
            root.update()
            assert app.log.winfo_height() > 35
            app.canvas.yview_moveto(1)
            root.update()
            assert app.canvas.yview()[1] > 0.99
            assert not app.worker.is_alive()
            print("GUI OK: cópia/restauração DDC, ajustes manuais, Sabor OLED com curva, "
                  "idempotência, padrão visual fechado, tamanho mínimo e worker encerrado.")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
