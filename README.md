# 🚦 Gitlight

Widget que muestra en tiempo real si alguien está trabajando en el proyecto compartido.

| Estado | Significado |
|--------|-------------|
| 🟢 Verde | Nadie está trabajando — puedes entrar |
| 🔴 Rojo  | El otro está trabajando — espera |
| 🔵 Azul  | Tú estás trabajando (recordatorio) |
| ⚪ Gris  | Sin conexión a internet |

---

## Cómo funciona

Los scripts usan un **GitHub Gist privado** como pizarra compartida. Cuando alguien empieza a trabajar, actualiza ese Gist con su nombre. El widget del otro lo lee cada 15 segundos y cambia de color. No necesita servidor ni cuenta de pago.

---

## Instalación paso a paso

### 1. Instalar Python

- **Mac**: Ya viene instalado. Compruébalo con `python3 --version` en la Terminal.
- **Windows**: Descárgalo de https://python.org → durante la instalación marca **"Add Python to PATH"**.

---

### 2. Instalar las dependencias

**Mac** (Terminal):
```bash
pip3 install rumps requests
```

**Windows** (PowerShell o CMD):
```
pip install pystray pillow requests
```

---

### 3. Crear el Gist compartido (solo una vez, cualquiera de los dos)

#### 3.1 Crear un GitHub Token

1. Ve a https://github.com/settings/tokens/new
2. Escribe un nombre, por ejemplo: `semaforo`
3. En **Expiration** elige `No expiration` (o la que prefieras)
4. En **Select scopes** marca solo: **`gist`**
5. Haz clic en **Generate token**
6. **Copia el token** — solo se muestra una vez

#### 3.2 Ejecutar el setup

**Mac**:
```bash
python3 setup_gist.py
```

**Windows**:
```
python setup_gist.py
```

El script te pedirá:
- Tu token de GitHub
- Tu nombre de usuario de GitHub
- Si ya tienes un Gist ID (si el otro ya lo configuró)

Si eres el **primero en ejecutarlo**, el script crea el Gist y te muestra un **Gist ID** de 32 caracteres. **Compárteselo al otro** para que lo use en su setup.

Si eres el **segundo en ejecutarlo**, pega el Gist ID que te pasaron.

---

### 4. Ejecutar el semáforo

**Mac**:
```bash
python3 gitlight_mac.py
```
Verás un emoji en la barra de menú (arriba a la derecha). Haz clic para ver el menú.

**Windows**:
```
python gitlight_windows.py
```
Verás un círculo de color en la bandeja del sistema (abajo a la derecha, junto al reloj). Haz clic derecho para ver el menú.

---

## Uso diario

1. **Antes de empezar a trabajar** → haz clic en el icono → "Empezar a trabajar"
   - El semáforo del otro se pone en 🔴
2. **Al terminar** → haz clic → "Terminar de trabajar"
   - El semáforo del otro vuelve a 🟢
3. Si cierras la app sin pulsar "Terminar", se libera el estado automáticamente.
4. Si llevas más de 8 horas con el estado en "trabajando" sin actualizarlo, se considera libre automáticamente.

---

## Arranque automático (opcional)

### Mac — al iniciar sesión

1. Abre **Preferencias del Sistema → General → Elementos de inicio de sesión**
2. Haz clic en `+` y añade `gitlight_mac.py`

O desde Terminal:
```bash
# Crea un pequeño launcher
cat > ~/Library/LaunchAgents/com.gitlight.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.gitlight</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/ruta/completa/a/gitlight_mac.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.gitlight.plist
```
(Reemplaza `/ruta/completa/a/` con la ruta real del archivo)

### Windows — al iniciar sesión

1. Pulsa `Win + R` → escribe `shell:startup` → Enter
2. Crea un acceso directo a `gitlight_windows.py` en esa carpeta

O crea un archivo `gitlight.bat` con:
```bat
@echo off
start /min python C:\ruta\a\gitlight_windows.py
```
Y mueve ese `.bat` a la carpeta de inicio.

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `setup_gist.py` | Configuración inicial (ejecutar una vez) |
| `gitlight_mac.py` | Widget para macOS (barra de menú) |
| `gitlight_windows.py` | Widget para Windows (bandeja del sistema) |
| `README.md` | Este archivo |

La configuración se guarda en `~/.gitlight-config.json` (no la subas al repo, contiene tu token).
