"""Padrão visual estático: não modifica configurações de vídeo."""
import sys
import tkinter as tk

SHADOWS = (0, 1, 2, 4, 8, 12, 16, 24, 32)
HIGHLIGHTS = (224, 232, 240, 244, 248, 252, 254, 255)


def gray(value):
    return f"#{value:02x}{value:02x}{value:02x}"


def show_pattern(root, monitor):
    window = tk.Toplevel(root)
    window.title(f"Teste visual — {monitor['name']}")
    window.configure(background="#161616")
    bounds = monitor.get("bounds")
    width, height = ((bounds[2] - bounds[0], bounds[3] - bounds[1]) if bounds else (1000, 720))
    window.geometry(f"{width}x{height}+0+0")
    if bounds:
        window.overrideredirect(True)
    canvas = tk.Canvas(window, highlightthickness=0, background="#161616")
    canvas.pack(fill="both", expand=True)

    def render(event):
        w, h = event.width, event.height
        canvas.delete("all")
        pad = max(24, w // 35)
        canvas.create_text(pad, 30, text=f"Sabor OLED • Teste visual • {monitor['name']}",
                           fill="white", anchor="nw", font=("Segoe UI", 17, "bold"))
        canvas.create_text(pad, 74, text="Compare de frente, com a mesma luz ambiente. "
                           "Procure distinguir os degraus sem perder detalhes. Esc fecha.",
                           fill="#cccccc", anchor="nw", font=("Segoe UI", 11), width=w - 2 * pad)
        strips = ((SHADOWS, "Sombras — os valores 8, 12, 16 e 24 devem se separar do preto", 0.22),
                  (HIGHLIGHTS, "Realces — confira a separação entre 240, 248 e branco", 0.45))
        for values, title, fraction in strips:
            y = h * fraction
            canvas.create_text(pad, y - 30, text=title, fill="white", anchor="nw", font=("Segoe UI", 12))
            cell = (w - 2 * pad) / len(values)
            for index, value in enumerate(values):
                x = pad + index * cell
                canvas.create_rectangle(x, y, x + cell + 1, y + h * .12, fill=gray(value), outline="")
                canvas.create_text(x + cell / 2, y + h * .12 + 15, text=str(value), fill="#cccccc",
                                   font=("Segoe UI", 10))
        y = h * .71
        canvas.create_text(pad, y - 30, text="Gradiente neutro — observe faixas e dominantes de cor",
                           fill="white", anchor="nw", font=("Segoe UI", 12))
        cell = (w - 2 * pad) / 256
        for value in range(256):
            x = pad + value * cell
            canvas.create_rectangle(x, y, x + cell + 1, y + h * .1, fill=gray(value), outline="")
        canvas.create_text(pad, h - 60, text="Esta tela ajuda no ajuste visual. Não mede cores, "
                           "não certifica calibração e não reproduz o preto físico de um OLED.",
                           fill="#cccccc", anchor="nw", font=("Segoe UI", 11), width=w - 180)

    canvas.bind("<Configure>", render)
    tk.Button(window, text="Fechar (Esc)", command=window.destroy, padx=15, pady=6).place(
        relx=1, x=-20, y=20, anchor="ne")
    window.bind("<Escape>", lambda _: window.destroy())
    window.update_idletasks()
    if bounds and sys.platform == "win32":
        import ctypes as C
        from ctypes import wintypes as W
        user = C.WinDLL("user32", use_last_error=True)
        user.GetAncestor.argtypes, user.GetAncestor.restype = [W.HWND, W.UINT], W.HWND
        user.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
        user.SetWindowPos.restype = W.BOOL
        hwnd = user.GetAncestor(window.winfo_id(), 2)
        if not user.SetWindowPos(hwnd, None, bounds[0], bounds[1], width, height, 0x0040):
            window.overrideredirect(False)
    window.focus_set()
    return window


def launch_pattern(monitor):
    from .gui import enable_dpi_awareness
    enable_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    try:
        window = show_pattern(root, monitor)
        root.wait_window(window)
    finally:
        root.destroy()
