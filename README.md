# Legion 3D Enabler

A small, sleek desktop tool for the **Lenovo Legion 9i** (3D display model).

Lenovo's own "3D Engine" app only lets a handful of whitelisted games use the
laptop's 3D screen. Under the hood, all it really does is drop a small set of
support files into a game's install folder (next to the `.exe`) and let you
tweak the 3D settings from there.

**Legion 3D Enabler** automates that: scan for your installed games, pick
one, click a button, and 3D support is copied straight into that game's
folder — no manual file copying, no whitelist. It sources the support files
live from your Lenovo Game Engine install every time you enable 3D, so it's
always in sync with whatever Lenovo shipped — nothing is bundled with this
tool, and nothing goes stale.

## Features

- 🔍 **Scan for games** — automatically finds installs from Steam (all
  library folders), Epic Games, and GOG, plus any folder you add manually.
- 🖱️ **One-click Enable / Disable 3D** — copies the 3D support files into
  the selected game's folder, and remembers exactly what it copied so
  disabling removes only those files, nothing else.
- 🎯 **Per-game tuning** — automatically picks up the matching profile from
  Lenovo's own `Config` folder (depth, convergence, eye-delay settings) for
  each game, falling back to Lenovo's `Default` profile if a game has none.
- 🖱️🖱️ **Double-click a game** in the list to instantly toggle its 3D
  status.
- 🎮 **Open Game Center** — launches Lenovo's Game Center directly from the
  app.
- ▶️ **Launch Game** — starts the selected game, and if it has 3D enabled,
  automatically launches Game Center alongside it.
- ⚙️ **Settings** — if the app can't auto-detect your Lenovo install, point
  it at the right folders yourself, with a tooltip on each field explaining
  exactly what's expected inside.
- 🎨 Small, dark, distraction-free interface — a handful of buttons, nothing
  more.

## Important

**Game Center must stay running in the background** for the 3D effect to
actually work in-game, even after Legion 3D Enabler has copied the support
files into a game's folder. The app reminds you of this on screen, but it's
worth repeating here: enabling 3D only places the files — Game Center is
still what drives the 3D display while you play.

## Requirements

- Windows (Lenovo Legion 9i or another Legion model with the 3D display)
- **Lenovo's Game Engine / 3D Studio already installed** — this tool reads
  its files live and doesn't work without it
- [Python 3.9+](https://www.python.org/) if running from source or building
  it yourself (not required if you're just using a pre-built `.exe`)

## Getting Started

### Option 1 — Run from source

1. Install Python 3.9+ (check "Add to PATH" during install).
2. Clone or download this repo.
3. Run:
   ```
   python legion_3d_enabler_release.py
   ```

### Option 2 — Build a standalone `.exe`

1. Put these files together in one folder:
   - `legion_3d_enabler_release.py`
   - `build_release.bat`
   - `icon.ico`
   - `icon.png`
2. Double-click `build_release.bat`. It installs PyInstaller if needed and
   builds the executable.
3. Grab `Legion 3D Enabler.exe` from the new `dist` folder and move it
   anywhere you like.

## Usage

1. Launch **Legion 3D Enabler**.
2. Click **Scan for Games** (or **+ Add Folder** for anything it misses).
3. Select a game from the list.
4. Click **Enable 3D** (or double-click the game) to copy the support files
   into its folder. Click **Disable 3D** to cleanly remove them again.
5. Use **🎮 Open Game Center** to start Lenovo's Game Center, or
   **▶ Launch Game** to start the selected game directly — if that game has
   3D enabled, Game Center launches automatically alongside it.
6. Keep Game Center running while you play.

If the app can't find your Lenovo install automatically, open **⚙ Settings**
and point it at the correct folder(s) yourself — each field has a tooltip
(hover the ⓘ) explaining exactly what's expected inside.

## About

- **Version:** 1.1
- **Created by:** [WillemWavy](https://github.com/WillemWavy)
- **Repository:** https://github.com/WillemWavy/Legion-3D-Enabler
