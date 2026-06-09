"""Detect the currently focused application across X11 and Wayland.

Provides :class:`FocusWatcher`, a background poller that emits the focused
application's identifier (its window class / ``app_id``, lower-cased) whenever it
changes, so Stream Deck pages can follow the focused application.

Detection is best effort and backend specific:

* Hyprland (Wayland) - ``hyprctl``
* Sway / wlroots (Wayland) - ``swaymsg``
* KDE Plasma (Wayland or X11) - ``kdotool``, when installed
* X11 - ``xdotool``, falling back to ``xprop``

Some compositors (notably GNOME on Wayland) do not let an application read the
focused window of other applications. There the focused app cannot be detected
and the feature simply stays inactive.
"""

import json
import os
import shutil
import subprocess
from typing import Callable, List, Optional

from PySide6.QtCore import QThread, Signal


def _run(command: List[str]) -> Optional[str]:
    """Runs a command and returns its stdout, or None on any failure."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1.0)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _normalize(app: Optional[str]) -> Optional[str]:
    if not app:
        return None
    app = app.strip().lower()
    return app or None


def _from_hyprland() -> Optional[str]:
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or not shutil.which("hyprctl"):
        return None
    output = _run(["hyprctl", "-j", "activewindow"])
    if not output:
        return None
    try:
        data = json.loads(output)
    except ValueError:
        return None
    return _normalize(data.get("class"))


def _find_focused_node(node: dict) -> Optional[dict]:
    if node.get("focused"):
        return node
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        found = _find_focused_node(child)
        if found:
            return found
    return None


def _from_sway() -> Optional[str]:
    if not os.environ.get("SWAYSOCK") or not shutil.which("swaymsg"):
        return None
    output = _run(["swaymsg", "-t", "get_tree"])
    if not output:
        return None
    try:
        tree = json.loads(output)
    except ValueError:
        return None
    node = _find_focused_node(tree)
    if not node:
        return None
    # Wayland-native windows expose app_id; XWayland ones expose a window class.
    return _normalize(node.get("app_id") or (node.get("window_properties") or {}).get("class"))


def _from_kdotool() -> Optional[str]:
    if not shutil.which("kdotool"):
        return None
    window = _run(["kdotool", "getactivewindow"])
    if not window or not window.strip():
        return None
    return _normalize(_run(["kdotool", "getwindowclassname", window.strip()]))


def _from_xdotool() -> Optional[str]:
    if not os.environ.get("DISPLAY") or not shutil.which("xdotool"):
        return None
    return _normalize(_run(["xdotool", "getactivewindow", "getwindowclassname"]))


def _from_xprop() -> Optional[str]:
    if not os.environ.get("DISPLAY") or not shutil.which("xprop"):
        return None
    root = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
    if not root or "0x" not in root:
        return None
    window_id = root.split()[-1]
    output = _run(["xprop", "-id", window_id, "WM_CLASS"])
    if not output or "=" not in output:
        return None
    # WM_CLASS(STRING) = "instance", "Class" -- use the class (last quoted value).
    values = [part.strip().strip('"') for part in output.split("=", 1)[1].split(",")]
    values = [value for value in values if value]
    return _normalize(values[-1] if values else None)


# Detectors tried in order: Wayland-specific ones first, then X11 helpers.
_DETECTORS: List[Callable[[], Optional[str]]] = [
    _from_hyprland,
    _from_sway,
    _from_kdotool,
    _from_xdotool,
    _from_xprop,
]


def _safe(detector: Callable[[], Optional[str]]) -> Optional[str]:
    try:
        return detector()
    except Exception:  # noqa: BLE001 - detection must never crash the watcher
        return None


def get_focused_app() -> Optional[str]:
    """Returns the focused application's identifier, or None if it cannot be
    determined (or nothing is focused).

    A Wayland compositor that can report the focused window is *authoritative*:
    when it reports no focused window we must NOT fall through to the X11 helpers,
    because under XWayland ``xprop``/``xdotool`` still report a stale active
    window (e.g. on an empty Sway workspace they would return the last app)."""
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
        return _safe(_from_hyprland)
    if os.environ.get("SWAYSOCK") and shutil.which("swaymsg"):
        return _safe(_from_sway)
    for detector in _DETECTORS:
        app = _safe(detector)
        if app:
            return app
    return None


def focus_detection_available() -> bool:
    """True if a focus-detection backend is able to report the focused app."""
    return get_focused_app() is not None


def _collect_sway_apps(node: dict, found: set) -> None:
    app = node.get("app_id") or (node.get("window_properties") or {}).get("class")
    normalized = _normalize(app)
    if normalized:
        found.add(normalized)
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        _collect_sway_apps(child, found)


def _open_from_sway() -> set:
    if not os.environ.get("SWAYSOCK") or not shutil.which("swaymsg"):
        return set()
    output = _run(["swaymsg", "-t", "get_tree"])
    if not output:
        return set()
    try:
        tree = json.loads(output)
    except ValueError:
        return set()
    found: set = set()
    _collect_sway_apps(tree, found)
    return found


def _open_from_hyprland() -> set:
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or not shutil.which("hyprctl"):
        return set()
    output = _run(["hyprctl", "-j", "clients"])
    if not output:
        return set()
    try:
        clients = json.loads(output)
    except ValueError:
        return set()
    return {app for app in (_normalize(client.get("class")) for client in clients) if app}


def _open_from_x11() -> set:
    if not os.environ.get("DISPLAY") or not shutil.which("xprop"):
        return set()
    listing = _run(["xprop", "-root", "_NET_CLIENT_LIST"])
    if not listing or "#" not in listing:
        return set()
    window_ids = [token.strip(",") for token in listing.split("#", 1)[1].split() if token.strip(",").startswith("0x")]
    found: set = set()
    for window_id in window_ids:
        output = _run(["xprop", "-id", window_id, "WM_CLASS"])
        if not output or "=" not in output:
            continue
        values = [part.strip().strip('"') for part in output.split("=", 1)[1].split(",")]
        normalized = _normalize(values[-1] if values else None)
        if normalized:
            found.add(normalized)
    return found


def list_open_apps() -> List[str]:
    """Returns the identifiers of currently open applications, so the user can
    pick one to bind to a page. Best effort; may be empty on unsupported
    systems."""
    apps: set = set()
    for collector in (_open_from_sway, _open_from_hyprland, _open_from_x11):
        try:
            apps.update(collector())
        except Exception:  # noqa: BLE001 - never let enumeration crash callers
            pass
    return sorted(apps)


class FocusWatcher(QThread):
    """Polls the focused application and emits ``focus_changed`` when it changes."""

    focus_changed = Signal(str)

    def __init__(self, parent=None, interval: float = 0.5):
        super().__init__(parent)
        self._interval_ms = int(interval * 1000)
        self._running = False

    def run(self) -> None:  # noqa: N802 - QThread entry point
        self._running = True
        last: Optional[str] = None
        while self._running:
            app = get_focused_app()
            if app != last:
                last = app
                # Emit "" when focus is lost (no window focused) so listeners can
                # react to "nothing focused" too.
                self.focus_changed.emit(app or "")
            self.msleep(self._interval_ms)

    def stop(self) -> None:
        """Stops the watcher and waits for the thread to finish."""
        self._running = False
        self.wait(2000)
