#!/usr/bin/env pythonw
"""
Firestone launcher — a small control bar.

  [Setup]  opens the calibration GUI (setup_gui.py)
  [Run]    runs the bot with the chosen profile/sequence in its own console
  [Stop]   kills the running bot
  [Folder] opens the project folder

Double-click this file (it runs without a console via pythonw), or build it into
a pinnable Firestone.exe with build_exe.ps1.  Requires Python with the project's
dependencies installed (pip install -r requirements.txt).
"""

import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

# Where the scripts live (next to this file, or next to the .exe when frozen).
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

CONFIG = os.path.join(BASE, "config.json")
EXAMPLE = os.path.join(BASE, "config.example.json")
CREATE_NEW_CONSOLE = 0x00000010  # so the bot gets its own window + Ctrl+C


def find_python():
    """Locate a Python interpreter to launch the scripts with."""
    for cand in ("py", "python", "python3"):
        path = shutil.which(cand)
        if path:
            return path
    return None


def load_config():
    path = CONFIG if os.path.exists(CONFIG) else EXAMPLE
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"profiles": {}, "sequences": {}}


class Launcher:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.py = find_python()
        cfg = load_config()

        root.title("Firestone")
        root.resizable(False, False)
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        frm = ttk.Frame(root, padding=8)
        frm.pack(fill="both", expand=True)

        ttk.Button(frm, text="⚙ Setup", width=9, command=self.open_setup).grid(row=0, column=0, padx=3)

        # Run target = profiles + sequences, prefixed so we know which is which.
        targets = [f"profile: {n}" for n in cfg.get("profiles", {})]
        targets += [f"sequence: {n}" for n in cfg.get("sequences", {})]
        self.target = ttk.Combobox(frm, width=24, state="readonly", values=targets)
        if targets:
            self.target.current(0)
        self.target.grid(row=0, column=1, padx=3)

        self.bg = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="bg", variable=self.bg).grid(row=0, column=2, padx=2)

        ttk.Label(frm, text="reps").grid(row=0, column=3)
        self.reps = ttk.Spinbox(frm, from_=1, to=9999, width=5)
        self.reps.set(1)
        self.reps.grid(row=0, column=4, padx=2)

        ttk.Button(frm, text="▶ Run", width=7, command=self.run).grid(row=0, column=5, padx=3)
        self.stop_btn = ttk.Button(frm, text="■ Stop", width=7, command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=6, padx=3)
        ttk.Button(frm, text="📁", width=3, command=self.open_folder).grid(row=0, column=7, padx=3)

        self.status = ttk.Label(root, text="Ready.", relief="sunken", anchor="w", padding=3)
        self.status.pack(fill="x")

        if self.py is None:
            self.status.config(text="Python not found on PATH — install Python 3.")
        root.after(1000, self._poll)

    # ---- actions ---------------------------------------------------------- #
    def _launch(self, args, new_console=False):
        if self.py is None:
            messagebox.showerror("No Python", "Could not find a Python interpreter on PATH.")
            return None
        flags = CREATE_NEW_CONSOLE if (new_console and os.name == "nt") else 0
        return subprocess.Popen([self.py, *args], cwd=BASE, creationflags=flags)

    def open_setup(self):
        self._launch(["setup_gui.py"])
        self.status.config(text="Opened the setup GUI.")

    def run(self):
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("Already running", "The bot is already running. Stop it first.")
            return
        sel = self.target.get()
        if not sel:
            messagebox.showwarning("Nothing selected", "Pick a profile or sequence to run.")
            return
        kind, name = sel.split(": ", 1)
        args = ["firestone_bot.py"]
        if kind == "profile":
            args += ["--profile", name]
        else:
            args += ["--sequence", name, "--reps", str(self.reps.get())]
        if self.bg.get():
            args += ["--background"]
        self.proc = self._launch(args, new_console=True)
        if self.proc:
            self.stop_btn.config(state="normal")
            self.status.config(text=f"Running {sel}"
                                    f"{' (background)' if self.bg.get() else ''} — "
                                    "see the new console window.")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            if os.name == "nt":
                subprocess.call(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.proc.terminate()
            self.status.config(text="Stopped the bot.")
        self.proc = None
        self.stop_btn.config(state="disabled")

    def open_folder(self):
        if os.name == "nt":
            os.startfile(BASE)
        else:
            subprocess.call(["xdg-open", BASE])

    def _poll(self):
        if self.proc and self.proc.poll() is not None:
            self.proc = None
            self.stop_btn.config(state="disabled")
            self.status.config(text="Bot finished.")
        self.root.after(1000, self._poll)


def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
