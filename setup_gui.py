#!/usr/bin/env python3
"""
Firestone setup GUI — two tabs:

  POINTS    Calibrate every coordinate. Pick the game window, then for any point
            click "Capture", hover the spot in-game and press F8 (global hotkey;
            falls back to a countdown if the optional `keyboard` package is
            missing). "Test" moves your mouse there; "Show" flashes a square
            there without moving the mouse. Hover a name to read what it does.

  SEQUENCE  Build your own action cycle from drop-downs: choose an action
            (click / move / key / scroll / wait ...) and a target point, add it
            to the list, reorder, and save. Run it with:
                python firestone_bot.py --sequence <name> --reps N

Only the standard library + pyautogui are required (tkinter ships with Python);
`keyboard` is optional and only makes F8 capture instant.
"""

import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

import pyautogui

try:
    import pygetwindow as gw
except Exception:
    gw = None

try:
    import keyboard  # optional: enables the global F8 capture hotkey
except Exception:
    keyboard = None

from firestone_bot import GameWindow

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
EXAMPLE = os.path.join(HERE, "config.example.json")
CAPTURE_HOTKEY = "f8"

ACTIONS = ["click", "double click", "right click", "move", "key", "scroll", "wait"]
ACTION_KEY = {"double click": "double_click", "right click": "right_click"}

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
    "guardian_pos": "Position of guardian #{n} in the Guardian selection row.",
    "swap_favorites_pos": "Position of favourite server #{n} in the server-swap grid.",
}
ARRAY_POINTS = ("guardian_pos", "swap_favorites_pos")


def load_config():
    path = CONFIG if os.path.exists(CONFIG) else EXAMPLE
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class SetupApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.cfg.setdefault("sequences", {})
        self.gamewin = None
        self.markers = []
        self._armed = None
        self._capture_timer = None
        self.value_labels = {}

        root.title("Firestone — setup")
        root.geometry("860x780")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self.points_tab = ttk.Frame(nb)
        self.seq_tab = ttk.Frame(nb)
        nb.add(self.points_tab, text="Points")
        nb.add(self.seq_tab, text="Sequence")
        self._build_point_list(self.points_tab)
        self._build_sequence_editor(self.seq_tab)
        self._build_footer()

        if keyboard is not None:
            try:
                keyboard.add_hotkey(CAPTURE_HOTKEY, self._on_hotkey)
            except Exception:
                pass
        self.refresh_windows()

    # ---- window picker ---------------------------------------------------- #
    def _build_header(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Game window:").grid(row=0, column=0, sticky="w")
        self.win_combo = ttk.Combobox(top, width=54, state="readonly")
        self.win_combo.grid(row=0, column=1, padx=6)
        self.win_combo.bind("<<ComboboxSelected>>", self.on_pick_window)
        ttk.Button(top, text="Refresh", command=self.refresh_windows).grid(row=0, column=2)
        self.win_status = ttk.Label(top, text="not selected", foreground="#a33")
        self.win_status.grid(row=0, column=3, padx=8)

        ttk.Label(top, text="Filter:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.filter_var = tk.StringVar(value=self.cfg.get("window_title", "Firestone"))
        f = ttk.Entry(top, textvariable=self.filter_var, width=20)
        f.grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        f.bind("<KeyRelease>", lambda e: self.refresh_windows())

        cap = "F8 (global)" if keyboard is not None else "the 3s countdown (install `keyboard` for instant F8)"
        ttk.Label(top, wraplength=820, justify="left", foreground="#555",
                  text=("Pick the GAME window (size should look ~16:9, not a near-square folder "
                        f"window). To calibrate: click Capture, hover the spot in-game, trigger with {cap}.")
                  ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self._win_objs = []

    def refresh_windows(self):
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
            flag = "  <- ~16:9" if 1.6 <= ratio <= 1.9 else ""
            labels.append(f"{w.title[:38]}  -  {w.width}x{w.height} @ ({w.left},{w.top}){flag}")
        self._win_objs = objs
        self.win_combo["values"] = labels
        if not labels:
            self.gamewin = None
            self.win_status.config(text="no matching window", foreground="#a33")
            return
        # Auto-pick the best candidate: prefer ~16:9, then largest area.
        def score(w):
            ratio = w.width / w.height if w.height else 0
            return (1 if 1.6 <= ratio <= 1.9 else 0, w.width * w.height)
        best = max(range(len(objs)), key=lambda i: score(objs[i]))
        self.win_combo.current(best)
        self.on_pick_window()

    def on_pick_window(self, _evt=None):
        idx = self.win_combo.current()
        if not (0 <= idx < len(self._win_objs)):
            return
        w = self._win_objs[idx]
        self.cfg["window_title"] = w.title
        self.gamewin = GameWindow(w.title, self.cfg["reference_size"], window=w)
        ratio = w.width / w.height if w.height else 0
        warn = "" if 1.6 <= ratio <= 1.9 else "  (warning: not ~16:9 — is this the game?)"
        self.win_status.config(text=f"{w.width}x{w.height}{warn}",
                              foreground="#161" if not warn else "#b25a00")

    # ---- POINTS tab ------------------------------------------------------- #
    def _build_point_list(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

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
        for arr in ARRAY_POINTS:
            ttk.Label(self.inner, text=arr.upper(), font=("", 9, "bold"),
                      foreground="#7a1f2b").grid(row=row, column=0, sticky="w", pady=(10, 2))
            row += 1
            for i in range(len(self.cfg["arrays"][arr])):
                self._array_row(arr, i, row)
                row += 1

    def _hover(self, text):
        return lambda _e: self.status.config(text=text)

    def _point_row(self, name, row):
        lbl = ttk.Label(self.inner, text=name, width=24)
        lbl.grid(row=row, column=0, sticky="w")
        lbl.bind("<Enter>", self._hover(DESCRIPTIONS.get(name, "(no description)")))
        val = ttk.Label(self.inner, text=str(self.cfg["points"][name]), width=12)
        val.grid(row=row, column=1, padx=6)
        self.value_labels[("point", name)] = val
        ttk.Button(self.inner, text="Capture", width=8,
                   command=lambda: self._arm(("point", name))).grid(row=row, column=2)
        ttk.Button(self.inner, text="Test", width=6,
                   command=lambda: self.test_point(self.cfg["points"][name])).grid(row=row, column=3)
        ttk.Button(self.inner, text="Show", width=6,
                   command=lambda: self.show_marker(self.cfg["points"][name], name)).grid(row=row, column=4)

    def _array_row(self, arr, i, row):
        label = f"{arr}[{i}]"
        lbl = ttk.Label(self.inner, text=label, width=24)
        lbl.grid(row=row, column=0, sticky="w")
        lbl.bind("<Enter>", self._hover(ARRAY_DESCRIPTIONS.get(arr, "").format(n=i + 1)))
        val = ttk.Label(self.inner, text=str(self.cfg["arrays"][arr][i]), width=12)
        val.grid(row=row, column=1, padx=6)
        self.value_labels[("array", arr, i)] = val
        ttk.Button(self.inner, text="Capture", width=8,
                   command=lambda: self._arm(("array", arr, i))).grid(row=row, column=2)
        ttk.Button(self.inner, text="Test", width=6,
                   command=lambda: self.test_point(self.cfg["arrays"][arr][i])).grid(row=row, column=3)
        ttk.Button(self.inner, text="Show", width=6,
                   command=lambda: self.show_marker(self.cfg["arrays"][arr][i], label)).grid(row=row, column=4)

    # ---- capture (non-modal, global F8 + countdown fallback) -------------- #
    def _arm(self, target):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        self._armed = target
        name = target[1] if target[0] == "point" else f"{target[1]}[{target[2]}]"
        # F8 (if available) fires instantly; a countdown always runs as a
        # backstop so capture still works even if the global hook is dead.
        self._countdown(6.0 if keyboard is not None else 3.0, name)

    def _countdown(self, remaining, name):
        if self._armed is None:
            return
        if remaining <= 0:
            self._do_capture()
            return
        self.status.config(
            text=f"Capturing '{name}' in {remaining:0.1f}s — hover the spot in-game…",
            foreground="#7a1f2b")
        self._capture_timer = self.root.after(100, lambda: self._countdown(remaining - 0.1, name))

    def _on_hotkey(self):
        # Runs in keyboard's thread; marshal to the Tk thread.
        self.root.after(0, self._do_capture)

    def _do_capture(self):
        if self._armed is None or self.gamewin is None:
            return
        if self._capture_timer is not None:
            try:
                self.root.after_cancel(self._capture_timer)
            except Exception:
                pass
            self._capture_timer = None
        sx, sy = pyautogui.position()
        ref = list(self.gamewin.to_reference(sx, sy))
        target = self._armed
        self._armed = None
        if target[0] == "point":
            self.cfg["points"][target[1]] = ref
            self.value_labels[("point", target[1])].config(text=str(ref))
            name = target[1]
        else:
            self.cfg["arrays"][target[1]][target[2]] = ref
            self.value_labels[("array", target[1], target[2])].config(text=str(ref))
            name = f"{target[1]}[{target[2]}]"
        self.show_marker(ref, name)
        self.status.config(text=f"Captured '{name}' -> {ref}  (remember to Save).",
                           foreground="#161")

    def test_point(self, ref_xy):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        pyautogui.moveTo(x, y, duration=0.3)

    # ---- markers ---------------------------------------------------------- #
    def _make_marker(self, sx, sy, text, color, size=16):
        m = tk.Toplevel(self.root)
        m.overrideredirect(True)
        m.attributes("-topmost", True)
        try:
            m.attributes("-alpha", 0.85)
        except Exception:
            pass
        m.configure(bg=color)
        m.geometry(f"{size}x{size}+{int(sx - size / 2)}+{int(sy - size / 2)}")
        self.markers.append(m)
        if text:
            cap = tk.Toplevel(self.root)
            cap.overrideredirect(True)
            cap.attributes("-topmost", True)
            tk.Label(cap, text=text, bg="#222", fg="#fff", font=("", 8)).pack()
            cap.update_idletasks()
            cap.geometry(f"+{int(sx + 10)}+{int(sy - 10)}")
            self.markers.append(cap)

    def show_marker(self, ref_xy, text=None):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        self._make_marker(x, y, text, "#e02020")
        self.root.after(2500, self._clear_markers)

    def show_all(self):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        self._clear_markers()
        for xy in self.cfg["points"].values():
            x, y = self.gamewin.to_screen(xy[0], xy[1])
            self._make_marker(x, y, None, "#1f6feb", size=10)
        for arr in ARRAY_POINTS:
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

    # ---- SEQUENCE tab ----------------------------------------------------- #
    def _target_options(self):
        opts = list(self.cfg["points"])
        for arr in ARRAY_POINTS:
            opts += [f"{arr}[{i}]" for i in range(len(self.cfg["arrays"][arr]))]
        return opts

    def _build_sequence_editor(self, parent):
        self.sequence = []

        bar = ttk.Frame(parent, padding=8)
        bar.pack(fill="x")
        ttk.Label(bar, text="Sequence:").grid(row=0, column=0, sticky="w")
        self.seq_name = ttk.Combobox(bar, width=22, values=list(self.cfg["sequences"]))
        self.seq_name.grid(row=0, column=1, padx=6)
        if self.cfg["sequences"]:
            self.seq_name.current(0)
        ttk.Button(bar, text="Load", command=self.load_sequence).grid(row=0, column=2)
        ttk.Button(bar, text="Save sequence", command=self.save_sequence).grid(row=0, column=3, padx=6)

        add = ttk.LabelFrame(parent, text="Add a step", padding=8)
        add.pack(fill="x", padx=8, pady=6)
        ttk.Label(add, text="Action").grid(row=0, column=0, padx=4)
        self.act_var = ttk.Combobox(add, width=12, state="readonly", values=ACTIONS)
        self.act_var.current(0)
        self.act_var.grid(row=0, column=1, padx=4)
        self.act_var.bind("<<ComboboxSelected>>", lambda e: self._sync_step_fields())
        ttk.Label(add, text="Point").grid(row=0, column=2, padx=4)
        self.tgt_var = ttk.Combobox(add, width=24, state="readonly", values=self._target_options())
        self.tgt_var.grid(row=0, column=3, padx=4)
        ttk.Label(add, text="Value / clicks").grid(row=0, column=4, padx=4)
        self.val_var = ttk.Entry(add, width=8)
        self.val_var.grid(row=0, column=5, padx=4)
        ttk.Button(add, text="Add step", command=self.add_step).grid(row=0, column=6, padx=8)
        self.step_hint = ttk.Label(add, text="", foreground="#555")
        self.step_hint.grid(row=1, column=0, columnspan=7, sticky="w", pady=(6, 0))
        self._sync_step_fields()

        mid = ttk.Frame(parent, padding=8)
        mid.pack(fill="both", expand=True)
        self.seq_list = tk.Listbox(mid, height=14)
        self.seq_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, command=self.seq_list.yview)
        sb.pack(side="left", fill="y")
        self.seq_list.config(yscrollcommand=sb.set)
        side = ttk.Frame(mid, padding=(8, 0))
        side.pack(side="left", fill="y")
        for txt, cmd in (("Up", self.step_up), ("Down", self.step_down),
                         ("Delete", self.step_del), ("Clear", self.step_clear)):
            ttk.Button(side, text=txt, width=8, command=cmd).pack(pady=2)

        if self.cfg["sequences"]:
            self.load_sequence()

    def _sync_step_fields(self):
        a = self.act_var.get()
        if a == "key":
            self.tgt_var.config(state="disabled")
            self.step_hint.config(text="key: put the key in Value (e.g. g, m, L, o, a).")
        elif a == "wait":
            self.tgt_var.config(state="disabled")
            self.step_hint.config(text="wait: put seconds in Value (e.g. 0.5).")
        elif a == "scroll":
            self.tgt_var.config(state="readonly")
            self.step_hint.config(text="scroll: Point = where; Value = notches (+up / -down).")
        elif a in ("click", "double click", "right click"):
            self.tgt_var.config(state="readonly")
            self.step_hint.config(text="click: Point = where; Value = number of clicks (optional).")
        else:  # move
            self.tgt_var.config(state="readonly")
            self.step_hint.config(text="move: Point = where to move the cursor.")

    def add_step(self):
        a = self.act_var.get()
        act = ACTION_KEY.get(a, a)
        val = self.val_var.get().strip()
        step = {"action": act}
        if act in ("key", "wait"):
            if not val:
                messagebox.showwarning("Missing value", f"'{a}' needs a value.")
                return
            step["value"] = val if act == "key" else float(val)
        else:
            tgt = self.tgt_var.get()
            if not tgt:
                messagebox.showwarning("Missing point", f"'{a}' needs a Point.")
                return
            step["target"] = tgt
            if act == "scroll":
                step["value"] = int(val or 0)
            elif val:
                step["clicks"] = int(val)
        self.sequence.append(step)
        self.seq_list.insert("end", self._fmt_step(step))

    @staticmethod
    def _fmt_step(s):
        a = s["action"]
        if a == "wait":
            return f"wait  {s['value']}s"
        if a == "key":
            return f"key  {s['value']}"
        if a == "scroll":
            return f"scroll  {s['target']}  {s.get('value', 0)}"
        extra = f"  x{s['clicks']}" if s.get("clicks", 1) and s.get("clicks", 1) != 1 else ""
        return f"{a}  {s.get('target', '')}{extra}"

    def _reload_listbox(self):
        self.seq_list.delete(0, "end")
        for s in self.sequence:
            self.seq_list.insert("end", self._fmt_step(s))

    def _sel(self):
        s = self.seq_list.curselection()
        return s[0] if s else None

    def step_up(self):
        i = self._sel()
        if i and i > 0:
            self.sequence[i - 1], self.sequence[i] = self.sequence[i], self.sequence[i - 1]
            self._reload_listbox()
            self.seq_list.selection_set(i - 1)

    def step_down(self):
        i = self._sel()
        if i is not None and i < len(self.sequence) - 1:
            self.sequence[i + 1], self.sequence[i] = self.sequence[i], self.sequence[i + 1]
            self._reload_listbox()
            self.seq_list.selection_set(i + 1)

    def step_del(self):
        i = self._sel()
        if i is not None:
            del self.sequence[i]
            self._reload_listbox()

    def step_clear(self):
        self.sequence = []
        self._reload_listbox()

    def load_sequence(self):
        name = self.seq_name.get().strip()
        self.sequence = [dict(s) for s in self.cfg["sequences"].get(name, [])]
        self._reload_listbox()
        self.status.config(text=f"Loaded sequence '{name}' ({len(self.sequence)} steps).")

    def save_sequence(self):
        name = self.seq_name.get().strip()
        if not name:
            messagebox.showwarning("Name needed", "Give the sequence a name.")
            return
        self.cfg["sequences"][name] = self.sequence
        self.seq_name["values"] = list(self.cfg["sequences"])
        self._write_config()
        self.status.config(text=f"Saved sequence '{name}' ({len(self.sequence)} steps) to config.json.",
                           foreground="#161")

    # ---- footer / save ---------------------------------------------------- #
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

    def _write_config(self):
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)

    def save(self):
        self._write_config()
        self.saved.config(text=f"saved (window: {self.cfg.get('window_title', '')[:20]!r})",
                          foreground="#161")

    def _on_close(self):
        if keyboard is not None:
            try:
                keyboard.remove_hotkey(CAPTURE_HOTKEY)
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    SetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
