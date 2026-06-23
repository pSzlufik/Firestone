#!/usr/bin/env python3
"""
Firestone setup GUI.

Tabs:

  BUILDER   Build your own positions from scratch (starts empty):
              * point  — one captured coordinate.
              * area   — a rectangle you drag on screen; the bot sweeps it as a
                grid of clicks (top-left -> bottom-right) stepping by an offset
                you set, with optional "meantime" clicks performed after EACH
                cell (e.g. accept-mission / close-window). Great for the map's
                non-deterministic mission spots or war-machine runs.

  POINTS    The ported DFSD coordinate set (for the built-in profile loop).

  SEQUENCE  Compose an action cycle from drop-downs (now including 'element').

Capture: click a Capture button, move the cursor to the spot in-game and hold
still for a moment — it grabs automatically (dwell-to-capture). Tune the dwell
with timing.capture_dwell in the config.

Run what you build:
    python firestone_bot.py --element <name> --reps N
    python firestone_bot.py --sequence <name> --reps N
"""

import copy
import json
import os
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import pyautogui

try:
    import pygetwindow as gw
except Exception:
    gw = None

try:
    import keyboard
except Exception:
    keyboard = None

from firestone_bot import GameWindow

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
EXAMPLE = os.path.join(HERE, "config.example.json")
CAPTURE_HOTKEY = "f8"

ACTIONS = ["click", "double click", "right click", "move", "key", "scroll", "wait", "element"]
ACTION_KEY = {"double click": "double_click", "right click": "right_click"}
ARRAY_POINTS = ("guardian_pos", "swap_favorites_pos")


def load_config():
    path = CONFIG if os.path.exists(CONFIG) else EXAMPLE
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def area_cells(el):
    """Replicate the bot's grid: top-left -> bottom-right by offset (ref px)."""
    x1, y1 = el["topleft"]
    x2, y2 = el["bottomright"]
    dx, dy = el.get("offset", [100, 100])
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    dx, dy = max(1, abs(int(dx))), max(1, abs(int(dy)))
    cells = []
    y = y1
    while y <= y2:
        x = x1
        while x <= x2:
            cells.append((x, y))
            x += dx
        y += dy
    return cells


class SetupApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.cfg.setdefault("elements", {})
        self.cfg.setdefault("sequences", {})
        self.gamewin = None
        self.markers = []
        self._armed = False
        self._capture_cb = None
        self._capture_timer = None
        self.value_labels = {}

        root.title("Firestone — setup")
        root.geometry("900x800")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self.builder_tab = ttk.Frame(nb)
        self.seq_tab = ttk.Frame(nb)
        nb.add(self.builder_tab, text="Builder")
        nb.add(self.seq_tab, text="Sequence")
        self._build_footer()                 # status bar first (capture uses it)
        self._build_builder(self.builder_tab)
        self._build_sequence_editor(self.seq_tab)

        if keyboard is not None:
            try:
                keyboard.add_hotkey(CAPTURE_HOTKEY, self._on_hotkey)
            except Exception:
                pass
        self.refresh_windows()

    # ===================================================================== #
    #  Window picker
    # ===================================================================== #
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
        def score(w):
            r = w.width / w.height if w.height else 0
            return (1 if 1.6 <= r <= 1.9 else 0, w.width * w.height)
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
        r = w.width / w.height if w.height else 0
        warn = "" if 1.6 <= r <= 1.9 else "  (warning: not ~16:9 — is this the game?)"
        self.win_status.config(text=f"{w.width}x{w.height}{warn}",
                              foreground="#161" if not warn else "#b25a00")

    # ===================================================================== #
    #  Capture infrastructure (callback based)
    # ===================================================================== #
    def _arm(self, callback, label):
        """Arm a single-point capture; `callback(ref_xy)` gets the result."""
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        self._capture_cb = callback
        self._armed = True
        # Dwell-to-capture: move the cursor to the spot, hold still briefly -> grab.
        # No global hotkey needed (F8 hooks are unreliable). F8 still works as an
        # instant trigger if the keyboard hook happens to fire.
        t = self.cfg.get("timing", {})
        self._dwell = float(t.get("capture_dwell", 0.35))
        self._arm_deadline = time.time() + float(t.get("capture_timeout", 10.0))
        self._arm_origin = pyautogui.position()
        self._last_pos = self._arm_origin
        self._still_since = None
        self._moved = False
        self._poll_capture(label)

    def _poll_capture(self, label):
        if not self._armed:
            return
        now = time.time()
        pos = pyautogui.position()
        if (pos.x, pos.y) != (self._last_pos.x, self._last_pos.y):
            self._last_pos = pos
            self._still_since = now
            if abs(pos.x - self._arm_origin.x) + abs(pos.y - self._arm_origin.y) > 25:
                self._moved = True
        elif self._still_since is None:
            self._still_since = now
        # Capture once the cursor has moved to the target and settled there.
        if self._moved and self._still_since and (now - self._still_since) >= self._dwell:
            self._do_capture()
            return
        if now >= self._arm_deadline:           # safety backstop
            self._do_capture()
            return
        hint = "move to the spot, then hold still" if not self._moved else "hold still…"
        self.status.config(text=f"Capturing '{label}': {hint}", foreground="#7a1f2b")
        self._capture_timer = self.root.after(40, lambda: self._poll_capture(label))

    def _on_hotkey(self):
        self.root.after(0, self._do_capture)

    def _do_capture(self):
        if not self._armed or self.gamewin is None:
            return
        if self._capture_timer is not None:
            try:
                self.root.after_cancel(self._capture_timer)
            except Exception:
                pass
            self._capture_timer = None
        sx, sy = pyautogui.position()
        ref = list(self.gamewin.to_reference(sx, sy))
        self._armed = False
        cb, self._capture_cb = self._capture_cb, None
        if cb:
            cb(ref)
        self.show_marker(ref)
        self.status.config(text=f"Captured {ref}  (remember to Save).", foreground="#161")

    @staticmethod
    def _virtual_screen():
        """(left, top, width, height) of the whole virtual desktop (all monitors)."""
        try:
            import ctypes
            u = ctypes.windll.user32
            # SM_XVIRTUALSCREEN=76, Y=77, CX=78, CY=79
            x, y = u.GetSystemMetrics(76), u.GetSystemMetrics(77)
            w, h = u.GetSystemMetrics(78), u.GetSystemMetrics(79)
            if w and h:
                return x, y, w, h
        except Exception:
            pass
        return None

    def capture_area_rect(self, callback):
        """Translucent overlay spanning ALL monitors; user drags a rectangle.
        `callback(topleft_ref, bottomright_ref)` gets the corners."""
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        try:
            ov.attributes("-alpha", 0.30)
        except Exception:
            pass
        vs = self._virtual_screen()
        if vs:                       # cover every monitor, wherever the game is
            vx, vy, vw, vh = vs
            ov.geometry(f"{vw}x{vh}+{vx}+{vy}")
        else:                        # fallback: primary monitor
            vx, vy = 0, 0
            ov.attributes("-fullscreen", True)
        cv = tk.Canvas(ov, cursor="cross", bg="black", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        # Put the instructions over the game window so they're visible there.
        try:
            gl, gt, gwd, _gh = self.gamewin.rect()
            tx, ty = gl - vx + gwd // 2, gt - vy + 30
        except Exception:
            tx, ty = 200, 30
        cv.create_text(tx, ty, fill="white", font=("", 14),
                       text="Drag a rectangle over the area to sweep — Esc to cancel")
        st = {"sx": None, "sy": None, "cx": None, "cy": None, "rect": None}

        def down(e):
            st["sx"], st["sy"], st["cx"], st["cy"] = e.x_root, e.y_root, e.x, e.y
            st["rect"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#ff3030", width=2)

        def drag(e):
            if st["rect"] is not None:
                cv.coords(st["rect"], st["cx"], st["cy"], e.x, e.y)

        def up(e):
            if st["sx"] is None:
                ov.destroy()
                return
            tl = self.gamewin.to_reference(min(st["sx"], e.x_root), min(st["sy"], e.y_root))
            br = self.gamewin.to_reference(max(st["sx"], e.x_root), max(st["sy"], e.y_root))
            ov.destroy()
            callback(list(tl), list(br))

        cv.bind("<ButtonPress-1>", down)
        cv.bind("<B1-Motion>", drag)
        cv.bind("<ButtonRelease-1>", up)
        ov.bind("<Escape>", lambda e: ov.destroy())
        cv.bind("<ButtonPress-3>", lambda e: ov.destroy())  # right-click cancels
        ov.lift()
        ov.focus_force()

    # ===================================================================== #
    #  BUILDER tab
    # ===================================================================== #
    def _build_builder(self, parent):
        left = ttk.Frame(parent, padding=8)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Your elements", font=("", 9, "bold")).pack(anchor="w")
        self.elem_list = tk.Listbox(left, width=26, height=22)
        self.elem_list.pack(fill="y", expand=True, pady=4)
        self.elem_list.bind("<<ListboxSelect>>", lambda e: self._show_element_details())
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Add point", width=9, command=self.add_point_element).pack(side="left")
        ttk.Button(row, text="Add area", width=9, command=self.add_area_element).pack(side="left", padx=4)
        row2 = ttk.Frame(left)
        row2.pack(fill="x", pady=2)
        ttk.Button(row2, text="Add scroll", width=9, command=self.add_scroll_element).pack(side="left")
        ttk.Button(row2, text="Copy", width=9, command=self.copy_element).pack(side="left", padx=4)
        ttk.Button(left, text="Delete element", command=self.delete_element).pack(fill="x", pady=2)

        self.detail = ttk.LabelFrame(parent, text="Element details", padding=10)
        self.detail.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self._reload_elements()

    def _reload_elements(self):
        self.elem_list.delete(0, "end")
        for name, el in self.cfg["elements"].items():
            tag = el["type"]
            if tag == "area":
                tag = f"area {len(area_cells(el))} cells"
            elif tag == "scroll":
                tag = f"scroll {el.get('amount', 0)}"
            desc = el.get("description", "").strip().replace("\n", " ")
            snippet = f"  — {desc[:28]}" if desc else ""
            self.elem_list.insert("end", f"{name}  ({tag}){snippet}")

    def _selected_element_name(self):
        sel = self.elem_list.curselection()
        if not sel:
            return None
        return self.elem_list.get(sel[0]).split("  (")[0]

    def add_point_element(self):
        name = simpledialog.askstring("New point", "Name for this point element:", parent=self.root)
        if not name:
            return
        self.cfg["elements"][name] = {"type": "point", "pos": [0, 0], "description": ""}
        self._reload_elements()

        def done(ref):
            self.cfg["elements"][name]["pos"] = ref
            self._reload_elements()
            self._select_element(name)
        self._arm(done, name)

    def add_area_element(self):
        name = simpledialog.askstring("New area", "Name for this area element:", parent=self.root)
        if not name:
            return

        def got_rect(tl, br):
            self.cfg["elements"][name] = {
                "type": "area", "topleft": tl, "bottomright": br,
                "offset": [100, 100], "meantime": [], "description": "",
            }
            self._reload_elements()
            self._select_element(name)
            self.status.config(text=f"Area '{name}' set. Adjust offset and add meantime clicks.",
                               foreground="#161")
        self.status.config(text="Drag a rectangle over the area in-game…", foreground="#7a1f2b")
        self.capture_area_rect(got_rect)

    def add_scroll_element(self):
        name = simpledialog.askstring("New scroll", "Name for this scroll element:", parent=self.root)
        if not name:
            return
        self.cfg["elements"][name] = {"type": "scroll", "pos": [0, 0],
                                      "amount": 150, "description": ""}
        self._reload_elements()

        def done(ref):
            self.cfg["elements"][name]["pos"] = ref
            self._reload_elements()
            self._select_element(name)
        self._arm(done, name)

    def copy_element(self):
        name = self._selected_element_name()
        if not name:
            messagebox.showinfo("Copy", "Select an element to copy first.")
            return
        new = simpledialog.askstring("Copy element", f"Name for the copy of '{name}':",
                                     parent=self.root)
        if not new:
            return
        if new in self.cfg["elements"]:
            messagebox.showwarning("Exists", f"An element named '{new}' already exists.")
            return
        self.cfg["elements"][new] = copy.deepcopy(self.cfg["elements"][name])
        self._reload_elements()
        self._select_element(new)
        self.status.config(text=f"Copied '{name}' -> '{new}'.", foreground="#161")

    def delete_element(self):
        name = self._selected_element_name()
        if not name:
            return
        if messagebox.askyesno("Delete", f"Delete element '{name}'?"):
            self.cfg["elements"].pop(name, None)
            self._reload_elements()
            for w in self.detail.winfo_children():
                w.destroy()

    def _select_element(self, name):
        names = list(self.cfg["elements"])
        if name in names:
            self.elem_list.selection_clear(0, "end")
            self.elem_list.selection_set(names.index(name))
            self._show_element_details()

    def _show_element_details(self):
        for w in self.detail.winfo_children():
            w.destroy()
        name = self._selected_element_name()
        if not name:
            return
        el = self.cfg["elements"][name]
        ttk.Label(self.detail, text=name, font=("", 11, "bold")).pack(anchor="w")

        if el["type"] in ("point", "scroll"):
            self._coord_row("position", el["pos"])
            bar = ttk.Frame(self.detail); bar.pack(anchor="w", pady=2)
            ttk.Button(bar, text="Recapture", command=lambda: self._arm(
                lambda ref: (el.__setitem__("pos", ref), self._show_element_details()), name)
                ).pack(side="left")
            ttk.Button(bar, text="Test", command=lambda: self.test_point(el["pos"])).pack(side="left", padx=4)
            ttk.Button(bar, text="Show", command=lambda: self.show_marker(el["pos"], name)).pack(side="left")
            if el["type"] == "scroll":
                sr = ttk.Frame(self.detail); sr.pack(anchor="w", pady=6)
                ttk.Label(sr, text="Scroll amount (notches, + up / - down):").pack(side="left")
                av = tk.StringVar(value=str(el.get("amount", 0)))
                ttk.Entry(sr, textvariable=av, width=7).pack(side="left", padx=4)

                def apply_amount():
                    try:
                        el["amount"] = int(av.get())
                    except ValueError:
                        messagebox.showwarning("Bad amount", "Amount must be a whole number.")
                        return
                    self._reload_elements()
                    self.status.config(text=f"Scroll amount set to {el['amount']}.", foreground="#161")
                ttk.Button(sr, text="Apply", command=apply_amount).pack(side="left")
            self._desc_editor(el)
            return

        # area — editable corners
        self._coord_row("top-left", el["topleft"], on_change=self._reload_elements)
        self._coord_row("bottom-right", el["bottomright"], on_change=self._reload_elements)
        ttk.Button(self.detail, text="Recapture rectangle",
                   command=lambda: self.capture_area_rect(
                       lambda tl, br: (el.update(topleft=tl, bottomright=br),
                                       self._reload_elements(), self._show_element_details()))
                   ).pack(anchor="w", pady=2)

        offr = ttk.Frame(self.detail); offr.pack(anchor="w", pady=6)
        ttk.Label(offr, text="Offset  dx:").pack(side="left")
        dxv = tk.StringVar(value=str(el["offset"][0]))
        ttk.Entry(offr, textvariable=dxv, width=6).pack(side="left", padx=2)
        ttk.Label(offr, text="dy:").pack(side="left")
        dyv = tk.StringVar(value=str(el["offset"][1]))
        ttk.Entry(offr, textvariable=dyv, width=6).pack(side="left", padx=2)

        grid_lbl = ttk.Label(self.detail, text="")
        def apply_offset():
            try:
                el["offset"] = [int(dxv.get()), int(dyv.get())]
            except ValueError:
                messagebox.showwarning("Bad offset", "Offsets must be whole numbers.")
                return
            self._reload_elements()
            grid_lbl.config(text=f"grid: {len(area_cells(el))} clicks")
        ttk.Button(offr, text="Apply", command=apply_offset).pack(side="left", padx=6)
        grid_lbl.config(text=f"grid: {len(area_cells(el))} clicks")
        grid_lbl.pack(anchor="w")

        ttk.Label(self.detail, text="Meantime clicks (after each cell):",
                  font=("", 9, "bold")).pack(anchor="w", pady=(10, 2))
        mlist = tk.Listbox(self.detail, height=6)
        for mp in el["meantime"]:
            mlist.insert("end", str(mp))
        mlist.pack(fill="x")
        mbar = ttk.Frame(self.detail); mbar.pack(anchor="w", pady=4)

        def add_meantime():
            el["meantime"].append([0, 0])
            idx = len(el["meantime"]) - 1

            def done(ref):
                el["meantime"][idx] = ref
                self._show_element_details()
            self._arm(done, f"{name} meantime[{idx}]")
        def del_meantime():
            s = mlist.curselection()
            if s:
                el["meantime"].pop(s[0])
                self._show_element_details()
        ttk.Button(mbar, text="Add meantime", command=add_meantime).pack(side="left")
        ttk.Button(mbar, text="Remove", command=del_meantime).pack(side="left", padx=4)
        ttk.Button(mbar, text="Show grid", command=lambda: self.show_area(el)).pack(side="left", padx=4)
        self._desc_editor(el)

    def _coord_row(self, label, coord_list, on_change=None):
        """Editable x/y fields bound to a [x, y] list (edited in place)."""
        fr = ttk.Frame(self.detail); fr.pack(anchor="w", pady=2)
        ttk.Label(fr, text=f"{label}:  x").pack(side="left")
        xv = tk.StringVar(value=str(coord_list[0]))
        ttk.Entry(fr, textvariable=xv, width=6).pack(side="left", padx=2)
        ttk.Label(fr, text="y").pack(side="left")
        yv = tk.StringVar(value=str(coord_list[1]))
        ttk.Entry(fr, textvariable=yv, width=6).pack(side="left", padx=2)

        def apply(*_):
            try:
                coord_list[0], coord_list[1] = int(xv.get()), int(yv.get())
            except ValueError:
                messagebox.showwarning("Bad value", "Coordinates must be whole numbers.")
                return
            if on_change:
                on_change()
            self.status.config(text=f"{label} set to {coord_list} (remember to Save).",
                               foreground="#161")
        ttk.Button(fr, text="Apply", command=apply).pack(side="left", padx=4)
        ttk.Button(fr, text="Show", command=lambda: self.show_marker(coord_list)).pack(side="left")

    def _desc_editor(self, el):
        """A free-text description box for an element (point or area)."""
        ttk.Label(self.detail, text="Description (your own notes):",
                  font=("", 9, "bold")).pack(anchor="w", pady=(12, 2))
        txt = tk.Text(self.detail, height=4, width=46, wrap="word")
        txt.insert("1.0", el.get("description", ""))
        txt.pack(anchor="w", fill="x")

        def apply(*_):
            el["description"] = txt.get("1.0", "end").strip()
            self.status.config(text="Description updated (remember to Save config.json).",
                               foreground="#161")
        txt.bind("<FocusOut>", apply)
        ttk.Button(self.detail, text="Apply description", command=apply).pack(anchor="w", pady=2)

    def show_area(self, el):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        self._clear_markers()
        for (x, y) in area_cells(el):
            sx, sy = self.gamewin.to_screen(x, y)
            self._make_marker(sx, sy, None, "#1f6feb", size=8)
        for mp in el["meantime"]:
            sx, sy = self.gamewin.to_screen(mp[0], mp[1])
            self._make_marker(sx, sy, None, "#e08a1f", size=12)
        self.root.after(4000, self._clear_markers)
        self.status.config(text="Blue = grid clicks, orange = meantime clicks.")

    # ===================================================================== #
    #  Shared helpers
    # ===================================================================== #
    def test_point(self, ref_xy):
        if self.gamewin is None:
            messagebox.showwarning("No window", "Pick the game window first.")
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        pyautogui.moveTo(x, y, duration=0.12)

    # ===================================================================== #
    #  Markers
    # ===================================================================== #
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
            return
        x, y = self.gamewin.to_screen(ref_xy[0], ref_xy[1])
        self._make_marker(x, y, text, "#e02020")
        self.root.after(2500, self._clear_markers)

    def _clear_markers(self):
        for m in self.markers:
            try:
                m.destroy()
            except Exception:
                pass
        self.markers = []

    # ===================================================================== #
    #  SEQUENCE tab
    # ===================================================================== #
    def _point_targets(self):
        opts = list(self.cfg.get("points", {}))
        for arr in ARRAY_POINTS:
            opts += [f"{arr}[{i}]" for i in range(len(self.cfg.get("arrays", {}).get(arr, [])))]
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
        ttk.Label(add, text="Target").grid(row=0, column=2, padx=4)
        self.tgt_var = ttk.Combobox(add, width=24, state="readonly", values=self._point_targets())
        self.tgt_var.grid(row=0, column=3, padx=4)
        ttk.Label(add, text="Value/clicks").grid(row=0, column=4, padx=4)
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
        if a == "element":
            self.tgt_var.config(state="readonly", values=list(self.cfg["elements"]))
            self.step_hint.config(text="element: run one of your Builder elements (point/area).")
        elif a == "key":
            self.tgt_var.config(state="disabled")
            self.step_hint.config(text="key: put the key in Value (e.g. g, m, L, o, a).")
        elif a == "wait":
            self.tgt_var.config(state="disabled")
            self.step_hint.config(text="wait: put seconds in Value (e.g. 0.5).")
        elif a == "scroll":
            self.tgt_var.config(state="readonly", values=self._point_targets())
            self.step_hint.config(text="scroll: Target = where; Value = notches (+up / -down).")
        elif a in ("click", "double click", "right click"):
            self.tgt_var.config(state="readonly", values=self._point_targets())
            self.step_hint.config(text="click: Target = point; Value = number of clicks (optional).")
        else:
            self.tgt_var.config(state="readonly", values=self._point_targets())
            self.step_hint.config(text="move: Target = point to move to.")

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
                messagebox.showwarning("Missing target", f"'{a}' needs a target.")
                return
            step["target"] = tgt
            if act == "scroll":
                step["value"] = int(val or 0)
            elif act in ("click", "double_click", "right_click") and val:
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
        if a == "element":
            return f"element  {s['target']}"
        extra = f"  x{s['clicks']}" if s.get("clicks", 1) != 1 else ""
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
            self._reload_listbox(); self.seq_list.selection_set(i - 1)

    def step_down(self):
        i = self._sel()
        if i is not None and i < len(self.sequence) - 1:
            self.sequence[i + 1], self.sequence[i] = self.sequence[i], self.sequence[i + 1]
            self._reload_listbox(); self.seq_list.selection_set(i + 1)

    def step_del(self):
        i = self._sel()
        if i is not None:
            del self.sequence[i]; self._reload_listbox()

    def step_clear(self):
        self.sequence = []; self._reload_listbox()

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
        self.status.config(text=f"Saved sequence '{name}' to config.json.", foreground="#161")

    # ===================================================================== #
    #  Footer / save
    # ===================================================================== #
    def _build_footer(self):
        self.status = ttk.Label(self.root, text="Ready.", relief="sunken",
                                anchor="w", padding=4, foreground="#333")
        self.status.pack(fill="x", side="bottom")
        bar = ttk.Frame(self.root, padding=10)
        bar.pack(fill="x", side="bottom")
        ttk.Button(bar, text="Save config.json", command=self.save).pack(side="right")
        self.saved = ttk.Label(bar, text="")
        self.saved.pack(side="right", padx=10)
        ttk.Button(bar, text="Hide markers", command=self._clear_markers).pack(side="left")

    def _write_config(self):
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)

    def save(self):
        self._write_config()
        self.saved.config(text="saved config.json", foreground="#161")

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
