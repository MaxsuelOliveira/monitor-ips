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
                bbox = (root.winfo_rootx(), root.winfo_rooty(),
                        root.winfo_rootx() + root.winfo_width(), root.winfo_rooty() + root.winfo_height())
                ImageGrab.grab(bbox=bbox, all_screens=True).save(output / "gui-demo.png")
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
            root.geometry("850x720")
            root.update()
            assert app.log.winfo_height() > 35
            app.canvas.yview_moveto(1)
            root.update()
            assert app.canvas.yview()[1] > 0.99
            assert not app.worker.is_alive()
            print("GUI OK: leitura, comparação, aplicação, restauração, ajuste manual, "
                  "invalidação da prévia, tamanho mínimo e worker encerrado.")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
