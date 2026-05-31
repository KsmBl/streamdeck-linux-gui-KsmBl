"""Discovery of installed desktop applications and their icons.

This module makes it easy to map an installed program to a Stream Deck button
without having to know the exact launch command. It reads freedesktop
``.desktop`` entries from the standard XDG locations and resolves a fitting
icon for each application so it can be used directly as the button image.
"""

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

# Field codes that may appear in a desktop entry Exec line. They are meant to be
# expanded by the launcher (file names, urls, the icon, ...) and make no sense
# when we run the program directly, so we strip them out.
# See https://specifications.freedesktop.org/desktop-entry-spec/latest/ar01s07.html
_FIELD_CODE_RE = re.compile(r"%[fFuUdDnNickvm]")

# Characters that are not safe to use in a cached icon file name.
_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]")

# Directories (relative to /usr/share and friends) where loose icons may live
# when they are not part of a proper icon theme.
_PIXMAP_DIRS = ("/usr/share/pixmaps", "/usr/local/share/pixmaps")

# Image extensions that the button rendering pipeline can read. Raster formats
# are preferred when an icon is available in several formats; SVGs are supported
# too (rendered with cairosvg downstream).
_RASTER_EXTENSIONS = (".png", ".xpm")
_VECTOR_EXTENSIONS = (".svg", ".svgz")
_ICON_EXTENSIONS = _RASTER_EXTENSIONS + _VECTOR_EXTENSIONS

# A raster icon at least this large is considered good enough to use as-is in
# preference to a scalable (vector) icon.
_MIN_PREFERRED_RASTER_SIZE = 48

_ICON_SIZE_DIR_RE = re.compile(r"(?:^|/)(\d+)x\1(?:/|$)")


@dataclass
class DesktopApplication:
    """A single installed application discovered from a .desktop entry."""

    name: str
    "The human readable name of the application, e.g. 'Firefox'"

    command: str
    "The command used to launch the application, with field codes removed"

    icon_name: str
    "The Icon value from the desktop entry (a theme name or an absolute path)"


def _desktop_directories() -> List[str]:
    """Returns the directories that may contain .desktop entries, most
    specific (user) first so that user entries take precedence."""
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"

    directories = [os.path.join(data_home, "applications")]
    for base in data_dirs.split(":"):
        base = base.strip()
        if base:
            directories.append(os.path.join(base, "applications"))

    # Flatpak exports its applications outside of XDG_DATA_DIRS in some setups.
    directories.append(os.path.expanduser("~/.local/share/flatpak/exports/share/applications"))
    directories.append("/var/lib/flatpak/exports/share/applications")
    return directories


def _clean_command(exec_value: str) -> str:
    """Removes desktop entry field codes from an Exec value and collapses
    surrounding whitespace so the result can be run directly."""
    return " ".join(_FIELD_CODE_RE.sub("", exec_value).split())


def parse_desktop_file(path: str) -> Optional[DesktopApplication]:
    """Parses a single .desktop file. Returns ``None`` if the file is not a
    visible, launchable application."""
    name = ""
    exec_value = ""
    icon = ""
    no_display = False
    hidden = False
    entry_type = ""
    in_main_section = False

    try:
        with open(path, encoding="utf-8", errors="replace") as desktop_file:
            for raw_line in desktop_file:
                line = raw_line.strip()
                if line.startswith("[") and line.endswith("]"):
                    # Only the [Desktop Entry] group describes the application
                    # itself, the rest are actions and should be ignored.
                    in_main_section = line == "[Desktop Entry]"
                    continue
                if not in_main_section or "=" not in line:
                    continue

                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()

                # Localised keys look like Name[de]; we only want the default.
                if key == "Name" and not name:
                    name = value
                elif key == "Exec" and not exec_value:
                    exec_value = value
                elif key == "Icon" and not icon:
                    icon = value
                elif key == "NoDisplay":
                    no_display = value.lower() == "true"
                elif key == "Hidden":
                    hidden = value.lower() == "true"
                elif key == "Type":
                    entry_type = value
    except OSError:
        return None

    if entry_type and entry_type != "Application":
        return None
    if no_display or hidden:
        return None
    if not name or not exec_value:
        return None

    command = _clean_command(exec_value)
    if not command:
        return None

    return DesktopApplication(name=name, command=command, icon_name=icon)


def list_desktop_applications() -> List[DesktopApplication]:
    """Scans the standard locations and returns the installed applications,
    sorted alphabetically by name. Entries with the same .desktop file name are
    de-duplicated, keeping the most specific (user) one."""
    found: Dict[str, DesktopApplication] = {}
    for directory in _desktop_directories():
        if not os.path.isdir(directory):
            continue
        for root, _dirs, files in os.walk(directory):
            for file_name in files:
                if not file_name.endswith(".desktop"):
                    continue
                # Directories are visited user-first, so the first definition of
                # a given desktop file id wins and shadows system entries.
                if file_name in found:
                    continue
                application = parse_desktop_file(os.path.join(root, file_name))
                if application is not None:
                    found[file_name] = application

    return sorted(found.values(), key=lambda application: application.name.lower())


def _icon_search_directories() -> List[str]:
    """Returns the freedesktop icon base directories, in lookup order."""
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"

    directories = [os.path.expanduser("~/.icons"), os.path.join(data_home, "icons")]
    for base in data_dirs.split(":"):
        base = base.strip()
        if base:
            directories.append(os.path.join(base, "icons"))
    directories.extend(_PIXMAP_DIRS)
    return directories


def _raster_size_score(path: str) -> int:
    """A larger score means a more desirable raster icon. Icons stored in a
    ``<n>x<n>`` themed directory are ranked by that size."""
    match = _ICON_SIZE_DIR_RE.search(path)
    if match:
        return int(match.group(1))
    return 0


def find_icon_file(icon_name: str) -> Optional[str]:
    """Resolves a desktop entry Icon value to a concrete image file on disk.

    Supports absolute paths as well as theme/pixmap icon names, searching the
    standard freedesktop icon directories directly (so it does not depend on a
    running desktop environment exposing the active icon theme to Qt).

    Prefers a reasonably sized raster icon; otherwise falls back to a scalable
    (vector) icon, then to whatever raster icon is available. Returns ``None``
    when no icon file can be found.
    """
    if not icon_name:
        return None

    if os.path.isabs(icon_name):
        return icon_name if os.path.isfile(icon_name) else None

    # Some entries (incorrectly) include an extension in the Icon value.
    base_name = icon_name
    for extension in _ICON_EXTENSIONS:
        if base_name.lower().endswith(extension):
            base_name = base_name[: -len(extension)]
            break

    raster_candidates: Dict[str, Tuple[int, Optional[str]]] = {
        extension: (-1, None) for extension in _RASTER_EXTENSIONS
    }
    vector_candidate: Optional[str] = None

    wanted = {base_name + extension: extension for extension in _ICON_EXTENSIONS}
    for directory in _icon_search_directories():
        if not os.path.isdir(directory):
            continue
        for root, _dirs, files in os.walk(directory):
            for file_name in files:
                matched_extension = wanted.get(file_name)
                if matched_extension is None:
                    continue
                full_path = os.path.join(root, file_name)
                if matched_extension in _RASTER_EXTENSIONS:
                    score = _raster_size_score(full_path)
                    if score > raster_candidates[matched_extension][0]:
                        raster_candidates[matched_extension] = (score, full_path)
                elif vector_candidate is None:
                    vector_candidate = full_path

    best_raster_score, best_raster_path = max(raster_candidates.values(), key=lambda item: item[0])

    # A decently sized raster icon is ideal for the button bitmap.
    if best_raster_path is not None and best_raster_score >= _MIN_PREFERRED_RASTER_SIZE:
        return best_raster_path
    if vector_candidate is not None:
        return vector_candidate
    return best_raster_path


def load_application_qicon(icon_name: str) -> QIcon:
    """Resolves a desktop entry Icon value to a QIcon for display in the UI.
    Falls back to Qt's icon theme lookup when no icon file is found directly.
    Returns a null QIcon if nothing could be found."""
    icon_path = find_icon_file(icon_name)
    if icon_path is not None:
        return QIcon(icon_path)
    if icon_name and not os.path.isabs(icon_name):
        return QIcon.fromTheme(icon_name)
    return QIcon()


def _render_qicon_to_png(icon: QIcon, name_hint: str, cache_dir: str, size: int) -> Optional[str]:
    """Renders a QIcon to a PNG file inside ``cache_dir`` and returns its path,
    or ``None`` if the icon could not be rendered."""
    if icon.isNull():
        return None

    pixmap = icon.pixmap(QSize(size, size))
    if pixmap.isNull():
        return None

    os.makedirs(cache_dir, exist_ok=True)
    safe_name = _UNSAFE_FILENAME_RE.sub("_", name_hint) or "app_icon"
    output_path = os.path.join(cache_dir, f"{safe_name}.png")
    if pixmap.save(output_path, "PNG"):
        return output_path
    return None


def resolve_icon_to_file(icon_name: str, cache_dir: str, size: int = 288) -> Optional[str]:
    """Resolves a desktop entry Icon value to an image file that the button
    rendering pipeline can read.

    PNG and SVG icons are returned as their existing file path. XPM icons (which
    the rendering pipeline does not read reliably) are converted to a PNG in
    ``cache_dir``. As a last resort, when only Qt's icon theme can provide the
    icon, it too is rendered to a PNG. Returns the path to a usable image, or
    ``None`` if no icon could be resolved.
    """
    icon_path = find_icon_file(icon_name)
    if icon_path is not None:
        if icon_path.lower().endswith(".xpm"):
            # Pillow's XPM support is unreliable, so render it with Qt instead.
            rendered = _render_qicon_to_png(QIcon(icon_path), icon_name or "app_icon", cache_dir, size)
            return rendered or icon_path
        return icon_path

    # Fallback: the icon may only be reachable through Qt's theme engine (e.g.
    # when it lives in a Qt resource or a non-standard location).
    return _render_qicon_to_png(load_application_qicon(icon_name), icon_name, cache_dir, size)
