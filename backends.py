#!/usr/bin/env python3
"""
Input backends for the Firestone bot.

Two interchangeable backends expose the same low-level verbs the bot needs:

  activate()                 ensure the game is ready to receive input
  move(rx, ry)               move/point at a reference coordinate
  mouse_down(rx, ry, btn)    press a mouse button at a reference coordinate
  mouse_up(rx, ry, btn)      release it
  scroll(rx, ry, notches)    wheel scroll (+up / -down)
  tap_key(token)             press a key ('g', 'm', 'L' = Shift+l, ...)

Reference coordinates are positions in the configured reference resolution
(e.g. 1920x1080); each backend rescales them to the live window.

  * ForegroundBackend  — pyautogui. Drives the real cursor; the game must be
    focused/visible. Simple and reliable, but takes over your mouse.

  * BackgroundBackend  — Win32 PostMessage. Injects events directly into the
    game window without moving your real cursor, so the bot can run while you
    use the PC. Whether it actually registers depends on how the game reads
    input — many games ignore posted messages. Windows only.
"""

import sys

import pyautogui

try:
    import pygetwindow as gw
except Exception:
    gw = None


def _match_windows(title):
    """Titled windows containing `title`, exact matches preferred (so a folder
    window merely named 'Firestone' doesn't shadow the game)."""
    wins = [w for w in gw.getWindowsWithTitle(title) if w.title]
    exact = [w for w in wins if w.title == title]
    return exact or wins


_fg_api_ready = False


def _force_foreground(hwnd):
    """Reliably bring a window to the foreground on Windows.

    Plain SetForegroundWindow is blocked for background processes, so we
    temporarily attach our input thread to the current foreground thread (the
    standard AttachThreadInput trick) — without this the game never gets focus
    and wheel/keyboard input is ignored."""
    global _fg_api_ready
    import ctypes
    from ctypes import wintypes

    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    if not _fg_api_ready:
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, wintypes.LPDWORD]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetForegroundWindow.restype = wintypes.HWND
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.BringWindowToTop.argtypes = [wintypes.HWND]
        u.IsIconic.argtypes = [wintypes.HWND]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetFocus.argtypes = [wintypes.HWND]
        u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        _fg_api_ready = True

    SW_RESTORE = 9
    if u.IsIconic(hwnd):
        u.ShowWindow(hwnd, SW_RESTORE)
    fg = u.GetForegroundWindow()
    if fg == hwnd:
        return
    cur = k.GetCurrentThreadId()
    tgt = u.GetWindowThreadProcessId(hwnd, None)
    fgt = u.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = []
    try:
        if fgt and fgt != cur:
            u.AttachThreadInput(cur, fgt, True)
            attached.append(fgt)
        if tgt and tgt != cur:
            u.AttachThreadInput(cur, tgt, True)
            attached.append(tgt)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        try:
            u.SetFocus(hwnd)
        except Exception:
            pass
    finally:
        for t in attached:
            u.AttachThreadInput(cur, t, False)


# --------------------------------------------------------------------------- #
#  Foreground (pyautogui) — moves the real cursor
# --------------------------------------------------------------------------- #
class ForegroundBackend:
    name = "foreground"

    def __init__(self, title, reference_size, move_duration=0.0):
        self.title = title
        self.ref_w, self.ref_h = reference_size
        self.move_dur = move_duration

    def _rect(self):
        if gw is None:
            raise RuntimeError("pygetwindow is required for the foreground backend.")
        wins = _match_windows(self.title)
        if not wins:
            raise RuntimeError(
                f"No window whose title contains {self.title!r} was found."
            )
        w = wins[0]
        return (w.left, w.top, w.width, w.height)

    def _screen(self, rx, ry):
        left, top, width, height = self._rect()
        return (int(round(left + rx / self.ref_w * width)),
                int(round(top + ry / self.ref_h * height)))

    def activate(self):
        if gw is None:
            return
        wins = _match_windows(self.title)
        if not wins:
            return
        w = wins[0]
        hwnd = getattr(w, "_hWnd", None)
        if hwnd and sys.platform.startswith("win"):
            try:
                _force_foreground(hwnd)
                return
            except Exception:
                pass
        try:                                   # non-Windows / fallback
            if w.isMinimized:
                w.restore()
            w.activate()
        except Exception:
            pass

    def move(self, rx, ry):
        x, y = self._screen(rx, ry)
        pyautogui.moveTo(x, y, duration=self.move_dur)

    def mouse_down(self, rx, ry, button="left"):
        x, y = self._screen(rx, ry)
        pyautogui.mouseDown(x=x, y=y, button=button)

    def mouse_up(self, rx, ry, button="left"):
        x, y = self._screen(rx, ry)
        pyautogui.mouseUp(x=x, y=y, button=button)

    def scroll(self, rx, ry, notches):
        x, y = self._screen(rx, ry)
        # Move there first (handles multi-monitor / negative coords), then scroll
        # at the current position. pyautogui passes its arg straight as the wheel
        # delta (120 = one notch) and clamps x/y to the PRIMARY monitor — so we
        # must NOT pass x/y, and must scale by 120 to get real notches.
        pyautogui.moveTo(x, y, duration=self.move_dur)
        notches = int(notches)
        step = 120 if notches >= 0 else -120
        for _ in range(abs(notches)):
            pyautogui.scroll(step)

    def tap_key(self, token):
        if len(token) == 1 and token.isalpha() and token.isupper():
            pyautogui.hotkey("shift", token.lower())
        else:
            pyautogui.press(token.lower() if len(token) == 1 else token)


# --------------------------------------------------------------------------- #
#  Background (Win32 PostMessage) — does not touch the real cursor
# --------------------------------------------------------------------------- #
class BackgroundBackend:
    name = "background"

    # Win32 message constants
    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
    WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0204, 0x0205
    WM_MOUSEWHEEL = 0x020A
    WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
    MK_LBUTTON, MK_RBUTTON = 0x0001, 0x0002
    VK_SHIFT = 0x10

    def __init__(self, title, reference_size, move_duration=0.0):
        if not sys.platform.startswith("win"):
            raise RuntimeError("The background backend is Windows-only.")
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.title = title
        self.ref_w, self.ref_h = reference_size
        self._hwnd = None

        self.user32.PostMessageW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.PostMessageW.restype = wintypes.BOOL
        self.user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user32.MapVirtualKeyW.restype = wintypes.UINT

    # ---- window handle + geometry ---------------------------------------- #
    def _hwnd_valid(self):
        return self._hwnd and self.user32.IsWindow(self._hwnd)

    def hwnd(self):
        if self._hwnd_valid():
            return self._hwnd
        if gw is None:
            raise RuntimeError("pygetwindow is required to locate the window handle.")
        wins = _match_windows(self.title)
        if not wins:
            raise RuntimeError(
                f"No window whose title contains {self.title!r} was found."
            )
        self._hwnd = wins[0]._hWnd
        return self._hwnd

    def _client_size(self):
        rect = self.wintypes.RECT()
        self.user32.GetClientRect(self.hwnd(), self.ctypes.byref(rect))
        return rect.right, rect.bottom  # left/top are always 0 for client rect

    def _client_xy(self, rx, ry):
        w, h = self._client_size()
        return int(round(rx / self.ref_w * w)), int(round(ry / self.ref_h * h))

    def _screen_xy(self, rx, ry):
        cx, cy = self._client_xy(rx, ry)
        pt = self.wintypes.POINT(cx, cy)
        self.user32.ClientToScreen(self.hwnd(), self.ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def _lparam(x, y):
        return ((y & 0xFFFF) << 16) | (x & 0xFFFF)

    def _post(self, msg, wparam, lparam):
        self.user32.PostMessageW(self.hwnd(), msg, wparam, lparam)

    # ---- backend verbs ---------------------------------------------------- #
    def activate(self):
        # Deliberately does NOT focus/raise the window — that's the whole point.
        self.hwnd()  # refresh handle / raise a clear error if the game vanished

    def move(self, rx, ry):
        x, y = self._client_xy(rx, ry)
        self._post(self.WM_MOUSEMOVE, 0, self._lparam(x, y))

    def mouse_down(self, rx, ry, button="left"):
        x, y = self._client_xy(rx, ry)
        if button == "right":
            self._post(self.WM_RBUTTONDOWN, self.MK_RBUTTON, self._lparam(x, y))
        else:
            self._post(self.WM_MOUSEMOVE, self.MK_LBUTTON, self._lparam(x, y))
            self._post(self.WM_LBUTTONDOWN, self.MK_LBUTTON, self._lparam(x, y))

    def mouse_up(self, rx, ry, button="left"):
        x, y = self._client_xy(rx, ry)
        if button == "right":
            self._post(self.WM_RBUTTONUP, 0, self._lparam(x, y))
        else:
            self._post(self.WM_LBUTTONUP, 0, self._lparam(x, y))

    def scroll(self, rx, ry, notches):
        # WM_MOUSEWHEEL uses SCREEN coords in lParam and delta in the high word.
        sx, sy = self._screen_xy(rx, ry)
        delta = int(notches) * 120
        wparam = (delta & 0xFFFF) << 16
        self._post(self.WM_MOUSEWHEEL, wparam, self._lparam(sx, sy))

    def tap_key(self, token):
        shifted = len(token) == 1 and token.isalpha() and token.isupper()
        vk = ord(token.upper()) if len(token) == 1 else self._named_vk(token)
        if shifted:
            self._key_event(self.VK_SHIFT, down=True)
        self._key_event(vk, down=True)
        self._key_event(vk, down=False)
        if shifted:
            self._key_event(self.VK_SHIFT, down=False)

    def _key_event(self, vk, down):
        scan = self.user32.MapVirtualKeyW(vk, 0)
        lparam = 1 | (scan << 16)
        if not down:
            lparam |= (1 << 30) | (1 << 31)
        self._post(self.WM_KEYDOWN if down else self.WM_KEYUP, vk, lparam)

    @staticmethod
    def _named_vk(token):
        names = {"enter": 0x0D, "esc": 0x1B, "escape": 0x1B, "space": 0x20,
                 "tab": 0x09}
        if token.lower() in names:
            return names[token.lower()]
        raise ValueError(f"Unsupported key token for background backend: {token!r}")


# --------------------------------------------------------------------------- #
def make_backend(config, background=False):
    title = config["window_title"]
    ref = config["reference_size"]
    dur = config["timing"].get("move_duration", 0.0)
    if background:
        return BackgroundBackend(title, ref, dur)
    return ForegroundBackend(title, ref, dur)
