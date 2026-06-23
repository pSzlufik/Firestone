# Firestone bot (Python port)

Cross-platform automation for the idle-RPG **Firestone**, rewritten from an
old Linux `bash` + `xdotool` script into Python + [pyautogui] so it runs on
Windows, macOS and Linux.

The original hardcoded mouse coordinates for one 1920×1080 layout. This port
stores every coordinate in a **reference resolution** and rescales it to the
live game window at run time, so the same config works across resolutions and
machines. A small **setup GUI** lets you recalibrate any point by hovering over
it in the game — no JSON editing required.

> ⚠️ Automating a game may violate its terms of service. Use on your own
> account at your own risk. This is a personal tool.

## Files

| File | What it is |
|------|-----------|
| `firestone_bot.py` | The bot engine + CLI. A faithful port of the original `DFSD.sh`. |
| `setup_gui.py` | Tkinter GUI to capture/calibrate coordinates into `config.json`. |
| `config.example.json` | Default coordinates (in 1920×1080 reference space) + run profiles. |
| `config.json` | Your calibrated copy (git-ignored; created by the setup GUI). |
| `original_bash/` | The original Linux scripts, kept for reference. |

## Launcher bar (pin to taskbar)

`launcher.pyw` is a small control bar — **Setup** (opens the calibration GUI),
a profile/sequence picker with **Run** / **Stop** / a `bg` (background) toggle /
`reps`, and a folder button.

- Just run it: double-click `launcher.pyw`, or `pythonw launcher.pyw`.
- Make a pinnable **Firestone.exe**:
  ```
  powershell -ExecutionPolicy Bypass -File build_exe.ps1
  ```
  Then right-click `Firestone.exe` → **Pin to taskbar**. (`make_shortcut.ps1`
  drops a Desktop shortcut you can pin instead.)

The `.exe` is just the launcher — Python with the dependencies installed still
needs to be present, since it runs the scripts. It's git-ignored (built
per-machine), so run `build_exe.ps1` on each PC.

## Setup

1. Install Python 3.9+ and the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Start Firestone (any resolution). Make sure its window title contains
   `Firestone`.
3. Calibrate:
   ```
   python setup_gui.py
   ```
   - Click **Detect window**.
   - For each point: click **Capture**, hover the matching spot in the game,
     press **F8** (or wait for the 3-second countdown). **Test** moves your
     mouse to a stored point so you can confirm it.
   - Click **Save config.json**.

   You don't have to capture every point in one go — the defaults are a sane
   1920×1080 starting set. Fix the ones that are off for your layout.

## Build your own positions (Builder tab)

The **Builder** tab in `setup_gui.py` starts empty and lets you define your own
elements:

- **point** — one captured coordinate. Click "Add point", name it, hover the
  spot in-game, press F8 (or wait for the countdown).
- **area** — click "Add area", name it, then **drag a rectangle** over the
  region on a translucent overlay. The bot sweeps that rectangle as a grid of
  clicks (top-left → bottom-right) stepping by an **offset** (dx, dy) you set —
  ideal for the map's non-deterministic mission spots or war-machine runs where
  you must click everywhere to be sure. After **each** cell it performs the
  area's **meantime clicks** (extra points you capture, e.g. an "accept mission"
  button then a "close window" button). "Show grid" previews every click
  position (blue) and meantime clicks (orange).

Run an element:

```
python firestone_bot.py --element <name> --reps N
```

Elements can also be dropped into a sequence (action **element**), so you can
mix single clicks, keys, waits and whole area-sweeps into one routine.

## Build your own routine (Sequence editor)

The **Sequence** tab in `setup_gui.py` lets you compose a custom action cycle
from drop-downs instead of the built-in loop: pick an **action**
(click / double click / right click / move / key / scroll / wait) and a
**target point**, "Add step", reorder with Up/Down, name it, and **Save
sequence**. Run it with:

```
python firestone_bot.py --sequence example_guardian --reps 5
```

Sequences live under `"sequences"` in the config. Targets can be any point name
or an array element like `guardian_pos[0]`. For `key` use the letter (e.g. `g`,
`L`); for `wait` use seconds; for `scroll` use notches (+up / −down).

## Run

```
python firestone_bot.py --list                 # show profiles AND sequences
python firestone_bot.py --profile default      # run the built-in main loop
python firestone_bot.py --sequence NAME --reps N   # run your custom sequence
python firestone_bot.py --func guardian 2      # run one built-in action once
```

A countdown gives you a few seconds to click into the game window first.

**Stop the bot at any time:** slam the mouse pointer into a screen corner
(pyautogui fail-safe) or press **Ctrl+C** in the terminal.

## Background mode (don't take over my mouse)

By default the bot drives your **real cursor** (foreground mode), so it takes
over the mouse while running. There's also an experimental **background mode**
(Windows only) that injects input straight into the game window via Win32
`PostMessage`, leaving your cursor free to use the PC meanwhile:

```
python firestone_bot.py --profile default --background
```

⚠️ **It may or may not work for Firestone.** Many games read *raw* hardware
input and ignore posted messages — keypresses tend to work more often than
clicks. **Test it before trusting a full run:**

```
# With the game open but NOT focused (click another window first):
python firestone_bot.py --background --func probe alch_db
```

Watch the game: if the bot's click registers (the spot reacts) while your
cursor stays put, background mode works and you can use `--background` on real
runs. If nothing happens in-game, the game is ignoring posted input — stick
with foreground mode (or the VM / second-session route). Try a key action too,
e.g. `--func guardian 1`, since keys often work even when clicks don't.

Notes for background mode:
- The fail-safe corner-abort doesn't apply (your cursor isn't moving) — use
  **Ctrl+C** to stop.
- The game window must be open and not minimized, but it does **not** need to
  be focused or on the active virtual desktop.

## How the original maps to this port

| Original (`xdotool`) | Here |
|----------------------|------|
| `search --name Firestone windowactivate` | `GameWindow.activate()` |
| `mousemove --window WID X Y` (window-relative) | reference coords → `to_screen()` |
| `click --repeat N --delay D 1` | `click(..., clicks=N, delay=D)` |
| `click 4` / `click 5` (scroll up/down) | `scroll(..., +/-)` |
| `key M` / `key L` (Shift+letter) | `key("M")` sends Shift+m |
| `mousedown` … `mouseup` (drag) | `drag()` |
| `run reps server lvl ...` args | `profiles` in the config |

The level-gated cycle (guardian → expeditions → library → tavern → campaign →
engineer → alchemy → oracle, with a map pass every 3rd rep and optional
server-swap) is preserved exactly. Profile parameters mirror the original
`run` arguments:

- `alchemy` / `swap_alchemy`: `"DB;dust;coins"` (each 0 or 1)
- `fs_tree` / `swap_fs_tree`: `"tree;node1;node2"` (fire-stone tree upgrades)

[pyautogui]: https://pyautogui.readthedocs.io/
