"""
Name Generator GUI - Select a prompt and generate names with Ollama.
"""
from __future__ import annotations

import json
import os
import sys
import webbrowser
import random
import re
import shutil
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from typing import Callable

from name_generator import (
    load_prompts,
    save_prompts,
    list_models,
    generate_names,
    parse_names,
)

def _app_base_path() -> Path:
    """Base path for app resources; works when run from source or as PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


# User data directory: %APPDATA%\NameGenerator on Windows, ~/.config/NameGenerator elsewhere
_APP_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / ".config"))) / "NameGenerator"
_APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

NEGATIVE_PROMPT_PATH = _APP_DATA_DIR / "negative_prompt.txt"
APP_CONFIG_PATH = _APP_DATA_DIR / "app_config.json"
PROMPTS_PATH = _APP_DATA_DIR / "prompts.json"


def _migrate_config_from_project() -> None:
    """Copy config files from project folder to AppData on first run (if source exists, dest does not). Skipped when running as installed/bundled app."""
    if getattr(sys, "frozen", False):
        return
    project_dir = Path(__file__).parent
    to_migrate = [
        ("negative_prompt.txt", NEGATIVE_PROMPT_PATH),
        ("app_config.json", APP_CONFIG_PATH),
        ("prompts.json", PROMPTS_PATH),
    ]
    for name, dest in to_migrate:
        src = project_dir / name
        if src.exists() and not dest.exists():
            try:
                shutil.copy2(src, dest)
            except OSError:
                pass


_migrate_config_from_project()

APP_NAME = "Name Generator"
APP_VERSION = "1.1"
COPYRIGHT_OWNER = "CodeGator"
COPYRIGHT_YEAR_START = 2002
LOGO_PATH = _app_base_path() / "resources" / "codegator-167x79.png"

THEME_COLORS = {
    "light": {
        "bg": "#f0f0f0",
        "fg": "#000000",
        "select_bg": "#c0c0c0",
        "select_fg": "#000000",
        "tab_bg_unselected": "#e0e0e0",
        "accent_bg": "#2563eb",
        "accent_bg_active": "#1d4ed8",
    },
    "dark": {
        "bg": "#2d2d2d",
        "fg": "#e0e0e0",
        "select_bg": "#505050",
        "select_fg": "#e0e0e0",
        "tab_bg_unselected": "#252525",
        "accent_bg": "#2563eb",
        "accent_bg_active": "#3b82f6",
    },
}

_current_theme = "light"  # updated by _apply_theme so new toplevels can use it

# Standard button width for consistency
BTN_WIDTH = 12

# UI constants
LISTBOX_DEFAULT_HEIGHT = 18
COMBOBOX_STYLE_DELAY_MS = 20


def _slug(name: str) -> str:
    """Convert a name to a lowercase id-style slug."""
    s = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", s).strip("-") or "prompt"


def _unique_id(prompts: list[dict], base: str) -> str:
    """Return base or base-N so the id is unique in prompts."""
    ids = {p["id"] for p in prompts}
    if base not in ids:
        return base
    n = 1
    while f"{base}-{n}" in ids:
        n += 1
    return f"{base}-{n}"


def _center_over_parent(win: tk.Toplevel, parent: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    """Position a toplevel window centered over its parent."""
    parent.update_idletasks()
    win.update_idletasks()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    x = px + max(0, (pw - width) // 2)
    y = py + max(0, (ph - height) // 2)
    win.geometry(f"+{x}+{y}")


def _read_app_config() -> dict:
    """Read app config file. Returns empty dict on missing file or invalid JSON (Single Responsibility)."""
    if not APP_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_app_config(updates: dict) -> None:
    """Merge key-value updates into app config and write (Single Responsibility)."""
    try:
        data = _read_app_config()
        data.update(updates)
        APP_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_theme() -> str:
    """Load saved theme from config file. Returns 'light' or 'dark'."""
    t = (_read_app_config().get("theme") or "light").lower()
    return t if t in ("light", "dark") else "light"


def _save_theme(theme: str) -> None:
    """Save theme to config file."""
    _write_app_config({"theme": theme})


def _load_selected_prompt() -> str | None:
    """Load saved selected prompt name from config. Returns None if not set or invalid."""
    return _read_app_config().get("selected_prompt") or None


def _save_selected_prompt(prompt_name: str) -> None:
    """Save selected prompt name to config file."""
    _write_app_config({"selected_prompt": prompt_name})


def _load_selected_model() -> str | None:
    """Load saved AI model from config. Returns None if not set or invalid."""
    return _read_app_config().get("selected_model") or None


def _save_selected_model(model: str) -> None:
    """Save selected AI model to config file."""
    _write_app_config({"selected_model": model})


def _apply_theme(root: tk.Tk, theme: str) -> None:
    """Apply light or dark theme to the app (ttk and tk widgets)."""
    global _current_theme
    _current_theme = theme
    colors = THEME_COLORS.get(theme, THEME_COLORS["light"])
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    bg, fg = colors["bg"], colors["fg"]
    style.configure(".", background=bg, foreground=fg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", background=bg, foreground=fg)
    style.map("TButton", background=[("active", colors["select_bg"])])
    # Accent button style (Generate, Close in popups): stands out with color
    accent_bg = colors.get("accent_bg", "#2563eb")
    accent_active = colors.get("accent_bg_active", "#1d4ed8")
    style.configure(
        "Accent.TButton",
        background=accent_bg,
        foreground="#ffffff",
    )
    style.map("Accent.TButton", background=[("active", accent_active), ("pressed", accent_active)])
    # Link style: blue foreground for hyperlinks
    style.configure("Link.TLabel", background=bg, foreground=accent_bg)
    style.configure("TEntry", fieldbackground=bg, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TScale", background=bg, foreground=fg)
    style.configure("TCombobox", fieldbackground=bg, foreground=fg, background=bg)
    # When combobox is readonly and/or unfocused, some themes show wrong colors; force theme colors
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", bg),
            ("!focus", bg),
            (("readonly", "!focus"), bg),
        ],
        foreground=[
            ("readonly", fg),
            ("!focus", fg),
            (("readonly", "!focus"), fg),
        ],
    )
    # Notebook: selected tab must use content bg/fg so it's readable
    tab_unselected = colors.get("tab_bg_unselected", bg)
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=tab_unselected, foreground=fg)
    style.map("TNotebook.Tab", background=[("selected", bg)], foreground=[("selected", fg)])
    # Combobox dropdown listbox uses tk Listbox; set option so popdown gets theme colors
    for prefix in ("*TCombobox*Listbox", "*Listbox"):
        root.option_add(f"{prefix}.background", bg)
        root.option_add(f"{prefix}.foreground", fg)
        root.option_add(f"{prefix}.selectBackground", colors["select_bg"])
        root.option_add(f"{prefix}.selectForeground", colors["select_fg"])
    root.configure(bg=bg)
    _style_tk_widgets_recursive(root, colors)


def _style_tk_widgets_recursive(w: tk.Widget, colors: dict) -> None:
    """Recursively apply theme colors to tk widgets (Listbox, Text, Entry, image Labels)."""
    for c in w.winfo_children():
        _style_tk_widgets_recursive(c, colors)
    try:
        cls = w.winfo_class()
        bg, fg = colors["bg"], colors["fg"]
        if cls in ("Listbox", "Text", "Entry"):
            w.configure(
                bg=bg,
                fg=fg,
                selectbackground=colors["select_bg"],
                selectforeground=colors["select_fg"],
            )
        elif cls == "Label" and "image" in w.keys():
            w.configure(bg=bg)
    except (tk.TclError, AttributeError):
        pass


def _style_combobox_dropdowns(root: tk.Tk) -> None:
    """Find all Listbox widgets (including combobox popdowns) and apply current theme colors.
    Call this shortly after a combobox dropdown is posted so the listbox gets correct colors.
    """
    colors = THEME_COLORS.get(_current_theme, THEME_COLORS["light"])
    _style_tk_widgets_recursive(root, colors)


def _apply_theme_to_window(win: tk.Toplevel | tk.Tk) -> None:
    """Apply current theme to a single window (e.g. a new Toplevel). Call after creating the window."""
    colors = THEME_COLORS.get(_current_theme, THEME_COLORS["light"])
    win.configure(bg=colors["bg"])
    _style_tk_widgets_recursive(win, colors)


def _prompt_editor_dialog(
    parent: tk.Tk | tk.Toplevel,
    title: str,
    initial_name: str = "",
    initial_prompt: str = "",
) -> tuple[str | None, str | None]:
    """Show a dialog to edit name and prompt text. Returns (name, prompt) or (None, None) if cancelled."""
    result = [None, None]  # mutable so nested fn can set

    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.grab_set()
    win.geometry("420x280")

    f = ttk.Frame(win, padding=10)
    f.pack(fill=tk.BOTH, expand=True)
    ttk.Label(f, text="Name:").grid(row=0, column=0, sticky="w", pady=(0, 4))
    name_var = tk.StringVar(value=initial_name)
    name_entry = ttk.Entry(f, textvariable=name_var, width=50)
    name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(f, text="Prompt text:").grid(row=2, column=0, sticky="w", pady=(0, 4))
    prompt_text = tk.Text(f, wrap=tk.WORD, width=50, height=8)
    prompt_text.insert("1.0", initial_prompt)
    prompt_text.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
    f.columnconfigure(0, weight=1)
    f.rowconfigure(3, weight=1)

    def ok():
        n = name_var.get().strip()
        p = prompt_text.get("1.0", tk.END).strip()
        if not n:
            messagebox.showwarning("Missing name", "Please enter a name.", parent=win)
            return
        result[0], result[1] = n, p
        win.destroy()

    def cancel():
        win.destroy()

    btns = ttk.Frame(win)
    btns.pack(fill=tk.X, padx=10, pady=(0, 10))
    ttk.Button(btns, text="OK", width=BTN_WIDTH, command=ok).pack(side=tk.RIGHT, padx=4)
    ttk.Button(btns, text="Cancel", width=BTN_WIDTH, command=cancel).pack(side=tk.RIGHT)

    win.protocol("WM_DELETE_WINDOW", cancel)
    name_entry.focus_set()
    _apply_theme_to_window(win)
    _center_over_parent(win, parent, 420, 280)
    win.wait_window()
    return (result[0], result[1])


def _names_result_window(
    parent: tk.Tk | tk.Toplevel,
    names: list[str],
    on_regenerate: None = None,
) -> None:
    """Show generated names in a popup with multi-select and Copy to clipboard.
    on_regenerate: if set, callable(update_fn) where update_fn(names, error_msg) updates the list.
    """
    win = tk.Toplevel(parent)
    win.title("Generated names")
    win.transient(parent)
    win.minsize(320, 360)
    win.geometry("360x370")

    current_names = list(names)  # mutable copy for sorting

    f = ttk.Frame(win, padding=10)
    f.pack(fill=tk.BOTH, expand=True)
    f.columnconfigure(0, weight=1)
    f.rowconfigure(2, weight=1)

    ttk.Label(f, text="Select names to copy (or copy all with none selected):").grid(
        row=0, column=0, sticky="w", pady=(0, 4)
    )

    list_frame = ttk.Frame(f)
    def refresh_listbox():
        listbox.delete(0, tk.END)
        for name in current_names:
            listbox.insert(tk.END, name)

    def sort_asc():
        current_names.sort(key=str.lower)
        refresh_listbox()

    def sort_desc():
        current_names.sort(key=str.lower, reverse=True)
        refresh_listbox()

    sort_f = ttk.Frame(f)
    sort_f.grid(row=1, column=0, sticky="w", pady=(0, 4))
    ttk.Button(sort_f, text="Sort A–Z", width=BTN_WIDTH, command=sort_asc).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(sort_f, text="Sort Z–A", width=BTN_WIDTH, command=sort_desc).pack(side=tk.LEFT)

    list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)
    scrollbar = ttk.Scrollbar(list_frame)
    listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=LISTBOX_DEFAULT_HEIGHT, yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)
    listbox.grid(row=0, column=0, sticky="nsew")
    if len(current_names) > LISTBOX_DEFAULT_HEIGHT:
        scrollbar.grid(row=0, column=1, sticky="ns")
    for name in current_names:
        listbox.insert(tk.END, name)

    def copy_to_clipboard():
        sel = listbox.curselection()
        if sel:
            to_copy = [current_names[i] for i in sel]
        else:
            to_copy = current_names
        if to_copy:
            text = "\n".join(to_copy)
            parent.clipboard_clear()
            parent.clipboard_append(text)
            parent.update_idletasks()
            status_var.set(f"Copied {len(to_copy)} name(s).")

    def save_to_file():
        path = filedialog.asksaveasfilename(
            parent=win,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text("\n".join(current_names), encoding="utf-8")
            status_var.set(f"Saved {len(current_names)} names to file.")
        except Exception as e:
            messagebox.showerror("Save failed", str(e), parent=win)

    status_var = tk.StringVar(value="")
    ttk.Label(f, textvariable=status_var).grid(row=3, column=0, sticky="w", pady=(0, 4))

    def update_names(new_names: list, error_msg: str | None):
        regen_btn.config(state="normal")
        if error_msg:
            status_var.set(error_msg)
            return
        current_names.clear()
        current_names.extend(new_names)
        refresh_listbox()
        status_var.set(f"Generated {len(new_names)} names.")
        if len(new_names) > LISTBOX_DEFAULT_HEIGHT:
            scrollbar.grid(row=0, column=1, sticky="ns")

    def do_regenerate():
        if not on_regenerate:
            return
        regen_btn.config(state="disabled")
        status_var.set("Generating…")
        on_regenerate(update_names)

    btn_below = ttk.Frame(f)
    btn_below.grid(row=4, column=0, sticky="w", pady=(4, 0))
    if on_regenerate:
        regen_btn = ttk.Button(btn_below, text="Regenerate", width=BTN_WIDTH, command=do_regenerate)
        regen_btn.pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_below, text="Copy", width=BTN_WIDTH, command=copy_to_clipboard).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_below, text="Save to file", width=BTN_WIDTH, command=save_to_file).pack(side=tk.LEFT, padx=4)

    ttk.Button(f, text="Close", width=BTN_WIDTH, command=win.destroy, style="Accent.TButton").grid(row=5, column=0, sticky="ew", pady=(8, 0))

    _apply_theme_to_window(win)
    _center_over_parent(win, parent, 360, 370)


def _manage_prompts_window(
    parent: tk.Tk | tk.Toplevel,
    prompts: list[dict],
    save_prompts_fn: Callable[[list[dict]], None],
    refresh_callback: Callable[[], None],
) -> None:
    """Open a window to add, edit, and remove prompts. Saves to disk on each change."""
    win = tk.Toplevel(parent)
    win.title("Manage prompts")
    win.transient(parent)
    win.geometry("480x320")

    main = ttk.Frame(win, padding=10)
    main.pack(fill=tk.BOTH, expand=True)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(1, weight=1)

    ttk.Label(main, text="Prompts (double-click to edit):").grid(row=0, column=0, sticky="w", pady=(0, 4))
    listbox = tk.Listbox(main, height=12, selectmode=tk.SINGLE)
    listbox.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
    for p in prompts:
        listbox.insert(tk.END, p["name"])

    def save_and_refresh():
        save_prompts_fn(prompts)
        refresh_callback()

    def on_add():
        name, prompt_text = _prompt_editor_dialog(win, "Add prompt", "", "")
        if name is None:
            return
        if any(p["name"].lower().strip() == name.lower().strip() for p in prompts):
            messagebox.showwarning(
                "Duplicate title",
                "A prompt with this name already exists. Please use a different name.",
                parent=win,
            )
            return
        pid = _unique_id(prompts, _slug(name))
        prompts.append({"id": pid, "name": name, "prompt": prompt_text})
        prompts.sort(key=lambda p: p["name"].lower())
        save_and_refresh()
        listbox.delete(0, tk.END)
        for p in prompts:
            listbox.insert(tk.END, p["name"])
        # Select the new one
        idx = next(i for i, p in enumerate(prompts) if p["name"] == name)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(idx)
        listbox.see(idx)

    def on_edit():
        sel = listbox.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select a prompt to edit.", parent=win)
            return
        idx = int(sel[0])
        p = prompts[idx]
        name, prompt_text = _prompt_editor_dialog(win, "Edit prompt", p["name"], p["prompt"])
        if name is None:
            return
        if any(prompts[i]["name"].lower().strip() == name.lower().strip() for i in range(len(prompts)) if i != idx):
            messagebox.showwarning(
                "Duplicate title",
                "Another prompt already has this name. Please use a different name.",
                parent=win,
            )
            return
        p["name"] = name
        p["prompt"] = prompt_text
        # Keep id unless name changed enough to want new slug (we keep same id on edit)
        prompts.sort(key=lambda x: x["name"].lower())
        save_and_refresh()
        listbox.delete(0, tk.END)
        for pr in prompts:
            listbox.insert(tk.END, pr["name"])
        new_idx = next(i for i, pr in enumerate(prompts) if pr["name"] == name)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(new_idx)
        listbox.see(new_idx)

    def on_remove():
        sel = listbox.curselection()
        if not sel:
            messagebox.showinfo("Remove", "Select a prompt to remove.", parent=win)
            return
        idx = int(sel[0])
        if not messagebox.askyesno("Remove prompt", "Remove this prompt?", parent=win):
            return
        prompts.pop(idx)
        save_and_refresh()
        listbox.delete(idx)
        if prompts and idx < len(prompts):
            listbox.selection_set(idx)
        elif prompts and idx > 0:
            listbox.selection_set(idx - 1)

    def on_double_click(event):
        on_edit()

    listbox.bind("<Double-1>", on_double_click)

    btn_frame = ttk.Frame(main)
    btn_frame.grid(row=2, column=0, sticky="w")
    ttk.Button(btn_frame, text="Add", width=BTN_WIDTH, command=on_add).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text="Edit", width=BTN_WIDTH, command=on_edit).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame, text="Remove", width=BTN_WIDTH, command=on_remove).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame, text="Close", width=BTN_WIDTH, command=win.destroy).pack(side=tk.RIGHT)

    _apply_theme_to_window(win)
    _center_over_parent(win, parent, 480, 320)


def run_app() -> None:
    """Create main window, build tabs (Generate, Options, About), and start main loop."""
    prompts = load_prompts(PROMPTS_PATH)
    prompts = sorted(prompts, key=lambda p: p["name"].lower())

    root = tk.Tk()
    root.title("Name Generator")
    root.minsize(480, 420)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    # Remove maximize and minimize buttons from title bar (Windows: tool window style)
    try:
        root.attributes("-toolwindow", 1)
    except tk.TclError:
        pass

    initial_theme = _load_theme()
    _apply_theme(root, initial_theme)

    models = list_models()
    status_msg = "Select a prompt and click Generate."
    if not models:
        status_msg = "No models found. Go to Options tab, start Ollama, and click Refresh."
    status_var = tk.StringVar(value=status_msg)

    notebook = ttk.Notebook(root)
    notebook.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    status_bar = ttk.Frame(root)
    status_bar.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
    root.columnconfigure(0, weight=1)
    status_bar.columnconfigure(0, weight=1)
    ttk.Label(status_bar, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W).grid(
        row=0, column=0, sticky="ew"
    )

    # ---- Main tab: Generate ----
    frame_main = ttk.Frame(notebook, padding=8)
    notebook.add(frame_main, text="Generate")
    frame_main.columnconfigure(0, weight=1)

    ttk.Label(frame_main, text="Prompt:").grid(row=0, column=0, sticky="w", pady=(0, 4))
    prompt_names = [p["name"] for p in prompts]
    saved_prompt = _load_selected_prompt()
    initial_prompt = (saved_prompt if saved_prompt in prompt_names else (prompt_names[0] if prompt_names else ""))
    prompt_var = tk.StringVar(value=initial_prompt)
    prompt_combo = ttk.Combobox(
        frame_main,
        textvariable=prompt_var,
        values=[p["name"] for p in prompts],
        state="readonly",
        width=50,
    )
    prompt_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    prompt_combo["postcommand"] = lambda: root.after(COMBOBOX_STYLE_DELAY_MS, lambda: _style_combobox_dropdowns(root))

    def refresh_prompt_list():
        """Reload prompts from disk, sort, and update dropdown and selection."""
        nonlocal prompts
        prompts.clear()
        prompts.extend(sorted(load_prompts(PROMPTS_PATH), key=lambda p: p["name"].lower()))
        names = [p["name"] for p in prompts]
        prompt_combo["values"] = names
        if prompt_var.get() not in names and names:
            prompt_var.set(names[0])
        elif not names:
            prompt_var.set("")
        update_generate_button_state()

    def open_manage_prompts():
        _manage_prompts_window(root, prompts, lambda p: save_prompts(p, PROMPTS_PATH), refresh_prompt_list)

    ttk.Button(frame_main, text="Edit prompts", width=BTN_WIDTH, command=open_manage_prompts).grid(
        row=1, column=1, padx=(8, 0), pady=(0, 8)
    )

    num_names_var = tk.IntVar(value=10)
    num_names_row = ttk.Frame(frame_main)
    num_names_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 4))
    ttk.Label(num_names_row, text="Number of names:").pack(side=tk.LEFT)
    num_names_label = ttk.Label(num_names_row, text="10")
    num_names_label.pack(side=tk.LEFT, padx=(4, 0))

    def on_num_names_change(v):
        n = int(float(v))
        num_names_var.set(n)
        num_names_label.config(text=str(n))

    num_slider = ttk.Scale(
        frame_main,
        from_=1,
        to=100,
        orient=tk.HORIZONTAL,
        variable=num_names_var,
        command=on_num_names_change,
    )
    num_slider.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    # Optional: limit characters per name
    char_limit_var = tk.BooleanVar(value=False)
    char_limit_check = ttk.Checkbutton(
        frame_main,
        text="Limit characters per name",
        variable=char_limit_var,
    )
    char_limit_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 4))

    char_limit_frame = ttk.LabelFrame(frame_main, text="Min / max characters per name", padding=4)
    char_limit_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    min_chars_var = tk.IntVar(value=2)
    max_chars_var = tk.IntVar(value=20)

    def on_min_chars(v):
        n = int(float(v))
        min_chars_var.set(n)
        min_chars_label.config(text=str(n))

    def on_max_chars(v):
        n = int(float(v))
        max_chars_var.set(n)
        max_chars_label.config(text=str(n))

    ttk.Label(char_limit_frame, text="Min:").grid(row=0, column=0, sticky="w", padx=(0, 2), pady=2)
    min_chars_label = ttk.Label(char_limit_frame, text="2")
    min_chars_label.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=2)
    min_slider = ttk.Scale(
        char_limit_frame, from_=1, to=30, orient=tk.HORIZONTAL, variable=min_chars_var, command=on_min_chars
    )
    min_slider.grid(row=0, column=2, sticky="ew", padx=(0, 12), pady=2)

    ttk.Label(char_limit_frame, text="Max:").grid(row=0, column=3, sticky="w", padx=(0, 2), pady=2)
    max_chars_label = ttk.Label(char_limit_frame, text="20")
    max_chars_label.grid(row=0, column=4, sticky="w", padx=(0, 8), pady=2)
    max_slider = ttk.Scale(
        char_limit_frame, from_=1, to=50, orient=tk.HORIZONTAL, variable=max_chars_var, command=on_max_chars
    )
    max_slider.grid(row=0, column=5, sticky="ew", padx=(0, 0), pady=2)

    char_limit_frame.columnconfigure(2, weight=1)
    char_limit_frame.columnconfigure(5, weight=1)

    def set_children_state(parent, disabled: bool):
        for w in parent.winfo_children():
            if hasattr(w, "state") and callable(getattr(w, "state")):
                try:
                    w.state(["disabled"] if disabled else ["!disabled"])
                except tk.TclError:
                    pass
            set_children_state(w, disabled)

    def update_char_limit_section_state():
        set_children_state(char_limit_frame, not char_limit_var.get())

    char_limit_var.trace_add("write", lambda *a: update_char_limit_section_state())
    update_char_limit_section_state()

    generate_btn = ttk.Button(frame_main, text="Generate", width=BTN_WIDTH, style="Accent.TButton")
    generate_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)

    def update_generate_button_state():
        if not prompts or not prompt_var.get().strip():
            generate_btn.config(state="disabled")
        else:
            names = [p["name"] for p in prompts]
            generate_btn.config(state="normal" if prompt_var.get() in names else "disabled")

    prompt_var.trace_add("write", lambda *a: update_generate_button_state())
    update_generate_button_state()

    frame_main.columnconfigure(1, weight=0)

    # ---- Options tab ----
    frame_options = ttk.Frame(notebook, padding=8)
    notebook.add(frame_options, text="Options")
    frame_options.columnconfigure(1, weight=1)

    # ---- About tab ----
    frame_about = ttk.Frame(notebook, padding=8)
    notebook.add(frame_about, text="About")
    frame_about.columnconfigure(0, weight=1)
    copyright_years = f"{COPYRIGHT_YEAR_START}\u2013{date.today().year}"  # en dash
    row_about = 0
    if LOGO_PATH.exists():
        try:
            logo_photo = tk.PhotoImage(file=str(LOGO_PATH))
            frame_about._logo_image = logo_photo  # keep reference so image is not garbage-collected
            logo_bg = THEME_COLORS.get(initial_theme, THEME_COLORS["light"])["bg"]
            logo_label = tk.Label(frame_about, image=logo_photo, bg=logo_bg)
            logo_label.grid(row=row_about, column=0, sticky="w", pady=(0, 12))
            row_about += 1
        except (tk.TclError, OSError):
            pass
    ttk.Label(frame_about, text=APP_NAME, font=("", 14, "bold")).grid(row=row_about, column=0, sticky="w", pady=(0, 4))
    row_about += 1
    ttk.Label(frame_about, text=f"Version {APP_VERSION}").grid(row=row_about, column=0, sticky="w", pady=(0, 4))
    row_about += 1

    GITHUB_URL = "https://github.com/CodeGator/NameGenerator"
    link_label = ttk.Label(frame_about, text="GitHub repository", cursor="hand2", style="Link.TLabel")
    link_label.grid(row=row_about, column=0, sticky="w", pady=(0, 4))
    link_label.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))
    row_about += 1

    ttk.Label(frame_about, text=f"Copyright \u00a9 {copyright_years} {COPYRIGHT_OWNER}. All rights reserved.").grid(
        row=row_about, column=0, sticky="w", pady=(0, 4)
    )

    ttk.Label(frame_options, text="Theme:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
    theme_var = tk.StringVar(value=initial_theme)
    theme_combo = ttk.Combobox(
        frame_options,
        textvariable=theme_var,
        values=["light", "dark"],
        state="readonly",
        width=12,
    )
    theme_combo.grid(row=1, column=0, sticky="w", pady=(0, 4))
    theme_combo["postcommand"] = lambda: root.after(COMBOBOX_STYLE_DELAY_MS, lambda: _style_combobox_dropdowns(root))

    def on_theme_change(*_):
        t = (theme_var.get() or "light").lower()
        if t not in ("light", "dark"):
            t = "light"
        _save_theme(t)
        _apply_theme(root, t)

    theme_var.trace_add("write", on_theme_change)

    ttk.Label(frame_options, text="AI model:").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
    saved_model = _load_selected_model()
    model_choices = models if models else ["llama2"]
    default_model = (
        saved_model if saved_model and saved_model in model_choices else (models[0] if models else "llama2")
    )
    model_var = tk.StringVar(value=default_model)
    model_combo = ttk.Combobox(
        frame_options,
        textvariable=model_var,
        values=models if models else ["llama2"],
        state="readonly" if models else "normal",
        width=36,
    )
    model_combo.grid(row=3, column=0, sticky="ew", pady=(0, 4))
    model_combo["postcommand"] = lambda: root.after(COMBOBOX_STYLE_DELAY_MS, lambda: _style_combobox_dropdowns(root))

    def on_model_change(*_):
        m = model_var.get().strip()
        if m:
            _save_selected_model(m)

    model_var.trace_add("write", on_model_change)

    def refresh_models():
        new_models = list_models()
        model_combo["values"] = new_models if new_models else ["llama2"]
        if new_models and model_var.get() not in new_models:
            model_var.set(new_models[0])
        if new_models:
            model_combo["state"] = "readonly"
            status_var.set("Select a prompt and click Generate.")
        else:
            model_combo["state"] = "normal"
            status_var.set("No models found. Start Ollama and click Refresh, or run: ollama pull llama2")

    ttk.Button(frame_options, text="Refresh", width=BTN_WIDTH, command=refresh_models).grid(
        row=3, column=1, sticky="w", pady=(0, 4), padx=(8, 0)
    )
    frame_options.columnconfigure(0, weight=1)

    creativity_var = tk.DoubleVar(value=0.8)
    creativity_row = ttk.Frame(frame_options)
    creativity_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 4))
    ttk.Label(creativity_row, text="Creativity (variation between runs):").pack(side=tk.LEFT)
    creativity_label = ttk.Label(creativity_row, text="0.8")
    creativity_label.pack(side=tk.LEFT, padx=(4, 0))

    def on_creativity_change(v):
        val = round(float(v) * 10) / 10
        creativity_var.set(val)
        creativity_label.config(text=str(val))

    ttk.Scale(
        frame_options,
        from_=0.0,
        to=1.5,
        orient=tk.HORIZONTAL,
        variable=creativity_var,
        command=on_creativity_change,
    ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    ttk.Label(frame_options, text="Negative prompt (what to avoid):").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(12, 4)
    )
    neg_frame = ttk.Frame(frame_options)
    neg_frame.grid(row=8, column=0, columnspan=2, sticky="nsew", pady=(0, 0))
    frame_options.rowconfigure(8, weight=1)
    neg_frame.columnconfigure(0, weight=1)
    neg_frame.rowconfigure(0, weight=1)
    neg_scroll = ttk.Scrollbar(neg_frame)
    negative_prompt_text = tk.Text(neg_frame, height=6, width=50, wrap=tk.WORD, yscrollcommand=neg_scroll.set)
    neg_scroll.config(command=negative_prompt_text.yview)
    negative_prompt_text.grid(row=0, column=0, sticky="nsew")
    neg_scroll.grid(row=0, column=1, sticky="ns")
    if NEGATIVE_PROMPT_PATH.exists():
        try:
            negative_prompt_text.insert("1.0", NEGATIVE_PROMPT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    def save_negative_prompt():
        try:
            NEGATIVE_PROMPT_PATH.write_text(
                negative_prompt_text.get("1.0", tk.END).strip(), encoding="utf-8"
            )
        except Exception:
            pass

    def get_selected_prompt_text():
        if not prompts:
            return ""
        name = prompt_var.get()
        for p in prompts:
            if p["name"] == name:
                return p["prompt"]
        return prompts[0]["prompt"]

    # Appended to every prompt so the model only outputs a list of names, nothing else.
    PROMPT_GUARDRAILS = (
        " Reply with only the list of names: one name per line, no numbering, no bullets, "
        "no introductions or other text. Do not include any commentary, explanations, or text "
        "besides the names themselves. Every name must be unique; do not repeat any name."
    )

    # One is picked at random each time so the prompt is never identical (reduces repeated name lists).
    VARIATION_PHRASES = (
        "Vary your choices.",
        "Try unexpected options.",
        "Use a different style this time.",
        "Avoid the most obvious answers.",
        "Be creative and varied.",
        "Surprise me with unusual picks.",
        "Mix it up.",
        "Go for variety.",
    )

    def build_prompt_with_count(
        prompt_text: str,
        n: int,
        min_chars: int | None = None,
        max_chars: int | None = None,
        negative_prompt: str = "",
    ) -> str:
        """Build prompt: prepend count, strip old 'Generate N', add constraints and guardrails so output is only a list of names."""
        rest = re.sub(r"^Generate\s+\d+\s*", "", prompt_text.strip(), flags=re.IGNORECASE)
        out = f"Generate {n} {rest}".strip()
        if min_chars is not None and max_chars is not None:
            lo, hi = min(min_chars, max_chars), max(min_chars, max_chars)
            out += f" Each name must be between {lo} and {hi} characters in length."
        if negative_prompt.strip():
            out += " Avoid: " + negative_prompt.strip()
        out += " " + random.choice(VARIATION_PHRASES)
        out += PROMPT_GUARDRAILS
        return out

    last_generation = {}

    def do_regenerate_from_popup(update_names_fn):
        """Run generation with last params and call update_names_fn(names, error_msg) on the main thread."""
        if not last_generation:
            root.after(0, lambda: update_names_fn([], "No previous generation."))
            return
        prompt_text = last_generation.get("prompt_text", "")
        model = last_generation.get("model", "llama2")
        temperature = last_generation.get("temperature", 0.8)
        if not prompt_text:
            root.after(0, lambda: update_names_fn([], "No previous generation."))
            return

        def work():
            err = None
            names = []
            try:
                raw = generate_names(prompt_text, model=model, temperature=temperature)
                names = parse_names(raw)
            except Exception as e:
                err = str(e)

            def done():
                if err:
                    msg = err
                    if "not found" in err.lower():
                        msg += " Install with: ollama pull " + model.split(":")[0]
                    update_names_fn([], msg)
                else:
                    update_names_fn(names, None)

            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def do_generate():
        prompt_text = get_selected_prompt_text()
        if not prompt_text:
            status_var.set("Add or select a prompt first.")
            return
        n = max(1, min(100, num_names_var.get()))
        min_chars = max_chars = None
        if char_limit_var.get():
            min_chars = max(1, min(30, min_chars_var.get()))
            max_chars = max(1, min(50, max_chars_var.get()))
        negative_prompt = negative_prompt_text.get("1.0", tk.END).strip()
        prompt_text = build_prompt_with_count(prompt_text, n, min_chars, max_chars, negative_prompt)
        model = model_var.get().strip() or "llama2"
        temperature = max(0.0, min(2.0, float(creativity_var.get())))

        last_generation["prompt_text"] = prompt_text
        last_generation["model"] = model
        last_generation["temperature"] = temperature

        generate_btn.config(state="disabled")
        status_var.set("Generating…")

        def work():
            err = None
            names = []
            try:
                raw = generate_names(prompt_text, model=model, temperature=temperature)
                names = parse_names(raw)
            except Exception as e:
                err = str(e)

            def done():
                update_generate_button_state()
                if err:
                    msg = err
                    if "not found" in err.lower():
                        msg += " Install with: ollama pull " + model.split(":")[0]
                    status_var.set(msg)
                    return
                status_var.set(f"Generated {len(names)} names.")
                _names_result_window(root, names, on_regenerate=do_regenerate_from_popup)

            root.after(0, done)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

    generate_btn.config(command=do_generate)

    # Center main window on screen
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

    def on_closing():
        save_negative_prompt()
        _save_selected_prompt(prompt_var.get().strip())
        _save_selected_model(model_var.get().strip())
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    run_app()
