# Building the Name Generator Installer

This project uses **PyInstaller** to create a standalone executable and **Inno Setup** to create a Windows installer that actually installs the app (Start Menu, Uninstall, etc.).

**Important:** PyInstaller alone does **not** install anything—it only creates an exe file. To have the app show up in Start Menu and Add/Remove Programs, you must build the Inno Setup installer and then **run** the generated Setup exe.

## Prerequisites

- Python 3.10+ with the project dependencies installed
- [PyInstaller](https://pyinstaller.org): `pip install pyinstaller`
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (needed to create the installer that installs the app)

## Step 1: Create the executable

From the project root (where `app.py` and `NameGenerator.spec` are):

```powershell
# Activate your venv, then:
pip install pyinstaller -r requirements.txt
pyinstaller NameGenerator.spec
```

**Result:** A file is created at `dist\NameGenerator.exe`. This step does **not** install the app—it only builds the exe. You can run `dist\NameGenerator.exe` directly to test, but nothing is added to Start Menu or Program Files yet.

## Step 2: Create the installer (Setup exe)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) if you haven’t.
2. Make sure Step 1 is done (you have `dist\NameGenerator.exe`).
3. Open `installer.iss` in Inno Setup (double‑click or File → Open).
4. In Inno Setup, choose **Build → Compile**.

**Result:** Inno Setup creates `output\NameGenerator-Setup-1.0.exe`. This is the **installer program**—it does not install the app by itself.

## Step 3: Install the app (run the Setup exe)

1. Go to the `output` folder in your project.
2. Double‑click **NameGenerator-Setup-1.0.exe**.
3. Follow the wizard (choose install folder, desktop shortcut, etc.).
4. When it finishes, the app is installed:
   - **Start Menu** → “Name Generator”
   - **Uninstall:** Settings → Apps → Name Generator → Uninstall

Until you run the Setup exe (Step 3), nothing is installed on the system—you only have the built exe and the installer file.

## Summary

| Step | What you do | What you get |
|------|-------------|--------------|
| 1 | `pyinstaller NameGenerator.spec` | `dist\NameGenerator.exe` (run directly to test) |
| 2 | Compile `installer.iss` in Inno Setup | `output\NameGenerator-Setup-1.0.exe` (the installer) |
| 3 | **Run** `NameGenerator-Setup-1.0.exe` | App installed (Start Menu, optional desktop icon, Uninstall entry) |

## Notes for end users

- **Ollama** must be installed and running (e.g. `ollama serve`) with at least one model (e.g. `ollama pull llama2`). The installer can optionally open the Ollama download page.
- The first run creates `%APPDATA%\NameGenerator` for prompts, config, and theme. Reinstalling or updating the app does not delete this data.
