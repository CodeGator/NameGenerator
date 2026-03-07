# Name Generator

A desktop app that uses [Ollama](https://ollama.com) to generate names: character names, project names, product names, and more. Pick a stored prompt, set how many names you want, and click **Generate** to get a list of unique names.

**Features:**

- **Generate** — Choose a prompt, number of names (1–100), optional character limits, and generate. Sort, copy, or save the list to a file.
- **Manage prompts** — Add, edit, and remove prompts in-app (no need to edit JSON by hand). Duplicate titles are prevented.
- **Options** — Theme (light/dark), AI model (from Ollama), creativity slider, and a “negative prompt” (what to avoid).
- **About** — App name, version, and copyright (CodeGator).

User data (prompts, theme, selected prompt, negative prompt) is stored in a single folder and is preserved when you update or reinstall.

---

## Requirements

- **Python 3.10+**
- [Ollama](https://ollama.com) installed and running, with at least one model (e.g. `ollama pull llama2`)

---

## Setup

1. Install and run [Ollama](https://ollama.com). Pull a model, e.g.:
   ```bash
   ollama pull llama2
   ```
2. Clone or download this project, then create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

---

## Run

```bash
python app.py
```

- **Generate tab** — Pick a prompt, set the number of names (slider), optionally limit character length, then click **Generate**. The list opens in a popup where you can sort, copy, save to file, or regenerate.
- **Edit prompts** — Opens a window to add, edit, or remove prompts (name + prompt text). The selected prompt is remembered between sessions.
- **Options tab** — Theme (light/dark), AI model and Refresh, creativity (temperature), and negative prompt text. Theme and selected prompt are saved automatically.
- **About tab** — App name, version, and copyright.

---

## Managing prompts

Use **Edit prompts** on the Generate tab to add, edit, or remove prompts. Each prompt has:

- **Name** — Shown in the dropdown (must be unique).
- **Prompt text** — The exact text sent to the model (e.g. “Generate 10 fantasy character names. One per line.”).

Prompt data is stored in `prompts.json` in the app data folder (see below). You can also edit that file directly if you prefer.

---

## Where your data is stored

All user data is in one folder so it survives reinstalls and updates:

| Platform | Folder |
|----------|--------|
| Windows | `%APPDATA%\NameGenerator` (e.g. `C:\Users\<you>\AppData\Roaming\NameGenerator`) |
| macOS/Linux | `~/.config/NameGenerator` |

Files there:

- **prompts.json** — Your prompts (name + prompt text).
- **app_config.json** — Theme (light/dark) and last selected prompt.
- **negative_prompt.txt** — The “what to avoid” text from the Options tab.

---

## Creating an installer

To build a standalone Windows executable and an installer (Start Menu shortcut, Uninstall):

1. **Build the exe:** `pip install pyinstaller` then `pyinstaller NameGenerator.spec` → creates `dist\NameGenerator.exe`.
2. **Build the installer:** Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), open `installer.iss`, and use **Build → Compile** → creates `output\NameGenerator-Setup-1.0.exe`.
3. **Install the app:** Run `NameGenerator-Setup-1.0.exe` and complete the wizard. The app will appear in the Start Menu and in Settings → Apps (for uninstall).

See **[BUILD.md](BUILD.md)** for detailed step-by-step instructions.
