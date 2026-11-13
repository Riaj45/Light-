# Flashlight Pro

A Kivy-based Android flashlight app with:
- Flashlight ON/OFF
- Adjustable blink mode
- SOS pattern mode
- Auto-off timer (1, 5, or 10 minutes)
- Battery percentage display
- Animated interface

## Project files

- `main.py` — application source
- `buildozer.spec` — Android packaging configuration
- `requirements.txt` — Python dependencies for local development

## Run locally

Install Kivy in a supported desktop Python environment:

```bash
python -m pip install -r requirements.txt
python main.py
```

Desktop mode is only a UI preview. It cannot control an Android phone's LED flash.

## Build an Android APK

Buildozer is normally run on Linux (or WSL2 with a suitable Linux setup), not directly inside Pydroid 3.

```bash
python3 -m pip install --user buildozer
buildozer android debug
```

The first build downloads Android build dependencies and can take a while. The APK is normally created under `bin/`.

## Android permission

The app requests the Android `CAMERA` permission because Android's CameraManager torch API requires it. The permission prompt must be accepted for the flashlight to work.

## Important notes

- Some devices do not have an LED flash, or do not expose torch control to third-party apps.
- Test on the actual Android device after installing the APK.
- Blink and SOS modes flash rapidly. Avoid using them near anyone who may be sensitive to flashing lights.
- This project is provided as-is; test hardware behavior before relying on it.
