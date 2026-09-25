"""
Legion 3D Enabler (Release)
---------------------------
A small, sleek desktop tool for the Lenovo Legion 9i (3D display model).

What it does
============
Lenovo's own "3D Engine" app only lets a handful of whitelisted games use the
laptop's 3D screen. Under the hood, all it really does is drop a small set of
support files into a game's install folder (next to the .exe) and let you
tweak the 3D settings from there.

This tool automates that:
  1. It sources the support files live from your Lenovo Game Engine install
     (its GameDll, Hotkey, and Config folders) every time you enable 3D, so
     it's always in sync with whatever Lenovo shipped. Nothing is bundled or
     baked in - this tool requires Lenovo's Game Engine to already be
     installed. If it can't auto-detect the install location, point it at
     the right folders yourself in Settings.
  2. Scan for installed games (Steam / Epic / GOG / manual folders).
  3. Select a game, click "Enable 3D" -> the files are copied into that
     game's folder. Click "Disable 3D" to remove exactly what was copied.

Requires: Python 3.9+ (standard library only - no extra installs needed) and
a working Lenovo Game Engine install.
Run with:  python legion_3d_enabler_release.py
Or build a standalone .exe - see build_release.bat / README included
alongside this file.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
import winreg
from pathlib import Path
from tkinter import Tk, Toplevel, StringVar, PhotoImage, filedialog, messagebox
from tkinter import ttk


class ToolTip:
    """Minimal hover tooltip for a widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=ACCENT)
        ttk.Label(
            tw, text=self.text, background=BG_PANEL, foreground=TEXT,
            font=FONT, padding=8, justify="left",
        ).pack(padx=1, pady=1)

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

APP_NAME = "Legion 3D Enabler"
APP_VERSION = "1.1"
APP_CREATOR = "WillemWavy"
APP_GITHUB_URL = "https://github.com/WillemWavy/Legion-3D-Enabler"

DEFAULT_GAME_ENGINE_ROOT = r"C:\Program Files\Lenovo\Lenovo 3D Studio\Game Engine"

# These three files are game-specific tuning (depth, convergence, eye delay).
# They always come from Lenovo's own Config folder - the subfolder matching
# this game's exe name if one exists, otherwise the "Default" subfolder.
OVERRIDE_FILENAMES = ("ReShade.ini", "ReShadePreset.ini", "EyePreDelay.ini")

# Tooltip text shown in Settings next to each folder field, so it's clear
# what's actually expected to be inside the folder you point it at.
GAMEDLL_HELP = (
    "Should contain: GameBridge.addon, GB.fx, ReShade.fxh, ReShade64.dll,\n"
    "SuperDepth3D.fx, and a \"weave\" subfolder with boe_ET_Predict.dll and\n"
    "Runtime_BOE_18NBSDK_ETDX.dll."
)
HOTKEY_HELP = "Should contain: Hotkey.ini"
CONFIG_HELP = (
    "Should contain one subfolder per game (named after that game's .exe,\n"
    "e.g. \"Cyberpunk2077\") plus a \"Default\" subfolder - each holding\n"
    "ReShade.ini, ReShadePreset.ini, and EyePreDelay.ini."
)
ENGINE_ROOT_HELP = (
    "Used to launch Game Center, and as the default location for the\n"
    "GameDll, Hotkey, and Config folders below if you leave those blank."
)

# Where the program itself lives - works both when run as a .py script and
# when run as a frozen .exe (PyInstaller sets sys.frozen + sys.executable).
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# The icon (window titlebar icon + exe file icon). Baked into the build via
# build_release.bat.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ICON_DIR = Path(sys._MEIPASS)
else:
    ICON_DIR = BASE_DIR
ICON_ICO_PATH = ICON_DIR / "icon.ico"
ICON_PNG_PATH = ICON_DIR / "icon.png"

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Legion3DEnabler"
CONFIG_FILE = CONFIG_DIR / "config.json"
MANIFEST_NAME = ".legion3d_manifest.json"

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG = "#111318"
BG_PANEL = "#181b22"
BG_ROW_ALT = "#1e222b"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#8f73ff"
GREEN = "#3ddc84"
RED = "#ff5c5c"
TEXT = "#e8e9ee"
SUBTEXT = "#8b8fa3"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------
def load_config():
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    else:
        cfg = {}
    cfg.setdefault("extra_folders", [])
    cfg.setdefault("game_engine_root", "")  # empty = use DEFAULT_GAME_ENGINE_ROOT
    cfg.setdefault("gamedll_dir_override", "")  # empty = <engine root>\GameDll
    cfg.setdefault("hotkey_dir_override", "")  # empty = <engine root>\Hotkey
    cfg.setdefault("config_dir_override", "")  # empty = <engine root>\Config
    return cfg


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def get_engine_root(cfg):
    override = (cfg.get("game_engine_root") or "").strip()
    return Path(override) if override else Path(DEFAULT_GAME_ENGINE_ROOT)


def get_gamedll_dir(cfg):
    override = (cfg.get("gamedll_dir_override") or "").strip()
    return Path(override) if override else get_engine_root(cfg) / "GameDll"


def get_hotkey_dir(cfg):
    override = (cfg.get("hotkey_dir_override") or "").strip()
    return Path(override) if override else get_engine_root(cfg) / "Hotkey"


def get_config_dir(cfg):
    override = (cfg.get("config_dir_override") or "").strip()
    return Path(override) if override else get_engine_root(cfg) / "Config"


# ---------------------------------------------------------------------------
# Game discovery
# ---------------------------------------------------------------------------
def steam_library_folders():
    """Find Steam's library folders via the registry + libraryfolders.vdf."""
    libs = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        steam_path = Path(steam_path)
        libs.append(steam_path / "steamapps" / "common")
        vdf = steam_path / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            text = vdf.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith('"path"'):
                    parts = line.split('"')
                    if len(parts) >= 4:
                        libs.append(Path(parts[3]) / "steamapps" / "common")
    except Exception:
        pass
    # Common fallback locations
    for guess in [
        r"C:\Program Files (x86)\Steam\steamapps\common",
        r"C:\Program Files\Steam\steamapps\common",
    ]:
        libs.append(Path(guess))
    seen, out = set(), []
    for p in libs:
        if p.exists() and str(p) not in seen:
            seen.add(str(p))
            out.append(p)
    return out


def default_scan_roots():
    roots = steam_library_folders()
    for guess in [
        r"C:\Program Files\Epic Games",
        r"C:\Program Files (x86)\Epic Games",
        r"C:\GOG Games",
        r"C:\Program Files (x86)\GOG Games",
    ]:
        p = Path(guess)
        if p.exists():
            roots.append(p)
    return roots


IGNORE_EXE_HINTS = (
    "unins", "crashhandler", "crashreport", "vc_redist", "redist",
    "directx", "dxsetup", "setup", "installer", "easyanticheat",
    "battleye", "vcredist",
)


def find_main_exe(game_folder: Path):
    """Best-effort guess at the game's main executable."""
    candidates = []
    try:
        for exe in game_folder.rglob("*.exe"):
            name = exe.name.lower()
            if any(hint in name for hint in IGNORE_EXE_HINTS):
                continue
            try:
                size = exe.stat().st_size
            except OSError:
                continue
            candidates.append((size, exe))
    except Exception:
        pass
    if not candidates:
        return None
    candidates.sort(reverse=True)  # largest .exe first, usually the game
    return candidates[0][1]


def scan_for_games(roots):
    games = []
    for root in roots:
        if not root.exists():
            continue
        try:
            subfolders = [f for f in root.iterdir() if f.is_dir()]
        except Exception:
            continue
        for folder in subfolders:
            exe = find_main_exe(folder)
            if exe:
                games.append({"name": folder.name, "folder": str(exe.parent), "exe": str(exe)})
    return games


def is_enabled(game_folder: str):
    return (Path(game_folder) / MANIFEST_NAME).exists()


def find_config_profile_dir(config_dir: Path, exe_stem: str):
    """Return the per-game folder in Lenovo's Config directory that matches
    this game's exe name (exact match, case-insensitive). Falls back to the
    "Default" subfolder if no game-specific one exists."""
    if not config_dir.exists():
        return None
    exe_stem_lower = exe_stem.lower()
    match = None
    default = None
    try:
        for sub in config_dir.iterdir():
            if not sub.is_dir():
                continue
            if sub.name.lower() == exe_stem_lower:
                match = sub
            elif sub.name.lower() == "default":
                default = sub
    except Exception:
        pass
    return match or default


def _copy_flattened(src_folder: Path, dst: Path, rename_map: dict = None):
    """Copy every FILE found anywhere under src_folder directly into dst,
    ignoring subfolder structure (e.g. GameDll's "weave" subfolder's DLLs
    land straight next to the game's exe, not in a "weave" subfolder).
    rename_map (lowercase source name -> new name) renames specific files
    on the way in, e.g. ReShade64.dll -> dxgi.dll so the game actually
    loads it as its graphics API proxy DLL."""
    rename_map = rename_map or {}
    copied = []
    for item in src_folder.rglob("*"):
        if item.is_file():
            dest_name = rename_map.get(item.name.lower(), item.name)
            shutil.copy2(item, dst / dest_name)
            copied.append(dest_name)
    return copied


# GameDll ships ReShade's proxy DLL under its generic build name. It only
# gets loaded by the game if it's named after the graphics API DLL the game
# actually imports - for DirectX 10/11/12 titles (the common case here)
# that's dxgi.dll.
GAMEDLL_RENAME_MAP = {"reshade64.dll": "dxgi.dll"}


# ---------------------------------------------------------------------------
# Enable / Disable
# ---------------------------------------------------------------------------
def enable_3d(game: dict, cfg: dict):
    dst = Path(game["folder"])
    copied = []

    game_dll_dir = get_gamedll_dir(cfg)
    hotkey_dir = get_hotkey_dir(cfg)
    config_dir = get_config_dir(cfg)

    missing = [str(p) for p in (game_dll_dir, hotkey_dir, config_dir) if not p.exists()]
    if missing:
        raise RuntimeError(
            "Couldn't find:\n" + "\n".join(missing) + "\n\nSet the correct folder(s) in Settings."
        )

    copied.extend(_copy_flattened(game_dll_dir, dst, rename_map=GAMEDLL_RENAME_MAP))
    copied.extend(_copy_flattened(hotkey_dir, dst))

    profile_dir = find_config_profile_dir(config_dir, Path(game["exe"]).stem)
    config_profile = profile_dir.name if profile_dir else None
    if profile_dir:
        for fname in OVERRIDE_FILENAMES:
            override_file = profile_dir / fname
            if override_file.exists():
                shutil.copy2(override_file, dst / fname)
                if fname not in copied:
                    copied.append(fname)

    if not copied:
        raise RuntimeError(
            f"Nothing found to copy in:\n{game_dll_dir}\n{hotkey_dir}\n{config_dir}\n\n"
            "Check the folders in Settings."
        )

    manifest = dst / MANIFEST_NAME
    manifest.write_text(
        json.dumps({"files": copied, "config_profile": config_profile}, indent=2),
        encoding="utf-8",
    )
    return {"config_profile": config_profile}


def disable_3d(game_folder: str):
    dst = Path(game_folder)
    manifest = dst / MANIFEST_NAME
    if not manifest.exists():
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for fname in data.get("files", []):
            f = dst / fname
            if f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
            elif f.exists():
                f.unlink()
    finally:
        manifest.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class LegionApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.games = []
        self.selected_index = None

        root.title(f"{APP_NAME} v{APP_VERSION}")
        root.geometry("700x800")
        root.configure(bg=BG)
        root.minsize(620, 680)
        root.resizable(True, True)

        if ICON_PNG_PATH.exists():
            try:
                self._icon_img = PhotoImage(file=str(ICON_PNG_PATH))  # keep a reference alive
                root.iconphoto(True, self._icon_img)
            except Exception:
                pass
        elif ICON_ICO_PATH.exists():
            try:
                root.iconbitmap(default=str(ICON_ICO_PATH))
            except Exception:
                pass

        self._build_style()
        self._build_ui()

    def toggle_maximize(self, _event=None):
        try:
            is_zoomed = self.root.state() == "zoomed"
            self.root.state("normal" if is_zoomed else "zoomed")
        except Exception:
            pass

    # -- styling -----------------------------------------------------------
    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("Sub.TLabel", background=BG, foreground=SUBTEXT, font=FONT)
        style.configure(
            "Accent.TButton", background=ACCENT, foreground="white",
            font=FONT_BOLD, padding=10, borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", "#3a3d47")])
        style.configure(
            "Ghost.TButton", background=BG_PANEL, foreground=TEXT,
            font=FONT, padding=8, borderwidth=0,
        )
        style.map("Ghost.TButton", background=[("active", "#242833")])
        style.configure(
            "Danger.TButton", background=RED, foreground="white",
            font=FONT_BOLD, padding=10, borderwidth=0,
        )
        style.map("Danger.TButton", background=[("active", "#ff7676"), ("disabled", "#3a3d47")])

    # -- layout --------------------------------------------------------------
    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(20, 18, 20, 10))
        header.pack(fill="x")
        header.bind("<Double-Button-1>", self.toggle_maximize)
        title_label = ttk.Label(header, text="Legion 3D Enabler", style="Title.TLabel")
        title_label.pack(side="left")
        title_label.bind("<Double-Button-1>", self.toggle_maximize)
        ttk.Button(header, text="ℹ About", style="Ghost.TButton", command=self.show_about).pack(side="right", padx=(0, 8))
        ttk.Button(header, text="⚙ Settings", style="Ghost.TButton", command=self.show_settings).pack(side="right", padx=(0, 8))

        toolbar = ttk.Frame(self.root, padding=(20, 0, 20, 10))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="🔍 Scan for Games", style="Accent.TButton", command=self.scan_games).pack(side="left")
        ttk.Button(toolbar, text="+ Add Folder", style="Ghost.TButton", command=self.add_manual_game).pack(side="left", padx=(10, 0))

        list_panel = ttk.Frame(self.root, style="Panel.TFrame", padding=1)
        list_panel.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.tree = ttk.Treeview(
            list_panel, columns=("status",), show="tree headings", selectmode="browse", height=14
        )
        self.tree.heading("#0", text="Game")
        self.tree.heading("status", text="3D Status")
        self.tree.column("#0", width=380)
        self.tree.column("status", width=140, anchor="center")
        style = ttk.Style()
        style.configure(
            "Treeview", background=BG_PANEL, fieldbackground=BG_PANEL,
            foreground=TEXT, borderwidth=0, rowheight=30, font=FONT,
        )
        style.configure("Treeview.Heading", background=BG_PANEL, foreground=SUBTEXT, font=FONT_BOLD, borderwidth=0)
        style.map("Treeview", background=[("selected", ACCENT)])
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-Button-1>", self.on_double_click)

        actions = ttk.Frame(self.root, padding=(20, 0, 20, 8))
        actions.pack(fill="x")
        self.enable_btn = ttk.Button(actions, text="Enable 3D", style="Accent.TButton", command=self.on_enable, state="disabled")
        self.enable_btn.pack(side="left")
        self.disable_btn = ttk.Button(actions, text="Disable 3D", style="Danger.TButton", command=self.on_disable, state="disabled")
        self.disable_btn.pack(side="left", padx=(10, 0))

        actions2 = ttk.Frame(self.root, padding=(20, 0, 20, 8))
        actions2.pack(fill="x")
        self.game_center_btn = ttk.Button(actions2, text="🎮 Open Game Center", style="Ghost.TButton", command=self.on_open_game_center)
        self.game_center_btn.pack(side="left")
        self.launch_btn = ttk.Button(actions2, text="▶ Launch Game", style="Accent.TButton", command=self.on_launch_game, state="disabled")
        self.launch_btn.pack(side="left", padx=(10, 0))

        ttk.Label(
            self.root,
            text="⚠ Keep Game Center running in the background - it has to stay open for the 3D effect to work in-game.",
            style="Sub.TLabel",
            padding=(20, 0, 20, 6),
            wraplength=660,
        ).pack(fill="x")

        self.status_var = StringVar(value=self._status_line())
        ttk.Label(self.root, textvariable=self.status_var, style="Sub.TLabel", padding=(20, 0, 20, 14)).pack(fill="x")

    def _status_line(self):
        missing = [
            name for name, folder in (
                ("GameDll", get_gamedll_dir(self.cfg)),
                ("Hotkey", get_hotkey_dir(self.cfg)),
                ("Config", get_config_dir(self.cfg)),
            )
            if not folder.exists()
        ]
        if missing:
            return f"⚠ Couldn't find: {', '.join(missing)} - set the correct folder(s) in Settings."
        return f"Live-sourcing from Game Engine: {get_engine_root(self.cfg)}"

    # -- actions -------------------------------------------------------------
    def show_about(self):
        win = Toplevel(self.root)
        win.title(f"About {APP_NAME}")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        if getattr(self, "_icon_img", None) is not None:
            try:
                win.iconphoto(False, self._icon_img)
            except Exception:
                pass

        pad = ttk.Frame(win, padding=(28, 24, 28, 20))
        pad.pack(fill="both", expand=True)

        ttk.Label(pad, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(pad, text=f"Version {APP_VERSION}", style="Sub.TLabel").pack(anchor="w", pady=(2, 14))
        ttk.Label(pad, text=f"Created by {APP_CREATOR}", style="TLabel").pack(anchor="w")

        link = ttk.Label(pad, text=APP_GITHUB_URL, style="TLabel", foreground=ACCENT, cursor="hand2")
        link.pack(anchor="w", pady=(4, 18))
        link.bind("<Button-1>", lambda _e: webbrowser.open(APP_GITHUB_URL))

        ttk.Button(pad, text="Close", style="Accent.TButton", command=win.destroy).pack(anchor="e")

        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    def _settings_field(self, pad, label_text, help_text, value):
        """Build one labeled path field + Browse button + hover tooltip.
        Returns the StringVar backing the entry."""
        row_label = ttk.Frame(pad)
        row_label.pack(fill="x", pady=(0, 2))
        ttk.Label(row_label, text=label_text, style="TLabel").pack(side="left")
        info = ttk.Label(row_label, text=" ⓘ", style="Sub.TLabel", cursor="question_arrow")
        info.pack(side="left")
        ToolTip(info, help_text)

        var = StringVar(value=value)
        path_row = ttk.Frame(pad)
        path_row.pack(fill="x", pady=(0, 16))
        ttk.Entry(path_row, textvariable=var, width=44).pack(side="left", fill="x", expand=True)

        def browse():
            folder = filedialog.askdirectory(title=f"Select the {label_text}", initialdir=var.get() or str(BASE_DIR))
            if folder:
                var.set(folder)

        ttk.Button(path_row, text="Browse...", style="Ghost.TButton", command=browse).pack(side="left", padx=(8, 0))
        return var

    def show_settings(self):
        win = Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        if getattr(self, "_icon_img", None) is not None:
            try:
                win.iconphoto(False, self._icon_img)
            except Exception:
                pass

        pad = ttk.Frame(win, padding=(28, 24, 28, 20))
        pad.pack(fill="both", expand=True)

        ttk.Label(pad, text="Settings", style="Title.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            pad,
            text="Hover the ⓘ next to a field to see what's expected in that folder.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        engine_var = self._settings_field(
            pad, "Game Engine folder", ENGINE_ROOT_HELP, str(get_engine_root(self.cfg))
        )
        gamedll_var = self._settings_field(
            pad, "GameDll folder (optional override)", GAMEDLL_HELP, self.cfg.get("gamedll_dir_override", "")
        )
        hotkey_var = self._settings_field(
            pad, "Hotkey folder (optional override)", HOTKEY_HELP, self.cfg.get("hotkey_dir_override", "")
        )
        config_var = self._settings_field(
            pad, "Config folder (optional override)", CONFIG_HELP, self.cfg.get("config_dir_override", "")
        )

        def do_save():
            self.cfg["game_engine_root"] = engine_var.get().strip()
            self.cfg["gamedll_dir_override"] = gamedll_var.get().strip()
            self.cfg["hotkey_dir_override"] = hotkey_var.get().strip()
            self.cfg["config_dir_override"] = config_var.get().strip()
            save_config(self.cfg)
            self.status_var.set(self._status_line())
            win.destroy()

        btn_row = ttk.Frame(pad)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="Cancel", style="Ghost.TButton", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text="Save", style="Accent.TButton", command=do_save).pack(side="right", padx=(0, 8))

        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    def scan_games(self):
        self.status_var.set("Scanning…")
        self.root.update_idletasks()

        def worker():
            roots = default_scan_roots() + [Path(f) for f in self.cfg.get("extra_folders", [])]
            found = scan_for_games(roots)
            self.root.after(0, lambda: self._populate(found))

        threading.Thread(target=worker, daemon=True).start()

    def add_manual_game(self):
        folder = filedialog.askdirectory(title="Select the game's install folder")
        if not folder:
            return
        exe = find_main_exe(Path(folder))
        if not exe:
            messagebox.showwarning(APP_NAME, "Couldn't find an .exe in that folder.")
            return
        extras = self.cfg.setdefault("extra_folders", [])
        if folder not in extras:
            extras.append(folder)
            save_config(self.cfg)
        self._populate(scan_for_games(default_scan_roots() + [Path(f) for f in self.cfg["extra_folders"]]))

    def _populate(self, games):
        self.games = games
        self.tree.delete(*self.tree.get_children())
        for i, g in enumerate(games):
            status = "✓ Enabled" if is_enabled(g["folder"]) else "—"
            self.tree.insert("", "end", iid=str(i), text=g["name"], values=(status,))
        self.status_var.set(f"Found {len(games)} game(s).  {self._status_line()}")
        self.enable_btn.config(state="disabled")
        self.disable_btn.config(state="disabled")
        self.launch_btn.config(state="disabled")

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            self.selected_index = None
            self.enable_btn.config(state="disabled")
            self.disable_btn.config(state="disabled")
            self.launch_btn.config(state="disabled")
            return
        idx = int(sel[0])
        self.selected_index = idx
        enabled = is_enabled(self.games[idx]["folder"])
        self.enable_btn.config(state="disabled" if enabled else "normal")
        self.disable_btn.config(state="normal" if enabled else "disabled")
        self.launch_btn.config(state="normal")

    def on_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.selected_index = int(row_id)
        self.on_select(None)
        game = self.games[self.selected_index]
        if is_enabled(game["folder"]):
            self.on_disable()
        else:
            self.on_enable()

    def on_enable(self):
        if self.selected_index is None:
            return
        game = self.games[self.selected_index]
        try:
            result = enable_3d(game, self.cfg)
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))
            return
        self._refresh_row(self.selected_index)
        if result["config_profile"]:
            self.status_var.set(f"3D enabled for {game['name']} - using Config profile \"{result['config_profile']}\".")
        else:
            self.status_var.set(f"3D enabled for {game['name']} - using Game Engine files (no Config profile found).")

    def on_disable(self):
        if self.selected_index is None:
            return
        game = self.games[self.selected_index]
        disable_3d(game["folder"])
        self._refresh_row(self.selected_index)

    def on_open_game_center(self):
        self._launch_game_center(warn_if_missing=True)

    def _launch_game_center(self, warn_if_missing):
        path = get_engine_root(self.cfg) / "GameEngine.exe"
        if not path.exists():
            if warn_if_missing:
                messagebox.showwarning(
                    APP_NAME, f"Game Center wasn't found at:\n{path}\n\nSet the correct folder in Settings."
                )
            return False
        try:
            subprocess.Popen([str(path)], cwd=str(path.parent))
            return True
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Couldn't launch Game Center:\n{e}")
            return False

    def on_launch_game(self):
        if self.selected_index is None:
            return
        game = self.games[self.selected_index]
        if is_enabled(game["folder"]):
            self._launch_game_center(warn_if_missing=True)
        try:
            subprocess.Popen([game["exe"]], cwd=game["folder"])
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Couldn't launch the game:\n{e}")

    def _refresh_row(self, idx):
        game = self.games[idx]
        status = "✓ Enabled" if is_enabled(game["folder"]) else "—"
        self.tree.item(str(idx), values=(status,))
        self.on_select(None) if False else self.tree.selection_set(str(idx))
        self.on_select(None)


def main():
    root = Tk()
    LegionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
