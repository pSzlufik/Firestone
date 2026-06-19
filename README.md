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

## Run

```
python firestone_bot.py --list                 # show profiles
python firestone_bot.py --profile default      # run the main loop
python firestone_bot.py --func guardian 2      # run one action once (for testing)
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
