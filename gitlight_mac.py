#!/usr/bin/env python3
"""
gitlight_mac.py — Gitlight en la barra de menú (macOS)

Instala dependencias:
    pip3 install rumps requests

Ejecutar:
    python3 gitlight_mac.py
"""

import json
import os
import sys
import datetime

try:
    import rumps
except ImportError:
    print("❌ Falta la librería 'rumps'. Instálala con:\n   pip3 install rumps requests")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ Falta la librería 'requests'. Instálala con:\n   pip3 install rumps requests")
    sys.exit(1)

# ── Configuración ─────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.expanduser("~/.gitlight-config.json")
POLL_INTERVAL = 15        # segundos entre cada consulta
STALE_HOURS   = 8         # horas sin actividad → se considera libre

ICONS = {
    "free":    "🟢",   # nadie trabaja
    "me":      "🔵",   # yo estoy trabajando
    "other":   "🔴",   # el otro está trabajando
    "stale":   "🟡",   # estado antiguo (>8h), se ignora
    "error":   "⚪",   # error de conexión
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        rumps.alert(
            title="Gitlight — Configuración no encontrada",
            message=f"Ejecuta primero setup_gist.py para configurar el semáforo.\n\nArchivo esperado: {CONFIG_PATH}"
        )
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def api_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gitlight"
    }


def is_stale(since_str):
    """Devuelve True si 'since' tiene más de STALE_HOURS horas."""
    if not since_str:
        return False
    try:
        since = datetime.datetime.fromisoformat(since_str.replace("Z", "+00:00"))
        now   = datetime.datetime.now(datetime.timezone.utc)
        return (now - since).total_seconds() > STALE_HOURS * 3600
    except Exception:
        return False


# ── App principal ─────────────────────────────────────────────────────────────

class SemaforoApp(rumps.App):

    def __init__(self):
        super().__init__(ICONS["error"], quit_button=None)
        self.config      = load_config()
        self.is_working  = False
        # display_name is optional in config; falls back to my_username
        self._my_display = self.config.get("display_name") or self.config["my_username"]

        # Elementos del menú
        self.status_item = rumps.MenuItem("Conectando…")
        self.status_item.set_callback(None)   # no-op, solo informativo

        self.toggle_item = rumps.MenuItem("▶  Empezar a trabajar", callback=self.toggle_work)

        self.menu = [
            self.status_item,
            None,
            self.toggle_item,
            None,
            rumps.MenuItem("Salir", callback=self._quit),
        ]

        # Lanzar el timer de polling
        self.timer = rumps.Timer(self._poll, POLL_INTERVAL)
        self.timer.start()
        self._poll(None)   # consulta inmediata al arrancar

    # ── Polling ───────────────────────────────────────────────────────────────

    def _get_remote_state(self):
        """Devuelve (worker, since) o lanza una excepción."""
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
        """Actualiza el Gist con el worker actual (None = libre)."""
        cfg  = self.config
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

    @rumps.timer(POLL_INTERVAL)
    def _poll(self, _):
        try:
            worker, since = self._get_remote_state()
        except Exception as e:
            self.title = ICONS["error"]
            self.status_item.title = f"⚪ Sin conexión ({type(e).__name__})"
            return

        my_user = self.config["my_username"]

        # Si el estado tiene más de STALE_HOURS horas, lo ignoramos
        if worker and is_stale(since):
            worker = None

        other_display = self.config.get("other_display_name") or worker

        if worker is None:
            self.title = ICONS["free"]
            self.status_item.title = "✅ Libre — nadie está trabajando"
            if not self.is_working:
                self.toggle_item.title = "▶  Empezar a trabajar"
        elif worker == my_user:
            self.title = f"🔵  {self._my_display} está trabajando"
            self.status_item.title = f"🔵 {self._my_display} está trabajando (tú)"
            self.toggle_item.title  = "⏹  Terminar de trabajar"
        else:
            self.title = f"🔴  {other_display} está trabajando en el proyecto"
            self.status_item.title = f"🔴 {other_display} está trabajando — ¡espera!"
            if not self.is_working:
                self.toggle_item.title = "▶  Empezar a trabajar"

    # ── Acciones ──────────────────────────────────────────────────────────────

    def toggle_work(self, _):
        my_user = self.config["my_username"]
        try:
            if not self.is_working:
                self._set_remote_state(my_user)
                self.is_working         = True
                self.title              = f"🔵  {self._my_display} está trabajando"
                self.status_item.title  = f"🔵 {self._my_display} está trabajando (tú)"
                self.toggle_item.title  = "⏹  Terminar de trabajar"
            else:
                self._set_remote_state(None)
                self.is_working         = False
                self.title              = ICONS["free"]
                self.status_item.title  = "✅ Libre — nadie está trabajando"
                self.toggle_item.title  = "▶  Empezar a trabajar"
        except Exception as e:
            rumps.alert(title="Error al actualizar estado", message=str(e))

    def _quit(self, _):
        """Al salir, libera el estado si estaba trabajando."""
        if self.is_working:
            try:
                self._set_remote_state(None)
            except Exception:
                pass
        rumps.quit_application()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SemaforoApp().run()
