#!/usr/bin/env python3
"""
Firestone automation bot — cross-platform Python port of the original
bash + xdotool script (DFSD.sh).

The original sent window-relative mouse moves / clicks / key presses to a
window titled "Firestone".  This port does the same with pyautogui, but stores
every coordinate as a position in a *reference* resolution (1920x1080 by
default).  At run time each reference coordinate is rescaled to the live game
window, so the same config works across resolutions and machines.

Calibrate the coordinates with setup_gui.py, then run a profile:

    python firestone_bot.py --profile default
    python firestone_bot.py --list                # show profiles
    python firestone_bot.py --func guardian 2     # run one action once

SAFETY: pyautogui's fail-safe is ON — slam the mouse into the top-left corner
of the screen to abort instantly.  Ctrl+C also stops the bot.
"""

import argparse
import json
import os
import re
import sys
import time

try:
    import pyautogui
except ImportError:
    sys.exit("pyautogui is not installed.  Run:  pip install -r requirements.txt")

# Window lookup is platform specific.  pygetwindow covers Windows (and some
# macOS); on Linux we fall back to wmctrl/xdotool via the shell.
try:
    import pygetwindow as gw
except Exception:  # pragma: no cover - optional on Linux
    gw = None

from backends import make_backend

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0  # we manage our own sleeps to mirror the original timing

HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
#  Window handling
# --------------------------------------------------------------------------- #
class GameWindow:
    """Locates the game window and converts reference coords to screen coords.

    `window` may be a specific pygetwindow object (e.g. chosen in the setup
    GUI's window picker) — that bypasses title matching entirely and is the
    reliable way to avoid grabbing some other window that merely has
    "Firestone" in its title (like a file-explorer folder)."""

    def __init__(self, title, reference_size, window=None):
        self.title = title
        self.ref_w, self.ref_h = reference_size
        self._window = window

    def _match(self):
        """Windows whose title contains self.title, exact matches preferred."""
        wins = [w for w in gw.getWindowsWithTitle(self.title) if w.title]
        exact = [w for w in wins if w.title == self.title]
        return exact or wins

    def rect(self):
        """Return (left, top, width, height) of the game window in screen px."""
        if self._window is not None:
            w = self._window
            return (w.left, w.top, w.width, w.height)
        if gw is not None:
            wins = self._match()
            if not wins:
                raise RuntimeError(
                    f"No window whose title contains {self.title!r} was found. "
                    "Is the game running and is the title set correctly in the config?"
                )
            w = wins[0]
            return (w.left, w.top, w.width, w.height)
        # Linux fallback via xdotool (if the user still has it).
        return self._rect_xdotool()

    def _rect_xdotool(self):
        import subprocess

        try:
            wid = subprocess.check_output(
                ["xdotool", "search", "--name", self.title]
            ).split()[0]
            geo = subprocess.check_output(
                ["xdotool", "getwindowgeometry", "--shell", wid]
            ).decode()
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Could not locate window via xdotool: {e}")
        vals = {}
        for line in geo.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = v
        return (int(vals["X"]), int(vals["Y"]), int(vals["WIDTH"]), int(vals["HEIGHT"]))

    def activate(self):
        if self._window is not None:
            try:
                if self._window.isMinimized:
                    self._window.restore()
                self._window.activate()
            except Exception:
                pass
            return
        if gw is not None:
            wins = self._match()
            if wins:
                try:
                    if wins[0].isMinimized:
                        wins[0].restore()
                    wins[0].activate()
                except Exception:
                    pass
        else:  # pragma: no cover
            import subprocess

            try:
                subprocess.call(
                    ["xdotool", "search", "--name", self.title, "windowactivate"]
                )
            except Exception:
                pass

    def to_screen(self, ref_x, ref_y):
        left, top, width, height = self.rect()
        x = left + (ref_x / self.ref_w) * width
        y = top + (ref_y / self.ref_h) * height
        return int(round(x)), int(round(y))

    def to_reference(self, screen_x, screen_y):
        """Inverse of to_screen — used by the setup GUI when capturing points."""
        left, top, width, height = self.rect()
        rx = (screen_x - left) / width * self.ref_w
        ry = (screen_y - top) / height * self.ref_h
        return int(round(rx)), int(round(ry))


# --------------------------------------------------------------------------- #
#  Bot
# --------------------------------------------------------------------------- #
class Firestone:
    def __init__(self, config, background=False):
        self.cfg = config
        self.points = config["points"]
        self.arrays = config["arrays"]
        self.mapcfg = config["map"]
        self.ref_w, self.ref_h = config["reference_size"]
        t = config["timing"]
        self.mult = t.get("global_multiplier", 1.0)
        self.t_short = t["short"]
        self.t_med = t["medium"]
        self.t_key = t["key"]
        self.t_fight = t.get("long_fight", 50)
        self.t_swap = t.get("server_swap_wait", 90)
        self.move_dur = t.get("move_duration", 0.0)
        self.backend = make_backend(config, background=background)

    # ---- low-level primitives (mirror the xdotool verbs) ------------------ #
    # All of these delegate to self.backend, so the same logic drives either the
    # foreground (real cursor) or background (PostMessage) input path.
    def sleep(self, seconds):
        time.sleep(seconds * self.mult)

    def focus(self):
        self.backend.activate()
        self.sleep(self.t_short)

    def move(self, ref_x, ref_y, after=0.0):
        self.backend.move(ref_x, ref_y)
        if after:
            self.sleep(after)

    def click(self, ref_x, ref_y, clicks=1, delay=0.0, button="left", after=0.0):
        """Move then click.  `delay` is the gap between repeated clicks (s)."""
        self.backend.move(ref_x, ref_y)
        self.sleep(self.t_med)
        for n in range(clicks):
            self.backend.mouse_down(ref_x, ref_y, button)
            self.backend.mouse_up(ref_x, ref_y, button)
            if delay and n < clicks - 1:
                self.sleep(delay)
        if after:
            self.sleep(after)

    def click_pt(self, name, **kw):
        rx, ry = self.points[name]
        self.click(rx, ry, **kw)

    def move_pt(self, name, **kw):
        rx, ry = self.points[name]
        self.move(rx, ry, **kw)

    def scroll(self, ref_x, ref_y, amount):
        """amount > 0 scrolls up, < 0 scrolls down (mirrors X11 button 4/5)."""
        self.backend.move(ref_x, ref_y)
        self.sleep(self.t_med)
        self.backend.scroll(ref_x, ref_y, amount)

    def key(self, k, after=None):
        """Send a hotkey.  Upper-case letters are sent as Shift+<letter>,
        matching `xdotool key M` / `xdotool key L`."""
        self.focus()
        self.backend.tap_key(k)
        self.sleep(self.t_key if after is None else after)

    def drag(self, x1, y1, x2, y2, relative=False):
        if relative:  # convert a reference-space relative move to absolute
            x2, y2 = x1 + x2, y1 + y2
        self.backend.move(x1, y1)
        self.sleep(self.t_med)
        self.backend.mouse_down(x1, y1)
        self.sleep(self.t_med)
        self.backend.move(x2, y2)
        self.sleep(self.t_med)
        self.backend.mouse_up(x2, y2)
        self.sleep(self.t_short)

    def probe(self, point_name):
        """Click a single named point once — handy for testing a backend."""
        self.click_pt(point_name, after=self.t_short)

    # ---- user-defined sequences (built in the setup GUI) ------------------ #
    def _resolve_target(self, name):
        """Resolve a step target to (rx, ry): a point name, or 'array[i]'."""
        if name in self.points:
            return self.points[name]
        m = re.match(r"^(\w+)\[(\d+)\]$", str(name))
        if m and m.group(1) in self.arrays:
            return self.arrays[m.group(1)][int(m.group(2))]
        raise KeyError(f"Unknown sequence target: {name!r}")

    def run_step(self, step):
        a = step["action"]
        if a == "wait":
            self.sleep(float(step.get("value", 0)))
        elif a == "key":
            self.key(str(step["value"]))
        elif a == "scroll":
            rx, ry = self._resolve_target(step["target"])
            self.scroll(rx, ry, int(step.get("value", 0)))
        elif a == "move":
            rx, ry = self._resolve_target(step["target"])
            self.move(rx, ry, after=self.t_short)
        elif a in ("click", "double_click", "right_click"):
            rx, ry = self._resolve_target(step["target"])
            clicks = int(step.get("clicks", 2 if a == "double_click" else 1))
            button = "right" if a == "right_click" else "left"
            self.click(rx, ry, clicks=clicks,
                       delay=float(step.get("delay", 0.0)),
                       button=button, after=self.t_short)
        else:
            raise ValueError(f"Unknown action in sequence step: {a!r}")

    def run_sequence(self, name, reps=1):
        steps = self.cfg.get("sequences", {}).get(name)
        if steps is None:
            raise KeyError(f"No sequence named {name!r} in the config.")
        start = time.time()
        self.focus()
        for r in range(1, reps + 1):
            for step in steps:
                self.run_step(step)
            print(f"sequence {name!r} rep {r}/{reps} done — "
                  f"elapsed {int(time.time() - start)}s")
        return int(time.time() - start)

    # ---- helpers ---------------------------------------------------------- #
    def reset(self):
        """Close any open panel (click the X a few times) and go home."""
        self.click_pt("reset_close", clicks=4, delay=0.2, after=self.t_med)
        self.click_pt("reset_home", after=0)

    # ---- game actions (ported 1:1 from DFSD.sh) --------------------------- #
    def guardian(self, guardian_no):
        self.focus()
        self.key("g")
        idx = guardian_no - 1
        gx, gy = self.arrays["guardian_pos"][idx]
        self.click(gx, gy, after=self.t_short)
        self.click_pt("guardian_confirm", after=self.t_short)
        self.sleep(self.t_med)
        self.reset()

    def exped(self):
        self.focus()
        self.click_pt("exped_open", after=self.t_short)
        self.click_pt("exped_select", after=self.t_short)
        self.click_pt("exped_start", clicks=2, delay=0.25, after=self.t_short)
        self.sleep(self.t_med)
        self.reset()

    def tavern(self):
        self.focus()
        self.click_pt("tavern_open")
        self.click_pt("tavern_collect")
        self.click_pt("tavern_tab")
        self.click_pt("tavern_claim")
        self.reset()

    def campaign_loot(self):
        self.focus()
        self.key("m")
        self.click_pt("campaign_menu", after=self.t_short)
        self.click_pt("campaign_loot_collect", after=self.t_short)
        self.sleep(self.t_med)
        self.reset()

    def campaign_fight(self):
        self.focus()
        self.key("m")
        self.click_pt("campaign_menu", after=self.t_short)
        self.click_pt("campaign_fight_select", after=self.t_short)
        self.click_pt("campaign_fight_start", after=self.t_short)
        self.sleep(self.t_fight)
        self.click_pt("campaign_fight_corner", clicks=3, delay=0.01, after=self.t_short)
        self.click_pt("campaign_fight_collect", after=self.t_med)
        self.click_pt("campaign_fight_next", after=self.t_med)
        self.click_pt("campaign_fight_corner", clicks=3, delay=0.01, after=self.t_short)
        self.reset()

    def engi(self):
        self.focus()
        self.click_pt("engi_open", after=self.t_short)
        self.click_pt("engi_b", after=self.t_short)
        self.click_pt("engi_c", after=self.t_short)
        self.click_pt("engi_d", after=self.t_short)
        self.sleep(self.t_med)
        self.reset()

    def alchemy(self, db, dust, ec):
        self.focus()
        if (db + dust + ec) == 0:
            return
        self.key("a")
        if db == 1:
            self.click_pt("alch_db", clicks=2, delay=0.025, after=self.t_short)
        if dust == 1:
            self.click_pt("alch_dust", clicks=2, delay=0.025, after=self.t_short)
        if ec == 1:
            self.click_pt("alch_coins", clicks=2, delay=0.025, after=self.t_short)
        self.reset()

    def oracle(self):
        self.focus()
        self.key("o", after=0.3)
        self.click_pt("oracle_solar", after=self.t_short)
        self.click_pt("oracle_lunar", clicks=2, delay=0.2)
        self.click_pt("oracle_comet", clicks=2, delay=0.2)
        self.click_pt("oracle_gifts2", clicks=2, delay=0.2)
        self.click_pt("oracle_gifts", clicks=2, delay=0.2)
        self.reset()

    def server_swap(self, favorite):
        self.focus()
        self.click_pt("swap_menu")
        self.click_pt("swap_servers_btn")
        self.click_pt("swap_favorites")
        self.click_pt("swap_list", after=self.t_med)
        fav = self.arrays["swap_favorites_pos"][favorite - 1]
        self.click(fav[0], fav[1])
        self.click_pt("swap_confirm")
        self.sleep(self.t_swap)

    def map_collect(self):
        self.focus()
        self.key("M")
        # Pan the map to the corner, twice, to reach the mission cluster.
        d = self.mapcfg
        self.drag(d["drag_start"][0], d["drag_start"][1], d["drag_end"][0], d["drag_end"][1])
        self.drag(d["drag2_start"][0], d["drag2_start"][1], d["drag2_rel"][0], d["drag2_rel"][1],
                  relative=True)
        for _ in range(8):
            self.click_pt("map_collect_mission", after=self.t_short)
            self.click_pt("map_collect_claim", after=self.t_short)
            self.click_pt("map_collect_close", clicks=3, delay=0.01)

    def map_start(self):
        self.focus()
        self.key("M")
        d = self.mapcfg
        p = d["grid_start_x"]
        t = d["grid_start_y"]
        step_y = d["grid_step_y"]

        def place(px, py):
            self.click(px, py, after=self.t_short)
            self.click_pt("map_start_confirm", after=self.t_short)
            self.click_pt("map_start_corner")

        # First column: 9 rows stepping +96, then one more at +84 (=+96-12).
        for _ in range(9):
            place(p, t)
            t += step_y
        t -= 12
        place(p, t)
        p += d["grid_step_x_first"]

        # Next 8 columns: 9 rows from y=150, then one more at +48.
        for _ in range(8):
            t = 150
            for _ in range(9):
                place(p, t)
                t += step_y
            t -= 48
            place(p, t)
            p += d["grid_step_x_main"]

        # Final 5 columns: 9 rows from y=150.
        for _ in range(5):
            t = 150
            for _ in range(9):
                place(p, t)
                t += step_y
            p += d["grid_step_x_last"]
        self.reset()

    # ---- fire-stone tree (library) --------------------------------------- #
    def _fs_node_coords(self, pattern, node_index):
        """Return (col, row) for a node, from the tree-pattern lookup table."""
        patterns = self.arrays["fs_tree_patterns"]
        # original: getMatrixElement(pattern, node_index, cols=16)
        idx = pattern * 16 + node_index
        col_s, row_s = patterns[idx].split(";")
        return int(col_s), int(row_s)

    def _upgrade_node(self, col, row):
        """Scroll the tree to the node's column and click the upgrade."""
        rows = self.arrays["fs_rows"]
        cols_left = self.arrays["fs_cols_left"]
        cols_right = self.arrays["fs_cols_right"]
        mid_x = self.arrays["fs_middle_x"]
        node_y = rows[row - 1]

        if col <= 4:
            node_x = cols_left[col - 1]
            self.scroll(1, 1, 150)  # scroll up to the early tree
            self.click(node_x, node_y, after=self.t_short)
        elif col >= 6:
            node_x = cols_right[col - 6]
            self.scroll(1, 1, -150)  # scroll down to the late tree
            self.click(node_x, node_y, after=self.t_short)
        else:  # middle column (5)
            self.scroll(1, 1, 150)
            self.scroll(1, 1, -50)
            self.click(mid_x, node_y, after=self.t_short)

        self.click_pt("lib_confirm_upgrade", after=self.t_short)
        self.click_pt("lib_close", clicks=2, delay=0.01, after=self.t_short)

    def lib(self, fs_tree, fs1, fs2):
        if fs_tree == 0:
            return
        self.focus()
        self.key("L")
        self.click_pt("lib_open_tree", after=self.t_short)
        self.click_pt("lib_corner", clicks=2, delay=0.01)
        self.click_pt("lib_top", after=self.t_short)
        self.click_pt("lib_corner", clicks=2, delay=0.01)
        self.click_pt("lib_tab_right", after=self.t_short)
        self.click_pt("lib_corner", clicks=2, delay=0.01)
        self.click_pt("lib_tab_left", after=self.t_short)
        self.click_pt("lib_corner", clicks=2, delay=0.01)

        pattern = fs_tree % 3
        col1, row1 = self._fs_node_coords(pattern, fs1 - 1)
        col2, row2 = self._fs_node_coords(pattern, fs2 - 1)
        self._upgrade_node(col1, row1)
        self._upgrade_node(col2, row2)
        self.reset()

    # ---- main loop -------------------------------------------------------- #
    def run(self, p):
        """Run one profile (a dict of parameters; see config 'profiles')."""
        reps = p["reps"]
        starting_server = p["starting_server"]
        lvl = p["lvl"]
        guardian_no = p["guardian_no"]
        alch_db, alch_dust, alch_coins = (int(x) for x in p["alchemy"].split(";"))
        fs_tree, fs1, fs2 = (int(x) for x in p["fs_tree"].split(";"))
        sw_server = p["swap_server"]

        start = time.time()
        self.focus()

        for i in range(1, reps + 1):
            self._cycle(lvl, guardian_no, fs_tree, fs1, fs2,
                        alch_db, alch_dust, alch_coins, oracle_ok=True)

            if i % 3 == 0:
                self.map_collect()
                self.map_start()

            if sw_server != 0:
                sw_lvl = p["swap_lvl"]
                sw_guardian = p["swap_guardian"]
                sa_db, sa_dust, sa_coins = (int(x) for x in p["swap_alchemy"].split(";"))
                sf_tree, sf1, sf2 = (int(x) for x in p["swap_fs_tree"].split(";"))

                self.server_swap(sw_server)
                self._cycle(sw_lvl, sw_guardian, sf_tree, sf1, sf2,
                            sa_db, sa_dust, sa_coins, oracle_ok=True)
                if i % 3 == 0:
                    self.map_collect()
                    self.map_start()
                self.server_swap(starting_server)

            print(f"rep {i}/{reps} done — elapsed {int(time.time() - start)}s")

        elapsed = int(time.time() - start)
        print(f"Finished {reps} reps in {elapsed}s")
        return elapsed

    def _cycle(self, lvl, guardian_no, fs_tree, fs1, fs2,
               alch_db, alch_dust, alch_coins, oracle_ok):
        """One server's worth of collection, gated by account level (as in DFSD.sh)."""
        self.reset()
        self.guardian(guardian_no)
        if lvl >= 10:
            self.exped()
            if fs_tree != 0:
                self.lib(fs_tree, fs1, fs2)
            if lvl >= 15:
                self.tavern()
                if lvl >= 50:
                    self.campaign_loot()
                    self.engi()
                    if lvl >= 120:
                        self.alchemy(alch_db, alch_dust, alch_coins)
                        if lvl >= 200 and oracle_ok:
                            self.oracle()


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def load_config(path):
    if not os.path.exists(path):
        sys.exit(
            f"Config not found: {path}\n"
            "Copy config.example.json to config.json and calibrate it with "
            "setup_gui.py first."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Firestone automation bot")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--profile", help="profile name from the config to run")
    ap.add_argument("--list", action="store_true", help="list available profiles")
    ap.add_argument("--func", nargs="+", metavar="ARG",
                    help="run a single action once, e.g. --func guardian 2")
    ap.add_argument("--sequence", help="run a user-defined sequence from the config")
    ap.add_argument("--reps", type=int, default=1,
                    help="repeat count for --sequence (default 1)")
    ap.add_argument("--background", action="store_true",
                    help="inject input into the game window via Win32 PostMessage "
                         "instead of moving the real cursor (Windows; may not work "
                         "if the game ignores posted input)")
    ap.add_argument("--countdown", type=int, default=4,
                    help="seconds to switch to the game before starting")
    args = ap.parse_args()

    cfg = load_config(args.config)
    bot = Firestone(cfg, background=args.background)
    if args.background:
        print("[background mode] injecting into the game window; your cursor is free.")

    if args.list:
        print("Profiles:")
        for name, p in cfg["profiles"].items():
            print(f"  {name}: reps={p['reps']} lvl={p['lvl']} swap={p['swap_server']}")
        print("Sequences:")
        for name, steps in cfg.get("sequences", {}).items():
            print(f"  {name}: {len(steps)} steps")
        return

    if args.sequence:
        print(f"Running sequence {args.sequence!r} x{args.reps} in {args.countdown}s — "
              "switch to the game now.")
        time.sleep(args.countdown)
        try:
            bot.run_sequence(args.sequence, reps=args.reps)
        except pyautogui.FailSafeException:
            print("\nAborted via fail-safe (mouse in corner).")
        except KeyboardInterrupt:
            print("\nStopped (Ctrl+C).")
        return

    if args.func:
        name, *rest = args.func
        fn = getattr(bot, name, None)
        if not callable(fn):
            sys.exit(f"No such action: {name}")
        print(f"Running {name}({', '.join(rest)}) in {args.countdown}s — "
              "switch to the game now.")
        time.sleep(args.countdown)
        fn(*[int(x) if x.lstrip('-').isdigit() else x for x in rest])
        return

    if not args.profile:
        ap.error("give --profile NAME, --func ..., or --list")
    if args.profile not in cfg["profiles"]:
        sys.exit(f"Unknown profile {args.profile!r}. Try --list.")

    print(f"Starting profile {args.profile!r} in {args.countdown}s — "
          "switch to the game window now.  (Slam mouse to a screen corner to abort.)")
    time.sleep(args.countdown)
    try:
        bot.run(cfg["profiles"][args.profile])
    except pyautogui.FailSafeException:
        print("\nAborted via fail-safe (mouse in corner).")
    except KeyboardInterrupt:
        print("\nStopped (Ctrl+C).")


if __name__ == "__main__":
    main()
