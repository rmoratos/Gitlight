#!/usr/bin/env python3
"""
setup_gist.py — Configuración inicial del Gitlight
Ejecutar UNA SOLA VEZ (cualquiera de los dos lo puede hacer).

Necesitas un Personal Access Token de GitHub con permiso 'gist'.
Crea uno aquí: https://github.com/settings/tokens/new
  → Selecciona el scope: gist
"""

import json
import os
import sys
import urllib.request
import urllib.error

CONFIG_PATH = os.path.expanduser("~/.gitlight-config.json")


def create_gist(token):
    """Crea el Gist compartido en GitHub."""
    payload = json.dumps({
        "description": "Gitlight - estado compartido",
        "public": False,
        "files": {
            "status.json": {
                "content": json.dumps({"worker": None, "since": None}, indent=2)
            }
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/gists",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "User-Agent": "gitlight"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["id"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"\n❌ Error al crear el Gist: {e.code} - {body}")
        sys.exit(1)


def save_config(gist_id, token, username, display_name=None, other_display_name=None):
    """Guarda la configuración en ~/.gitlight-config.json"""
    config = {
        "gist_id": gist_id,
        "github_token": token,
        "my_username": username,
        "display_name": display_name or username,
        "other_display_name": other_display_name or ""
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    # Permisos solo para el usuario actual
    os.chmod(CONFIG_PATH, 0o600)


def main():
    print("=" * 55)
    print("  🚦 Gitlight — Configuración inicial")
    print("=" * 55)
    print()
    print("Necesitas un GitHub Personal Access Token con scope 'gist'.")
    print("Créalo en: https://github.com/settings/tokens/new")
    print()

    token = input("🔑 Pega tu GitHub Token aquí: ").strip()
    if not token:
        print("❌ Token vacío. Saliendo.")
        sys.exit(1)

    username = input("👤 Tu nombre de usuario de GitHub: ").strip()
    if not username:
        print("❌ Username vacío. Saliendo.")
        sys.exit(1)

    display_name = input(
        f"✏️  Tu nombre visible (deja vacío para usar '{username}'): "
    ).strip() or username

    other_display_name = input(
        "✏️  Nombre visible del otro usuario (ej: 'Hijo', 'Papá', deja vacío para usar su username): "
    ).strip()

    existing_gist_id = input(
        "\n📋 ¿Ya tienes el Gist ID (porque el otro lo configuró antes)?\n"
        "   Si NO, deja vacío y se creará uno nuevo: "
    ).strip()

    if existing_gist_id:
        gist_id = existing_gist_id
        print(f"\n✅ Usando Gist existente: {gist_id}")
    else:
        print("\n⏳ Creando Gist compartido en GitHub...")
        gist_id = create_gist(token)
        print(f"✅ Gist creado: {gist_id}")
        print()
        print("=" * 55)
        print("  ⚠️  IMPORTANTE: Comparte este ID con el otro usuario")
        print(f"  Gist ID: {gist_id}")
        print("=" * 55)

    save_config(gist_id, token, username, display_name, other_display_name)
    print(f"\n✅ Configuración guardada en: {CONFIG_PATH}")
    print()
    print("=" * 55)
    print("  ¡Listo! Ahora ejecuta el semáforo:")
    if sys.platform == "darwin":
        print("  → python3 gitlight_mac.py")
    else:
        print("  → python gitlight_windows.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
