#!/usr/bin/env python3
"""
gitlight_windows.py — Gitlight en la bandeja del sistema (Windows)

Instala dependencias:
    pip install pystray pillow requests

Ejecutar:
    python gitlight_windows.py
"""

import json
import os
import sys
import threading
import time
import datetime

try:
    import pystray
    from pystray import MenuItem as Item, Menu
except ImportError:
    print("Falta la libreria 'pystray'. Instalala con:\n   pip install pystray pillow requests")
    input("Pulsa Enter para salir...")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Falta la libreria 'Pillow'. Instalala con:\n   pip install pystray pillow requests")
    input("Pulsa Enter para salir...")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Falta la libreria 'requests'. Instalala con:\n   pip install pystray pillow requests")
    input("Pulsa Enter para salir...")
    sys.exit(1)

# ── Configuracion ─────────────────────────────────────────────────────────────
CONFIG_PATH   = os.path.expanduser("~/.gitlight-config.json")
POLL_INTERVAL = 15        # segundos entre consultas
STALE_HOURS   = 8         # horas sin actividad -> libre

COLORS = {
    "free":  (34,  197, 94),    # verde
    "me":    (59,  130, 246),   # azul
    "other": (239, 68,  68),    # rojo
    "error": (156, 163, 175),   # gris
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Ejecuta primero setup_gist.py para configurar el semaforo.\n\nArchivo esperado:\n{CONFIG_PATH}",
            "Gitlight — Configuracion no encontrada",
            0x10
        )
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_icon(color_key):
    """Crea una imagen de 64x64 con un circulo de color."""
    size  = 64
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    color = COLORS.get(color_key, COLORS["error"])
    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline=(0, 0, 0, 80),
        width=2
    )
    return img


def api_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gitlight"
    }


def is_stale(since_str):
    if not since_str:
        return False
    try:
        since = datetime.datetime.fromisoformat(since_str.replace("Z", "+00:00"))
        now   = datetime.datetime.now(datetime.timezone.utc)
        return (now - since).total_seconds() > STALE_HOURS * 3600
    except Exception:
        return False


# ── App principal ─────────────────────────────────────────────────────────────

class SemaforoApp:

    def __init__(self):
        self.config     = load_config()
        self.is_working = False
        self._lock      = threading.Lock()

        # Estado inicial
        self._status_text = "Conectando..."
        self._color_key   = "error"

        # Crear el icono de bandeja
        self.icon = pystray.Icon(
            "gitlight",
            icon=make_icon("error"),
            title="Gitlight — conectando...",
            menu=self._build_menu()
        )

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        label = "Terminar de trabajar" if self.is_working else "Empezar a trabajar"
        return Menu(
            Item(lambda _: self._status_text, None, enabled=False),
            Menu.SEPARATOR,
            Item(label, self._toggle_work),
            Menu.SEPARATOR,
            Item("Salir", self._quit),
        )

    def _refresh_menu(self):
        self.icon.menu = self._build_menu()

    # ── Red ───────────────────────────────────────────────────────────────────

    def _get_remote_state(self):
        cfg  = self.config
        resp = requests.get(
            f"https://api.github.com/gists/{cfg['gist_id']}",
            headers=api_headers(cfg["github_token"]),
            timeout=8
        )
        resp.raise_for_status()
        content = resp.json()["files"]["status.json"]["content"]
        data    = json.loads(content)
        return data.get("worker"), data.get("since")

    def _set_remote_state(self, username):
        cfg   = self.config
        since = datetime.datetime.now(datetime.timezone.utc).isoformat() if username else None
        payload = {
            "files": {
                "status.json": {
                    "content": json.dumps({"worker": username, "since": since}, indent=2)
                }
            }
        }
        resp = requests.patch(
            f"https://api.github.com/gists/{cfg['gist_id']}",
            headers=api_headers(cfg["github_token"]),
            json=payload,
            timeout=8
        )
        resp.raise_for_status()

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll_loop(self):
        while True:
            self._poll_once()
            time.sleep(POLL_INTERVAL)

    def _poll_once(self):
        try:
            worker, since = self._get_remote_state()
        except Exception as e:
            with self._lock:
                self._status_text = f"Sin conexion ({type(e).__name__})"
                self._color_key   = "error"
            self.icon.icon  = make_icon("error")
            self.icon.title = "Gitlight — sin conexion"
            return

        my_user = self.config["my_username"]

        if worker and is_stale(since):
            worker = None

        with self._lock:
            if worker is None:
                self._status_text = "Libre — nadie esta trabajando"
                self._color_key   = "free"
                self.icon.icon    = make_icon("free")
                self.icon.title   = "Gitlight — Libre"
                if not self.is_working:
                    self._refresh_menu()
            elif worker == my_user:
                self._status_text = "Tu estas trabajando"
                self._color_key   = "me"
                self.icon.icon    = make_icon("me")
                self.icon.title   = "Gitlight — Tu estas trabajando"
            else:
                self._status_text = f"{worker} esta trabajando — espera!"
                self._color_key   = "other"
                self.icon.icon    = make_icon("other")
                self.icon.title   = f"Gitlight — {worker} esta trabajando"
                if not self.is_working:
                    self._refresh_menu()

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _toggle_work(self, icon, item):
        my_user = self.config["my_username"]
        try:
            with self._lock:
                if not self.is_working:
                    self._set_remote_state(my_user)
                    self.is_working   = True
                    self._status_text = "Tu estas trabajando"
                    self._color_key   = "me"
                    self.icon.icon    = make_icon("me")
                    self.icon.title   = "Gitlight — Tu estas trabajando"
                else:
                    self._set_remote_state(None)
                    self.is_working   = False
                    self._status_text = "Libre — nadie esta trabajando"
                    self._color_key   = "free"
                    self.icon.icon    = make_icon("free")
                    self.icon.title   = "Gitlight — Libre"
            self._refresh_menu()
        except Exception as e:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(e), "Error al actualizar estado", 0x10)

    def _quit(self, icon, item):
        if self.is_working:
            try:
                self._set_remote_state(None)
            except Exception:
                pass
        icon.stop()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        self.icon.run()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SemaforoApp().run()
