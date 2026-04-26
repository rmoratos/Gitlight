#!/usr/bin/env python3
"""
gitlight_windows.py — Gitlight system tray widget (Windows)

Install dependencies:
    pip install pystray pillow requests

Run:
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
    print("Missing 'pystray'. Install with:\n   pip install pystray pillow requests")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Missing 'Pillow'. Install with:\n   pip install pystray pillow requests")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Missing 'requests'. Install with:\n   pip install pystray pillow requests")
    input("Press Enter to exit...")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH   = os.path.expanduser("~/.gitlight-config.json")
POLL_INTERVAL = 15      # seconds between polls
STALE_HOURS   = 8       # hours of inactivity → treat as free

COLORS = {
    "free":  (34,  197, 94),    # green
    "me":    (59,  130, 246),   # blue
    "other": (239, 68,  68),    # red
    "error": (156, 163, 175),   # grey
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Run setup_gist.py first to configure Gitlight.\n\nExpected file:\n{CONFIG_PATH}",
            "Gitlight — config not found",
            0x10
        )
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_icon(color_key):
    """Creates a 64×64 colored circle image for the tray."""
    size   = 64
    img    = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(img)
    color  = COLORS.get(color_key, COLORS["error"])
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


# ── App ───────────────────────────────────────────────────────────────────────

class GitlightApp:

    def __init__(self):
        self.config       = load_config()
        self.is_working   = False
        self._lock        = threading.Lock()
        self._prev_worker = None   # tracks changes to trigger notifications
        self._first_poll  = True   # skip notification on startup

        # display_name is optional in config; falls back to my_username
        self._my_display  = self.config.get("display_name") or self.config["my_username"]

        self._status_text = "Connecting..."
        self._color_key   = "error"

        self.icon = pystray.Icon(
            "gitlight",
            icon=make_icon("error"),
            title="Gitlight — connecting...",
            menu=self._build_menu()
        )

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        label = "Stop working" if self.is_working else "Start working"
        return Menu(
            Item(lambda _: self._status_text, None, enabled=False),
            Menu.SEPARATOR,
            Item(label, self._toggle_work),
            Menu.SEPARATOR,
            Item("Quit", self._quit),
        )

    def _refresh_menu(self):
        self.icon.menu = self._build_menu()

    # ── Network ───────────────────────────────────────────────────────────────

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
                self._status_text = f"No connection ({type(e).__name__})"
                self._color_key   = "error"
            self.icon.icon  = make_icon("error")
            self.icon.title = "Gitlight — no connection"
            return

        my_user = self.config["my_username"]

        if worker and is_stale(since):
            worker = None

        with self._lock:
            changed = (worker != self._prev_worker)

            if worker is None:
                self._status_text = "Free — nobody is working"
                self.icon.icon    = make_icon("free")
                self.icon.title   = "Gitlight — Free"
                # Notify if someone just stopped working
                if changed and not self._first_poll and self._prev_worker and self._prev_worker != my_user:
                    self.icon.notify(
                        f"The project is free — you can start working.",
                        "🟢 Gitlight"
                    )
                if not self.is_working:
                    self._refresh_menu()

            elif worker == my_user:
                self._status_text = f"{self._my_display} is working (you)"
                self.icon.icon    = make_icon("me")
                self.icon.title   = f"Gitlight — {self._my_display} is working"

            else:
                # Resolve display name: check if config has a name for this user
                other_display = self.config.get("other_display_name") or worker
                self._status_text = f"{other_display} is working on the project"
                self.icon.icon    = make_icon("other")
                self.icon.title   = f"🔴 Gitlight — {other_display} is working"
                # Notify if this person just started
                if changed and not self._first_poll:
                    self.icon.notify(
                        f"{other_display} is working on the project — please wait!",
                        "🔴 Gitlight"
                    )
                if not self.is_working:
                    self._refresh_menu()

            self._prev_worker = worker
            self._first_poll  = False

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_work(self, icon, item):
        my_user = self.config["my_username"]
        try:
            with self._lock:
                if not self.is_working:
                    self._set_remote_state(my_user)
                    self.is_working   = True
                    self._prev_worker = my_user
                    self._status_text = f"{self._my_display} is working (you)"
                    self.icon.icon    = make_icon("me")
                    self.icon.title   = f"Gitlight — {self._my_display} is working"
                else:
                    self._set_remote_state(None)
                    self.is_working   = False
                    self._prev_worker = None
                    self._status_text = "Free — nobody is working"
                    self.icon.icon    = make_icon("free")
                    self.icon.title   = "Gitlight — Free"
            self._refresh_menu()
        except Exception as e:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(e), "Gitlight — error", 0x10)

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
    GitlightApp().run()
