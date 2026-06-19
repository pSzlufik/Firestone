#!/usr/bin/env python3
"""
Firestone point-setup GUI.

Calibrate every coordinate the bot uses, without editing JSON by hand:

  1. Start the game so a window titled "Firestone" is open.
  2. Run:  python setup_gui.py
  3. Set / confirm the window title and click "Detect window".
  4. For any point:
       - "Capture": hover the spot in-game and press F8 (or wait for the
         3-second countdown). The position is stored in resolution-independent
         reference coordinates.
       - "Test": moves your real mouse to the stored point.
       - "Show": flashes a small red square at the stored point WITHOUT moving
         your mouse, so you can see where it is.
     Hover a point's name to read what it does (bottom status bar).
  5. "Show all points" overlays every stored point at once.
  6. "Save" writes config.json.

Only the standard library + pyautogui are required (tkinter ships with Python).
"""

import json
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk

import pyautogui

try:
    import pygetwindow as gw
except Exception:
    gw = None

from firestone_bot import GameWindow

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
EXAMPLE = os.path.join(HERE, "config.example.json")
CAPTURE_HOTKEY = "f8"

# What each point is for, reconstructed from the game (Firestone Idle RPG) and
# the original script's logic.  Shown in the status bar when you hover a point.
DESCRIPTIONS = {
    "reset_close": "Top-right close (X). The bot clicks it a few times to back out of any open panel.",
    "reset_home": "Left-edge button that returns to the town / main screen.",

    "guardian_confirm": "The Train/confirm button in the Guardian panel (after picking which guardian to train).",

    "exped_open": "Opens the Expeditions panel (send heroes out; rewards feed the Tree of Life).",
    "exped_select": "Selects the expedition to send.",
    "exped_start": "Start / send the expedition (clicked twice).",

    "lib_open_tree": "Opens the upgrade tree (Tree of Life) inside the Library (L key).",
    "lib_top": "A section/tab near the top of the tree view.",
    "lib_tab_right": "Bottom-right tab switching which part of the tree is shown.",
    "lib_tab_left": "Bottom-left tab switching which part of the tree is shown.",
    "lib_confirm_upgrade": "Confirm / buy the selected tree node upgrade.",
    "lib_close": "Top-left close button for the tree pop-ups.",
    "lib_corner": "A harmless corner click used to dismiss hover tooltips between actions.",
    "lib_middle_x_probe": "Reference spot for the middle column of the tree (column 5).",

    "tavern_open": "Opens the Tavern (recruit heroes / collect).",
    "tavern_collect": "Collect / recruit button in the Tavern.",
    "tavern_tab": "A tab inside the Tavern.",
    "tavern_claim": "Claim the Tavern reward.",

    "campaign_menu": "Opens the Campaign / world menu (M key context).",
    "campaign_loot_collect": "Collects accumulated idle Campaign loot.",
    "campaign_fight_select": "Selects the Campaign battle to fight.",
    "campaign_fight_start": "Starts the Campaign fight.",
    "campaign_fight_corner": "Back / close corner used after a fight.",
    "campaign_fight_collect": "Collect the battle rewards.",
    "campaign_fight_next": "Proceed to the next battle.",

    "engi_open": "Opens the Engineer panel (war machines for campaign/daily missions).",
    "engi_b": "Engineer step 2 — dispatch / select.",
    "engi_c": "Engineer step 3.",
    "engi_d": "Engineer step 4 — confirm / collect.",

    "alch_db": "Alchemy experiment slot 1 ('DB'). Conducts that experiment.",
    "alch_dust": "Alchemy experiment slot 2 ('dust').",
    "alch_coins": "Alchemy experiment slot 3 ('coins').",

    "oracle_solar": "Oracle — open/collect Solar chests (Oracle unlocks at level 200).",
    "oracle_lunar": "Oracle — Lunar chests.",
    "oracle_comet": "Oracle — Comet chests.",
    "oracle_gifts2": "Oracle — second gift/chest button.",
    "oracle_gifts": "Oracle — Oracle's gifts.",

    "swap_menu": "Top-right menu button that starts a server/realm switch.",
    "swap_servers_btn": "The 'Switch server' option in that menu.",
    "swap_favorites": "The Favorites tab in the server list.",
    "swap_list": "Focuses the favorites list.",
    "swap_confirm": "Confirms the server switch.",

    "map_collect_mission": "A finished World-Map mission marker to collect.",
    "map_collect_claim": "Claim the map-mission reward.",
    "map_collect_close": "Close the mission pop-up.",
    "map_start_confirm": "Confirm starting a new map mission.",
    "map_start_corner": "Neutral corner click between map placements.",
}
ARRAY_DESCRIPTIONS = {
    "guardian_pos": "Position of guardian #{n} in the Guardian selection row (which guardian to train).",
    "swap_favorites_pos": "Position of favourite server #{n} in the server-swap favourites grid.",
}


def load_config():
    path = CONFIG if os.path.exists(CONFIG) else EXAMPLE
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class SetupApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.gamewin = None
        self.markers = []
        root.title("Firestone — point setup")
        root.geometry("820x740")

        self._build_header()
        self._build_point_list()
        self._build_footer()

    # ---- window detection ------------------------------------------------- #
    def _build_header(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Game window:").grid(row=0, column=0, sticky="w")
        self.win_choice = tk.StringVar()
        self.win_combo = ttk.Combobox(top, textvariable=self.win_choice,
                                      width=52, state="readonly")
        self.win_combo.grid(row=0, column=1, padx=6)
        self.win_combo.bind("<<ComboboxSelected>>", self.on_pick_window)
        ttk.Button(top, text="Refresh list", command=self.refresh_windows).grid(row=0, column=2)
        self.win_status = ttk.Label(top, text="not selected", foreground="#a33")
        self.win_status.grid(row=0, column=3, padx=8)

        # filter box so a long window list is easy to narrow
        ttk.Label(top, text="Filter:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.filter_var = tk.StringVar(value=self.cfg.get("window_title", "Firestone"))
        f = ttk.Entry(top, textvariable=self.filter_var, width=20)
        f.grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        f.bind("<KeyRelease>", lambda e: self.refresh_windows())

        ttk.Label(
            top,
            text=("Pick the GAME window from the list (check the size looks like the "
                  "game, ~16:9 — not a near-square folder window). Capture: click a "
                  f"point's button, hover the spot in-game, press {CAPTURE_HOTKEY.upper()} "
                  "(or wait 3s). Hover a name to see what it does."),
            foreground="#555", wraplength=780, justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self._win_objs = []
        self.refresh_windows()

    def refresh_windows(self):
        """List all titled, reasonably-sized windows, narrowed by the filter."""
        if gw is None:
            self.win_status.config(text="pygetwindow missing", foreground="#a33")
            return
        flt = self.filter_var.get().strip().lower()
        objs, labels = [], []
        for w in gw.getAllWindows():
            if not w.title or w.width < 100 or w.height < 100:
                continue
            if flt and flt not in w.title.lower():
                continue
            objs.append(w)
            ratio = w.width / w.height if w.height else 0
            flag = "  ⟵ ~16:9" if 1.6 <= ratio <= 1.9 else ""
            labels.append(f"{w.title[:40]}  —  {w.width}x{w.height} @ ({w.left},{w.top}){flag}")
        self._win_objs = objs
        self.win_combo["values"] = labels
        if labels:
            self.win_combo.current(0)
            self.on_pick_window()
        else:
            self.gamewin = None
            self.win_status.config(text="no matching window", foreground="#a33")

    def on_pick_window(self, _evt=None):
        idx = self.win_combo.current()
        if idx < 0 or idx >= len(self._win_objs):
            return
        w = self._win_objs[idx]
        self.cfg["window_title"] = w.title
        self.gamewin = GameWindow(w.title, self.cfg["reference_size"], window=w)
        ratio = w.width / w.height if w.height else 0
        warn = "" if 1.6 <= ratio <= 1.9 else "  (warning: not ~16:9 — is this the game?)"
        colour = "#161" if not warn else "#b25a00"
        self.win_status.config(text=f"{w.width}x{w.height}{warn}", foreground=colour)

    # ---- scrollable list of points --------------------------------------- #
    def _build_point_list(self):
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=10)

        canvas = tk.Canvas(container, highlightthickness=0)
        scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        self.value_labels = {}
        row = 0
        groups = {}
        for name in self.cfg["points"]:
            groups.setdefault(name.split("_")[0], []).append(name)

        for group, names in groups.items():
            ttk.Label(self.inner, text=group.upper(), font=("", 9, "bold"),
                      foreground="#7a1f2b").grid(row=row, column=0, sticky="w", pady=(10, 2))
            row += 1
            for name in names:
                self._point_row(name, row)
                row += 1

        for arr_name in ("guardian_pos", "swap_favorites_pos"):
            ttk.Label(self.inner, text=arr_name.upper(), font=("", 9, "bold"),
                      foreground="#7a1f2b").grid(row=row, column=0, sticky="w", pady=(10, 2))
            row += 1
            for i in range(len(self.cfg["arrays"][arr_name])):
                self._array_row(arr_name, i, row)
                row += 1

    def _hover_desc(self, text):
        """Bind factory: show `text` in the status bar on hover."""
        def enter(_e):
            self.status.config(text=text)
        return enter

    def _point_row(self, name, row):
        lbl = ttk.Label(self.inner, text=name, width=24)
        lbl.grid(row=row, column=0, sticky="w")
        lbl.bind("<Enter>", self._hover_desc(DESCRIPTIONS.get(name, "(no description)")))
        val = ttk.Label(self.inner, text=str(self.cfg["points"][name]), width=12)
        val.grid(row=row, column=1, padx=6)
        self.value_labels[("point", name)] = val
        ttk.Button(self.inner, text="Capture", width=8,
                   command=lambda n=name: self.capture_point(n)).grid(row=row, column=2)
        ttk.Button(self.inner, text="Test", width=6,
                   command=lambda n=name: self.test_point(self.cfg["points"][n])).grid(row=row, column=3)
        ttk.Button(self.inner, text="Show", width=6,
                   command=lambda n=name: self.show_marker(self.cfg["points"][n], n)
                   ).grid(row=row, column=4)

    def _array_row(self, arr_name, i, row):
        label = f"{arr_name}[{i}]"
        desc = ARRAY_DESCRIPTIONS.get(arr_name, "").format(n=i + 1)
        lbl = ttk.Label(self.inner, text=label, width=24)
        lbl.grid(row=row, column=0, sticky="w")
        lbl.bind("<Enter>", self._hover_desc(desc))
        val = ttk.Label(self.inner, text=str(self.cfg["arrays"][arr_name][i]), width=12)
        val.grid(row=row, column=1, padx=6)
        self.value_labels[("array", arr_name, i)] = val
        ttk.Button(self.inner, text="Capture", width=8,
                   command=lambda: self.capture_array(arr_name, i)).grid(row=row, column=2)
        ttk.Button(self.inner, text="Test", width=6,
                   command=lambda: self.test_point(self.cfg["arrays"][arr_name][i])).grid(row=row, column=3)
        ttk.Button(self.inner, text="Show", width=6,
                   command=lambda: self.show_marker(self.cfg["arrays"][arr_name][i], label)
                   ).grid(row=row, column=4)

    # ---- capture mechanics ----------------------------------------------- #
    def _grab_reference_point(self):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Detect the game window first.")
            return None

        win = tk.Toplevel(self.root)
        win.title("Capturing")
        win.geometry("300x110")
        win.transient(self.root)
        msg = ttk.Label(win, text="", font=("", 11))
        msg.pack(expand=True)
        win.grab_set()

        result = {"xy": None}
        deadline = time.time() + 3.0

        def poll():
            remaining = deadline - time.time()
            if self._hotkey_down():
                result["xy"] = pyautogui.position()
                win.destroy()
                return
            if remaining <= 0:
                result["xy"] = pyautogui.position()
                win.destroy()
                return
            msg.config(text=f"Hover the spot in-game.\nPress {CAPTURE_HOTKEY.upper()} "
                            f"or wait {remaining:0.1f}s")
            win.after(50, poll)

        poll()
        self.root.wait_window(win)
        if not result["xy"]:
            return None
        sx, sy = result["xy"]
        return self.gamewin.to_reference(sx, sy)

    @staticmethod
    def _hotkey_down():
        try:
            import keyboard
            return keyboard.is_pressed(CAPTURE_HOTKEY)
        except Exception:
            return False

    def capture_point(self, name):
        ref = self._grab_reference_point()
        if ref is None:
            return
        self.cfg["points"][name] = [ref[0], ref[1]]
        self.value_labels[("point", name)].config(text=str([ref[0], ref[1]]))

    def capture_array(self, arr_name, i):
        ref = self._grab_reference_point()
        if ref is None:
            return
        self.cfg["arrays"][arr_name][i] = [ref[0], ref[1]]
        self.value_labels[("array", arr_name, i)].config(text=str([ref[0], ref[1]]))

    def test_point(self, ref_xy):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Detect the game window first.")
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        pyautogui.moveTo(x, y, duration=0.3)

    # ---- visual markers --------------------------------------------------- #
    def _make_marker(self, screen_x, screen_y, text, color, size=16):
        m = tk.Toplevel(self.root)
        m.overrideredirect(True)
        m.attributes("-topmost", True)
        try:
            m.attributes("-alpha", 0.85)
        except Exception:
            pass
        m.configure(bg=color)
        m.geometry(f"{size}x{size}+{int(screen_x - size/2)}+{int(screen_y - size/2)}")
        if text:
            # A tiny floating caption just above the square.
            cap = tk.Toplevel(self.root)
            cap.overrideredirect(True)
            cap.attributes("-topmost", True)
            tk.Label(cap, text=text, bg="#222", fg="#fff",
                     font=("", 8)).pack()
            cap.update_idletasks()
            cap.geometry(f"+{int(screen_x + 10)}+{int(screen_y - 10)}")
            self.markers.append(cap)
        self.markers.append(m)
        return m

    def show_marker(self, ref_xy, text=None):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Detect the game window first.")
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        self._make_marker(x, y, text, "#e02020")
        self.root.after(2500, self._clear_markers)

    def show_all(self):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Detect the game window first.")
            return
        self._clear_markers()
        for name, xy in self.cfg["points"].items():
            x, y = self.gamewin.to_screen(xy[0], xy[1])
            self._make_marker(x, y, None, "#1f6feb", size=10)
        for arr in ("guardian_pos", "swap_favorites_pos"):
            for xy in self.cfg["arrays"][arr]:
                x, y = self.gamewin.to_screen(xy[0], xy[1])
                self._make_marker(x, y, None, "#1f9d55", size=10)
        self.status.config(text="Showing all points (blue=single, green=array). "
                                "Click 'Hide markers' to clear.")

    def _clear_markers(self):
        for m in self.markers:
            try:
                m.destroy()
            except Exception:
                pass
        self.markers = []

    # ---- footer ----------------------------------------------------------- #
    def _build_footer(self):
        self.status = ttk.Label(self.root, text="Ready.", relief="sunken",
                                anchor="w", padding=4, foreground="#333")
        self.status.pack(fill="x", side="bottom")

        bar = ttk.Frame(self.root, padding=10)
        bar.pack(fill="x", side="bottom")
        ttk.Button(bar, text="Save config.json", command=self.save).pack(side="right")
        self.saved = ttk.Label(bar, text="")
        self.saved.pack(side="right", padx=10)
        ttk.Button(bar, text="Show all points", command=self.show_all).pack(side="left")
        ttk.Button(bar, text="Hide markers", command=self._clear_markers).pack(side="left", padx=6)

    def save(self):
        # window_title is set by on_pick_window(); persist whatever is current.
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)
        self.saved.config(
            text=f"saved {os.path.basename(CONFIG)} (window: {self.cfg['window_title'][:24]!r})",
            foreground="#161")


def main():
    root = tk.Tk()
    SetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
