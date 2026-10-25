"""
Sub-Module 5.1: Desktop App Lifecycle & Window Manager.

* Enumerates running processes and visible top-level windows.
* Robustly brings a target window to the foreground (restores minimized windows
  and works around Windows' foreground-lock with the ALT-key / AttachThreadInput
  techniques).
* Resolves and launches desktop software: Visual Studio (via vswhere), SSMS
  (standard install paths), VS Code, browsers, Office, and anything on PATH or
  registered under the Windows "App Paths" registry key (read-only access).
"""
from __future__ import annotations

import glob
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import psutil

import sys
from config import IS_MAC, IS_WINDOWS

log = logging.getLogger("omniagent.windows")

if sys.platform == "win32" or IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    import win32api
    import win32con
    import win32gui
    import win32process


def ensure_interactive_desktop() -> bool:
    """Ensures the current thread is attached to the user's interactive desktop (WinSta0\\default)."""
    if not IS_WINDOWS:
        return True
    try:
        user32 = ctypes.windll.user32
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            return bool(user32.SetThreadDesktop(h_desk))
    except Exception:
        pass
    return False

# Friendly alias -> canonical key used by the resolver and process matcher
APP_ALIASES: dict[str, str] = {
    "visual studio": "devenv", "visualstudio": "devenv", "vs": "devenv", "devenv": "devenv",
    "microsoft visual studio": "devenv",
    "ssms": "ssms", "sql server management studio": "ssms", "management studio": "ssms",
    "microsoft sql server management studio": "ssms",
    "vscode": "code", "vs code": "code", "visual studio code": "code", "code": "code",
    "chrome": "chrome", "google chrome": "chrome",
    "edge": "msedge", "microsoft edge": "msedge", "msedge": "msedge",
    "firefox": "firefox", "mozilla firefox": "firefox",
    "terminal": "wt", "windows terminal": "wt", "wt": "wt",
    "powershell": "powershell", "pwsh": "pwsh", "cmd": "cmd", "command prompt": "cmd",
    "notepad": "notepad", "notepad++": "notepad++", "explorer": "explorer", "file explorer": "explorer",
    "excel": "excel", "word": "winword", "outlook": "outlook", "powerpoint": "powerpnt",
    "dbeaver": "dbeaver", "azure data studio": "azuredatastudio", "postman": "postman",
    "calculator": "calc", "calc": "calc", "paint": "mspaint",
}

# Canonical key -> process names (lowercase, without .exe)
PROCESS_NAMES: dict[str, tuple[str, ...]] = {
    "devenv": ("devenv",), "ssms": ("ssms",), "code": ("code",), "chrome": ("chrome",),
    "msedge": ("msedge",), "firefox": ("firefox",), "wt": ("windowsterminal", "wt"),
    "powershell": ("powershell",), "pwsh": ("pwsh",), "cmd": ("cmd",), "notepad": ("notepad",),
    "notepad++": ("notepad++",), "explorer": ("explorer",), "excel": ("excel",), "winword": ("winword",),
    "outlook": ("outlook",), "powerpnt": ("powerpnt",), "dbeaver": ("dbeaver",),
    "azuredatastudio": ("azuredatastudio",), "postman": ("postman",), "calc": ("calculatorapp", "calc"),
    "mspaint": ("mspaint",),
}

TITLE_HINTS: dict[str, str] = {
    "devenv": r"Microsoft Visual Studio",
    "ssms": r"(SQL Server Management Studio|Microsoft SQL Server Management Studio)",
    "code": r"Visual Studio Code",
    "chrome": r"Google Chrome",
    "msedge": r"Microsoft.*Edge",
    "firefox": r"Mozilla Firefox",
}


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    pid: int
    process_name: str
    exe: str
    left: int
    top: int
    width: int
    height: int
    minimized: bool
    foreground: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical(query: str) -> str:
    q = query.strip().lower()
    q = re.sub(r"\.exe$", "", q)
    return APP_ALIASES.get(q, q)


# --------------------------------------------------------------------------- #
# Enumeration
# --------------------------------------------------------------------------- #
def _is_cloaked(hwnd: int) -> bool:
    try:
        cloaked = ctypes.c_int(0)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        return cloaked.value != 0
    except Exception:  # noqa: BLE001
        return False


def _proc_info(pid: int) -> tuple[str, str]:
    try:
        p = psutil.Process(pid)
        name = p.name()
        try:
            exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess):
            exe = ""
        return re.sub(r"\.exe$", "", name, flags=re.I), exe
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "", ""


def list_windows() -> list[WindowInfo]:
    if IS_WINDOWS:
        return _list_windows_win32()
    return _list_windows_posix()


def _list_windows_win32() -> list[WindowInfo]:
    import ctypes
    from ctypes import wintypes

    results: list[WindowInfo] = []
    seen_hwnds: set[int] = set()
    fg = win32gui.GetForegroundWindow()

    def process_hwnd(hwnd: int) -> None:
        if hwnd in seen_hwnds:
            return
        seen_hwnds.add(hwnd)
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title.strip() or title == "Program Manager":
                return
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                return
            if win32gui.GetWindow(hwnd, win32con.GW_OWNER) and not (ex_style & win32con.WS_EX_APPWINDOW):
                return
            if _is_cloaked(hwnd):
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                pid = 0
            name, exe = _proc_info(pid)
            try:
                l, t, r, b = win32gui.GetWindowRect(hwnd)
            except Exception:
                l = t = r = b = 0
            results.append(WindowInfo(
                hwnd=hwnd, title=title, pid=pid, process_name=name, exe=exe, left=l, top=t,
                width=r - l, height=b - t, minimized=bool(win32gui.IsIconic(hwnd)), foreground=(hwnd == fg),
            ))
        except Exception:
            pass

    # 1. Enumerate current window station/desktop
    try:
        win32gui.EnumWindows(lambda h, _: (process_hwnd(h), True)[1], None)
    except Exception:
        pass

    # 2. Enumerate primary interactive desktop (WinSta0\\default)
    try:
        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        h_desk = user32.OpenDesktopW("default", 0, False, 0x0100)
        if h_desk:
            cb = WNDENUMPROC(lambda h, _: (process_hwnd(h), True)[1])
            user32.EnumDesktopWindows(h_desk, cb, 0)
            user32.CloseDesktop(h_desk)
    except Exception:
        pass

    return results


def _list_windows_posix() -> list[WindowInfo]:
    out: list[WindowInfo] = []
    if shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-lpG"], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                hwnd = int(parts[0], 16)
                pid = int(parts[2])
                name, exe = _proc_info(pid)
                out.append(WindowInfo(hwnd, parts[8], pid, name, exe, int(parts[3]), int(parts[4]),
                                      int(parts[5]), int(parts[6]), False, False))
        except Exception as exc:  # noqa: BLE001
            log.debug("wmctrl failed: %s", exc)
    elif IS_MAC:
        script = 'tell application "System Events" to get name of (processes where background only is false)'
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            for i, name in enumerate(n.strip() for n in res.stdout.split(",") if n.strip()):
                out.append(WindowInfo(i + 1, name, 0, name.lower(), "", 0, 0, 0, 0, False, False))
        except Exception as exc:  # noqa: BLE001
            log.debug("osascript failed: %s", exc)
    return out


def find_windows(query: str) -> list[WindowInfo]:
    """Rank windows matching a process name, alias or title fragment."""
    key = canonical(query)
    q = query.strip().lower()
    procs = PROCESS_NAMES.get(key, (key,))
    hint = TITLE_HINTS.get(key)
    scored: list[tuple[int, WindowInfo]] = []
    for w in list_windows():
        pname = w.process_name.lower()
        title = w.title.lower()
        score = 0
        if pname in procs:
            score = 100
        elif hint and re.search(hint, w.title, re.I):
            score = 90
        elif title == q:
            score = 85
        elif title.startswith(q):
            score = 70
        elif q and q in title:
            score = 60
        elif q and q in pname:
            score = 50
        if score:
            if w.foreground:
                score += 2
            if not w.minimized:
                score += 1
            scored.append((score, w))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [w for _, w in scored]


# --------------------------------------------------------------------------- #
# Focus
# --------------------------------------------------------------------------- #
def focus_window(hwnd: int) -> bool:
    if not IS_WINDOWS:
        if shutil.which("wmctrl"):
            subprocess.run(["wmctrl", "-ia", hex(hwnd)], capture_output=True, timeout=5)
            return True
        return False
    ensure_interactive_desktop()
    try:
        user32 = ctypes.windll.user32
        if not win32gui.IsWindow(hwnd):
            return False
        if win32gui.IsIconic(hwnd):
            user32.ShowWindowAsync(hwnd, win32con.SW_RESTORE)
        else:
            user32.ShowWindowAsync(hwnd, win32con.SW_SHOW)

        # 1. Force window focus using Windows Alt-Tab switcher API
        user32.SwitchToThisWindow(hwnd, True)

        # 2. ALT key tap unlocks SetForegroundWindow for background processes
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        try:
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
        except Exception:
            pass
        if win32gui.GetForegroundWindow() != hwnd:
            fg = win32gui.GetForegroundWindow()
            fg_thread, _ = win32process.GetWindowThreadProcessId(fg) if fg else (0, 0)
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            cur_thread = win32api.GetCurrentThreadId()
            attached = []
            for t in {fg_thread, target_thread}:
                if t and t != cur_thread:
                    try:
                        ctypes.windll.user32.AttachThreadInput(cur_thread, t, True)
                        attached.append(t)
                    except Exception:  # noqa: BLE001
                        pass
            try:
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetFocus(hwnd)
            except Exception:  # noqa: BLE001
                pass
            for t in attached:
                try:
                    ctypes.windll.user32.AttachThreadInput(cur_thread, t, False)
                except Exception:  # noqa: BLE001
                    pass
        time.sleep(0.25)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as exc:  # noqa: BLE001
        log.warning("focus_window(%s) failed: %s", hwnd, exc)
        return False


def window_control(hwnd: int, action: str) -> bool:
    if not IS_WINDOWS:
        return False
    cmds = {
        "minimize": win32con.SW_MINIMIZE, "maximize": win32con.SW_MAXIMIZE,
        "restore": win32con.SW_RESTORE, "show": win32con.SW_SHOW,
    }
    if action == "close":
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    if action in cmds:
        win32gui.ShowWindow(hwnd, cmds[action])
        return True
    return False


def foreground_window() -> Optional[WindowInfo]:
    for w in list_windows():
        if w.foreground:
            return w
    return None


# --------------------------------------------------------------------------- #
# Resolution & launch
# --------------------------------------------------------------------------- #
def _vswhere_devenv() -> Optional[str]:
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = Path(pf86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if vswhere.exists():
        try:
            res = subprocess.run([str(vswhere), "-latest", "-prerelease", "-property", "productPath"],
                                 capture_output=True, text=True, timeout=15)
            path = res.stdout.strip().splitlines()[0] if res.stdout.strip() else ""
            if path and Path(path).exists():
                return path
        except Exception as exc:  # noqa: BLE001
            log.debug("vswhere failed: %s", exc)
    for pattern in (r"C:\Program Files\Microsoft Visual Studio\*\*\Common7\IDE\devenv.exe",
                    r"C:\Program Files (x86)\Microsoft Visual Studio\*\*\Common7\IDE\devenv.exe"):
        hits = sorted(glob.glob(pattern), reverse=True)
        if hits:
            return hits[0]
    return None


def _ssms_path() -> Optional[str]:
    patterns = [
        r"C:\Program Files\Microsoft SQL Server Management Studio *\Release\Common7\IDE\SSMS.exe",
        r"C:\Program Files\Microsoft SQL Server Management Studio *\Common7\IDE\Ssms.exe",
        r"C:\Program Files (x86)\Microsoft SQL Server Management Studio *\Common7\IDE\Ssms.exe",
        r"C:\Program Files (x86)\Microsoft SQL Server\*\Tools\Binn\ManagementStudio\Ssms.exe",
    ]
    for pattern in patterns:
        hits = sorted(glob.glob(pattern), reverse=True)
        if hits:
            return hits[0]
    return None


def _app_paths_registry(exe_name: str) -> Optional[str]:
    if not IS_WINDOWS:
        return None
    import winreg

    if not exe_name.lower().endswith(".exe"):
        exe_name += ".exe"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}") as key:
                value, _ = winreg.QueryValueEx(key, "")
                value = os.path.expandvars(value.strip('"'))
                if value and Path(value).exists():
                    return value
        except OSError:
            continue
    return None


def resolve_executable(query: str) -> Optional[str]:
    raw = query.strip().strip('"')
    if raw and Path(raw).exists():
        return str(Path(raw))
    key = canonical(raw)
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        known: dict[str, list[str]] = {
            "code": [rf"{local}\Programs\Microsoft VS Code\Code.exe", rf"{pf}\Microsoft VS Code\Code.exe"],
            "chrome": [rf"{pf}\Google\Chrome\Application\chrome.exe", rf"{pf86}\Google\Chrome\Application\chrome.exe",
                       rf"{local}\Google\Chrome\Application\chrome.exe"],
            "msedge": [rf"{pf86}\Microsoft\Edge\Application\msedge.exe", rf"{pf}\Microsoft\Edge\Application\msedge.exe"],
            "firefox": [rf"{pf}\Mozilla Firefox\firefox.exe", rf"{pf86}\Mozilla Firefox\firefox.exe"],
            "notepad++": [rf"{pf}\Notepad++\notepad++.exe", rf"{pf86}\Notepad++\notepad++.exe"],
            "azuredatastudio": [rf"{local}\Programs\Azure Data Studio\azuredatastudio.exe"],
            "dbeaver": [rf"{pf}\DBeaver\dbeaver.exe", rf"{local}\DBeaver\dbeaver.exe"],
        }
        if key == "devenv":
            found = _vswhere_devenv()
            if found:
                return found
        if key == "ssms":
            found = _ssms_path()
            if found:
                return found
        for candidate in known.get(key, []):
            if Path(candidate).exists():
                return candidate
        reg = _app_paths_registry(key)
        if reg:
            return reg
    which = shutil.which(key) or shutil.which(raw)
    return which


def launch_app(query: str, args: list[str] | None = None, cwd: str | None = None) -> dict[str, Any]:
    args = args or []
    exe = resolve_executable(query)
    if IS_MAC and not exe:
        res = subprocess.run(["open", "-a", query] + (["--args"] + args if args else []), capture_output=True, text=True)
        return {"launched": res.returncode == 0, "exe": query, "pid": None, "error": res.stderr.strip()}
    if not exe:
        if IS_WINDOWS:
            try:
                os.startfile(query)  # type: ignore[attr-defined]  # shell-registered names / URLs
                return {"launched": True, "exe": query, "pid": None, "via": "shell"}
            except OSError as exc:
                return {"launched": False, "exe": None, "pid": None, "error": f"Could not resolve '{query}': {exc}"}
        return {"launched": False, "exe": None, "pid": None, "error": f"Executable '{query}' not found on PATH."}
    flags = 0
    if IS_WINDOWS:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    try:
        proc = subprocess.Popen([exe] + args, cwd=cwd, creationflags=flags, close_fds=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"launched": True, "exe": exe, "pid": proc.pid}
    except OSError as exc:
        return {"launched": False, "exe": exe, "pid": None, "error": str(exc)}


def wait_for_window(query: str, timeout: float = 30.0, pid: Optional[int] = None) -> Optional[WindowInfo]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        candidates = find_windows(query)
        if pid:
            try:
                family = {pid} | {c.pid for c in psutil.Process(pid).children(recursive=True)}
            except psutil.Error:
                family = {pid}
            by_pid = [w for w in list_windows() if w.pid in family]
            if by_pid:
                return by_pid[0]
        if candidates:
            return candidates[0]
        time.sleep(0.5)
    return None


def launch_or_focus(query: str, args: list[str] | None = None, timeout: float = 45.0) -> dict[str, Any]:
    existing = find_windows(query)
    if existing:
        target = existing[0]
        ok = focus_window(target.hwnd)
        return {
            "action": "focused_existing",
            "focused": ok,
            "reused_existing_instance": True,
            "window": target.as_dict(),
            "message": f"Application '{target.title}' is already open. Reusing active window instance."
        }
    launched = launch_app(query, args)
    if not launched.get("launched"):
        return {"action": "launch_failed", "focused": False, **launched}
    win = wait_for_window(query, timeout=timeout, pid=launched.get("pid"))
    if not win:
        return {"action": "launched", "focused": False, "launch": launched,
                "note": "Process started but no window appeared yet; capture the screen to verify."}
    ok = focus_window(win.hwnd)
    return {"action": "launched", "focused": ok, "launch": launched, "window": win.as_dict()}


def list_processes(limit: int = 60) -> list[dict[str, Any]]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            mem = p.info["memory_info"].rss if p.info.get("memory_info") else 0
            procs.append({"pid": p.info["pid"], "name": p.info["name"], "rss_mb": round(mem / 1048576, 1)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x["rss_mb"], reverse=True)
    return procs[:limit]
