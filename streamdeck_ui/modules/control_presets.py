"""Ready-made *control surfaces* for popular applications.

A control preset is a whole page of keys that drive an application via its
keyboard shortcuts (and, for media players, the global multimedia keys). Picking
one fills the current page with labelled keys — New Tab, Back, Reload, Save, … —
so a deck can become a remote for Firefox, Vivaldi, Thunar, Vim or a music
player in a single click.

The shortcuts are sent with the same *Press Keys* mechanism as a hand-made key,
using the key-combo syntax understood by :mod:`streamdeck_ui.modules.keyboard`
(sections separated by ``,`` are pressed in sequence, keys joined by ``+`` are
pressed together). Application shortcuts only take effect while that application
is focused; the global media keys work regardless of focus.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class ControlAction:
    """A single key on a control surface."""

    text: str
    "The label rendered on the key."

    keys: str = ""
    "Press-Keys combo string sent when the key is pressed."

    write: str = ""
    "Literal text typed when the key is pressed (rarely needed)."

    command: str = ""
    "Shell command run when the key is pressed (rarely needed)."

    icon: str = ""
    "Font Awesome solid glyph name (e.g. ``arrow-left``) shown on the key."


@dataclass(frozen=True)
class ControlPreset:
    """A named collection of control keys to lay out on a page."""

    name: str
    actions: List[ControlAction] = field(default_factory=list)

    app: str = ""
    "Window class / app id this surface controls, used to auto-bind an Auto page."


# Most browsers share the same editing/navigation shortcuts; the small
# differences (private window, downloads, reload) are spelled out per browser.
_FIREFOX = ControlPreset(
    "Firefox",
    [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Reopen\nTab", "ctrl+shift+t", icon="rotate-left"),
        ControlAction("Next\nTab", "ctrl+tab", icon="chevron-right"),
        ControlAction("Prev\nTab", "ctrl+shift+tab", icon="chevron-left"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Reload", "f5", icon="arrows-rotate"),
        ControlAction("Address\nBar", "ctrl+l", icon="globe"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Private\nWindow", "ctrl+shift+p", icon="user-secret"),
        ControlAction("Bookmark", "ctrl+d", icon="bookmark"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="firefox",
)

_VIVALDI = ControlPreset(
    "Vivaldi",
    [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Reopen\nTab", "ctrl+shift+t", icon="rotate-left"),
        ControlAction("Next\nTab", "ctrl+tab", icon="chevron-right"),
        ControlAction("Prev\nTab", "ctrl+shift+tab", icon="chevron-left"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Reload", "ctrl+r", icon="arrows-rotate"),
        ControlAction("Address\nBar", "ctrl+l", icon="globe"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Private\nWindow", "ctrl+shift+n", icon="user-secret"),
        ControlAction("Downloads", "ctrl+j", icon="download"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="vivaldi",
)

_THUNAR = ControlPreset(
    "Thunar (files)",
    [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Up", "alt+up", icon="arrow-up"),
        ControlAction("Home", "alt+home", icon="house"),
        ControlAction("Reload", "ctrl+r", icon="arrows-rotate"),
        ControlAction("New\nFolder", "ctrl+shift+n", icon="folder-plus"),
        ControlAction("Rename", "f2", icon="pen"),
        ControlAction("Delete", "delete", icon="trash"),
        ControlAction("Select\nAll", "ctrl+a", icon="check-double"),
        ControlAction("Hidden\nFiles", "ctrl+h", icon="eye"),
        ControlAction("Props", "alt+enter", icon="circle-info"),
    ],
    app="thunar",
)

# Vim is modal: each action first presses Esc to return to normal mode, then
# enters the relevant command. ":" is Shift+; on a US layout.
_VIM = ControlPreset(
    "Vim",
    [
        ControlAction("Save\n:w", "esc,shift+semicolon,w,enter", icon="floppy-disk"),
        ControlAction("Save &\nQuit", "esc,shift+semicolon,w,q,enter", icon="right-from-bracket"),
        ControlAction("Quit!\n:q!", "esc,shift+semicolon,q,shift+1,enter", icon="power-off"),
        ControlAction("Undo", "esc,u", icon="rotate-left"),
        ControlAction("Redo", "esc,ctrl+r", icon="rotate-right"),
        ControlAction("Copy\nLine", "esc,y,y", icon="copy"),
        ControlAction("Paste", "esc,p", icon="paste"),
        ControlAction("Delete\nLine", "esc,d,d", icon="trash"),
        ControlAction("Search", "esc,/", icon="magnifying-glass"),
        ControlAction("Top", "esc,g,g", icon="angles-up"),
        ControlAction("Bottom", "esc,shift+g", icon="angles-down"),
        ControlAction("Visual", "esc,v", icon="i-cursor"),
        ControlAction("Select\nAll", "esc,g,g,shift+v,shift+g", icon="check-double"),
        ControlAction("Save\nAll", "esc,shift+semicolon,w,a,enter", icon="floppy-disk"),
    ],
    app="gvim",
)

# Multimedia keys are global and work no matter which application is focused.
_MEDIA = ControlPreset(
    "Media player",
    [
        ControlAction("Play /\nPause", "playpause", icon="play"),
        ControlAction("Prev", "previoussong", icon="backward-step"),
        ControlAction("Next", "nextsong", icon="forward-step"),
        ControlAction("Stop", "stopcd", icon="stop"),
        ControlAction("Vol +", "volumeup", icon="volume-high"),
        ControlAction("Vol -", "volumedown", icon="volume-low"),
        ControlAction("Mute", "mute", icon="volume-xmark"),
    ],
    app="spotify",
)

_GIMP = ControlPreset(
    "GIMP",
    [
        ControlAction("New", "ctrl+n", icon="plus"),
        ControlAction("Open", "ctrl+o", icon="folder-open"),
        ControlAction("Save", "shift+ctrl+s", icon="floppy-disk"),
        ControlAction("Export", "shift+ctrl+e", icon="file-export"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+y", icon="rotate-right"),
        ControlAction("Copy", "ctrl+c", icon="copy"),
        ControlAction("Paste", "ctrl+v", icon="paste"),
        ControlAction("Brush", "p", icon="paintbrush"),
        ControlAction("Pencil", "n", icon="pen"),
        ControlAction("Eraser", "shift+e", icon="eraser"),
        ControlAction("Bucket\nFill", "shift+b", icon="fill-drip"),
        ControlAction("Crop", "shift+c", icon="crop-simple"),
        ControlAction("Fit\nImage", "shift+ctrl+j", icon="expand"),
    ],
    app="gimp",
)

_DISCORD = ControlPreset(
    "Discord",
    [
        ControlAction("Quick\nSwitch", "ctrl+k", icon="magnifying-glass"),
        ControlAction("Mute\nMic", "ctrl+shift+m", icon="microphone-slash"),
        ControlAction("Deafen", "ctrl+shift+d", icon="headphones"),
        ControlAction("Prev\nChannel", "alt+up", icon="chevron-up"),
        ControlAction("Next\nChannel", "alt+down", icon="chevron-down"),
        ControlAction("Prev\nServer", "ctrl+alt+up", icon="angles-up"),
        ControlAction("Next\nServer", "ctrl+alt+down", icon="angles-down"),
        ControlAction("Mark\nRead", "shift+esc", icon="check-double"),
        ControlAction("Answer", "ctrl+enter", icon="phone"),
        ControlAction("Close", "esc", icon="xmark"),
    ],
    app="discord",
)

_VLC = ControlPreset(
    "VLC",
    [
        ControlAction("Play /\nPause", "space", icon="play"),
        ControlAction("Stop", "s", icon="stop"),
        ControlAction("Prev", "p", icon="backward-step"),
        ControlAction("Next", "n", icon="forward-step"),
        ControlAction("Jump\nBack", "alt+left", icon="backward"),
        ControlAction("Jump\nFwd", "alt+right", icon="forward"),
        ControlAction("Vol +", "ctrl+up", icon="volume-high"),
        ControlAction("Vol -", "ctrl+down", icon="volume-low"),
        ControlAction("Mute", "m", icon="volume-xmark"),
        ControlAction("Full\nScreen", "f", icon="expand"),
        ControlAction("Subtitle", "v", icon="closed-captioning"),
        ControlAction("Snapshot", "shift+s", icon="camera"),
        ControlAction("Loop", "l", icon="repeat"),
        ControlAction("Random", "r", icon="shuffle"),
    ],
    app="vlc",
)

_XFCE_TERMINAL = ControlPreset(
    "Xfce Terminal",
    [
        ControlAction("New\nTab", "ctrl+shift+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+shift+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+shift+w", icon="xmark"),
        ControlAction("Copy", "ctrl+shift+c", icon="copy"),
        ControlAction("Paste", "ctrl+shift+v", icon="paste"),
        ControlAction("Prev\nTab", "ctrl+pageup", icon="chevron-left"),
        ControlAction("Next\nTab", "ctrl+pagedown", icon="chevron-right"),
        ControlAction("Find", "ctrl+shift+f", icon="magnifying-glass"),
        ControlAction("Zoom\nIn", "ctrl+plus", icon="magnifying-glass-plus"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="xfce4-terminal",
)

_KONSOLE = ControlPreset(
    "Konsole",
    [
        ControlAction("New\nTab", "ctrl+shift+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+shift+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+shift+w", icon="xmark"),
        ControlAction("Copy", "ctrl+shift+c", icon="copy"),
        ControlAction("Paste", "ctrl+shift+v", icon="paste"),
        ControlAction("Prev\nTab", "shift+left", icon="chevron-left"),
        ControlAction("Next\nTab", "shift+right", icon="chevron-right"),
        ControlAction("Find", "ctrl+shift+f", icon="magnifying-glass"),
        ControlAction("Clear", "ctrl+shift+k", icon="eraser"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="konsole",
)

_DOLPHIN = ControlPreset(
    "Dolphin (files)",
    [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Up", "alt+up", icon="arrow-up"),
        ControlAction("Home", "alt+home", icon="house"),
        ControlAction("Reload", "f5", icon="arrows-rotate"),
        ControlAction("New\nFolder", "f10", icon="folder-plus"),
        ControlAction("Rename", "f2", icon="pen"),
        ControlAction("Delete", "delete", icon="trash"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Select\nAll", "ctrl+a", icon="check-double"),
        ControlAction("Hidden\nFiles", "ctrl+h", icon="eye"),
    ],
    app="dolphin",
)

# TETR.IO desktop: the default in-game controls, driven from the deck.
_TETRIO = ControlPreset(
    "TETR.IO",
    [
        ControlAction("Left", "left", icon="arrow-left"),
        ControlAction("Right", "right", icon="arrow-right"),
        ControlAction("Soft\nDrop", "down", icon="arrow-down"),
        ControlAction("Hard\nDrop", "space", icon="angles-down"),
        ControlAction("Rotate\nCW", "up", icon="rotate-right"),
        ControlAction("Rotate\nCCW", "z", icon="rotate-left"),
        ControlAction("Rotate\n180", "a", icon="arrows-rotate"),
        ControlAction("Hold", "c", icon="box-archive"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="tetrio-desktop",
)

_THUNDERBIRD = ControlPreset(
    "Thunderbird",
    [
        ControlAction("Write", "ctrl+n", icon="pen-to-square"),
        ControlAction("Reply", "ctrl+r", icon="reply"),
        ControlAction("Reply\nAll", "ctrl+shift+r", icon="reply-all"),
        ControlAction("Forward", "ctrl+l", icon="share"),
        ControlAction("Send", "ctrl+enter", icon="paper-plane"),
        ControlAction("Get\nMail", "f5", icon="arrows-rotate"),
        ControlAction("Archive", "a", icon="box-archive"),
        ControlAction("Delete", "delete", icon="trash"),
        ControlAction("Junk", "j", icon="ban"),
        ControlAction("Mark\nRead", "m", icon="envelope"),
        ControlAction("Contacts", "ctrl+shift+b", icon="users"),
        ControlAction("Search", "ctrl+k", icon="magnifying-glass"),
    ],
    app="thunderbird",
)

_GITTYUP = ControlPreset(
    "Gittyup",
    [
        ControlAction("Refresh", "ctrl+r", icon="arrows-rotate"),
        ControlAction("Commit", "ctrl+enter", icon="check"),
        ControlAction("Stage\nAll", "ctrl+shift+a", icon="check-double"),
        ControlAction("Push", "ctrl+shift+p", icon="cloud-arrow-up"),
        ControlAction("Fetch", "ctrl+shift+f", icon="cloud-arrow-down"),
        ControlAction("Pull", "ctrl+shift+l", icon="download"),
        ControlAction("New\nBranch", "ctrl+shift+b", icon="code-branch"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+shift+z", icon="rotate-right"),
    ],
    app="gittyup",
)


def _browser_actions(reload: str, private: str, downloads: str) -> List[ControlAction]:
    """The shared browser control surface; the few differing shortcuts (reload,
    private window, downloads) are passed in per browser."""
    return [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Reopen\nTab", "ctrl+shift+t", icon="rotate-left"),
        ControlAction("Next\nTab", "ctrl+tab", icon="chevron-right"),
        ControlAction("Prev\nTab", "ctrl+shift+tab", icon="chevron-left"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Reload", reload, icon="arrows-rotate"),
        ControlAction("Address\nBar", "ctrl+l", icon="globe"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Private\nWindow", private, icon="user-secret"),
        ControlAction("Downloads", downloads, icon="download"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ]


def _file_manager_actions() -> List[ControlAction]:
    """The shared file-manager control surface (GNOME/GTK shortcut style)."""
    return [
        ControlAction("New\nTab", "ctrl+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+w", icon="xmark"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Up", "alt+up", icon="arrow-up"),
        ControlAction("Home", "alt+home", icon="house"),
        ControlAction("Reload", "f5", icon="arrows-rotate"),
        ControlAction("New\nFolder", "ctrl+shift+n", icon="folder-plus"),
        ControlAction("Rename", "f2", icon="pen"),
        ControlAction("Delete", "delete", icon="trash"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Select\nAll", "ctrl+a", icon="check-double"),
        ControlAction("Hidden\nFiles", "ctrl+h", icon="eye"),
    ]


def _terminal_actions() -> List[ControlAction]:
    """The shared terminal control surface (GNOME/kitty shortcut style)."""
    return [
        ControlAction("New\nTab", "ctrl+shift+t", icon="plus"),
        ControlAction("New\nWindow", "ctrl+shift+n", icon="window-restore"),
        ControlAction("Close\nTab", "ctrl+shift+w", icon="xmark"),
        ControlAction("Copy", "ctrl+shift+c", icon="copy"),
        ControlAction("Paste", "ctrl+shift+v", icon="paste"),
        ControlAction("Prev\nTab", "ctrl+pageup", icon="chevron-left"),
        ControlAction("Next\nTab", "ctrl+pagedown", icon="chevron-right"),
        ControlAction("Find", "ctrl+shift+f", icon="magnifying-glass"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ]


_CHROMIUM = ControlPreset("Chromium", _browser_actions("ctrl+r", "ctrl+shift+n", "ctrl+j"), app="chromium")
_CHROME = ControlPreset("Chrome", _browser_actions("ctrl+r", "ctrl+shift+n", "ctrl+j"), app="google-chrome")
_BRAVE = ControlPreset("Brave", _browser_actions("ctrl+r", "ctrl+shift+n", "ctrl+j"), app="brave-browser")
_LIBREWOLF = ControlPreset("LibreWolf", _browser_actions("f5", "ctrl+shift+p", "ctrl+shift+y"), app="librewolf")
_ZEN = ControlPreset("Zen Browser", _browser_actions("f5", "ctrl+shift+p", "ctrl+shift+y"), app="zen")

_NAUTILUS = ControlPreset("Files (Nautilus)", _file_manager_actions(), app="org.gnome.nautilus")
_NEMO = ControlPreset("Nemo (files)", _file_manager_actions(), app="nemo")
_PCMANFM = ControlPreset("PCManFM (files)", _file_manager_actions(), app="pcmanfm")

_GNOME_TERMINAL = ControlPreset("GNOME Terminal", _terminal_actions(), app="gnome-terminal")
_KITTY = ControlPreset("kitty", _terminal_actions(), app="kitty")

_VSCODE = ControlPreset(
    "VS Code",
    [
        ControlAction("Command\nPalette", "ctrl+shift+p", icon="bars"),
        ControlAction("Quick\nOpen", "ctrl+p", icon="magnifying-glass"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Replace", "ctrl+h", icon="pen-to-square"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("New\nFile", "ctrl+n", icon="file"),
        ControlAction("Sidebar", "ctrl+b", icon="bars"),
        ControlAction("Search", "ctrl+shift+f", icon="magnifying-glass"),
        ControlAction("Source\nControl", "ctrl+shift+g", icon="code-branch"),
        ControlAction("Terminal", "ctrl+j", icon="terminal"),
        ControlAction("Go to\nLine", "ctrl+g", icon="arrow-right"),
        ControlAction("Format", "shift+alt+f", icon="wand-magic-sparkles"),
    ],
    app="code",
)

_SUBLIME = ControlPreset(
    "Sublime Text",
    [
        ControlAction("Command\nPalette", "ctrl+shift+p", icon="bars"),
        ControlAction("Goto\nAnything", "ctrl+p", icon="magnifying-glass"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Replace", "ctrl+h", icon="pen-to-square"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("New\nFile", "ctrl+n", icon="file"),
        ControlAction("Goto\nLine", "ctrl+g", icon="arrow-right"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+shift+z", icon="rotate-right"),
    ],
    app="sublime_text",
)

_OBSIDIAN = ControlPreset(
    "Obsidian",
    [
        ControlAction("Command\nPalette", "ctrl+p", icon="bars"),
        ControlAction("Quick\nSwitch", "ctrl+o", icon="magnifying-glass"),
        ControlAction("Search", "ctrl+shift+f", icon="magnifying-glass"),
        ControlAction("New\nNote", "ctrl+n", icon="file"),
        ControlAction("Bold", "ctrl+b", icon="bold"),
        ControlAction("Italic", "ctrl+i", icon="italic"),
        ControlAction("Insert\nLink", "ctrl+k", icon="link"),
        ControlAction("Edit /\nPreview", "ctrl+e", icon="pen-to-square"),
        ControlAction("Graph", "ctrl+g", icon="share"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
    ],
    app="obsidian",
)

_KRITA = ControlPreset(
    "Krita",
    [
        ControlAction("New", "ctrl+n", icon="file"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+shift+z", icon="rotate-right"),
        ControlAction("Brush", "b", icon="paintbrush"),
        ControlAction("Eraser", "e", icon="eraser"),
        ControlAction("Gradient", "g", icon="fill-drip"),
        ControlAction("Line", "v", icon="pen"),
        ControlAction("Transform", "ctrl+t", icon="crop-simple"),
        ControlAction("Mirror\nView", "m", icon="image"),
    ],
    app="krita",
)

_INKSCAPE = ControlPreset(
    "Inkscape",
    [
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+shift+z", icon="rotate-right"),
        ControlAction("Select", "s", icon="i-cursor"),
        ControlAction("Pen", "b", icon="pen"),
        ControlAction("Text", "t", icon="pen-to-square"),
        ControlAction("Duplicate", "ctrl+d", icon="copy"),
        ControlAction("Group", "ctrl+g", icon="bars"),
        ControlAction("Fill &\nStroke", "ctrl+shift+f", icon="palette"),
        ControlAction("Export", "ctrl+shift+e", icon="file-export"),
    ],
    app="inkscape",
)

_BLENDER = ControlPreset(
    "Blender",
    [
        ControlAction("Grab", "g", icon="arrow-right"),
        ControlAction("Rotate", "r", icon="rotate-right"),
        ControlAction("Scale", "s", icon="expand"),
        ControlAction("Extrude", "e", icon="plus"),
        ControlAction("Delete", "x", icon="trash"),
        ControlAction("Add", "shift+a", icon="plus"),
        ControlAction("Edit\nMode", "tab", icon="pen"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Render", "f12", icon="image"),
    ],
    app="blender",
)

_KDENLIVE = ControlPreset(
    "Kdenlive",
    [
        ControlAction("Play /\nPause", "space", icon="play"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+shift+z", icon="rotate-right"),
        ControlAction("Set In", "i", icon="chevron-left"),
        ControlAction("Set Out", "o", icon="chevron-right"),
        ControlAction("Delete", "delete", icon="trash"),
        ControlAction("Render", "ctrl+enter", icon="film"),
        ControlAction("Full\nScreen", "f11", icon="expand"),
    ],
    app="org.kde.kdenlive",
)

_OKULAR = ControlPreset(
    "Okular (PDF)",
    [
        ControlAction("Prev\nPage", "pageup", icon="chevron-left"),
        ControlAction("Next\nPage", "pagedown", icon="chevron-right"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Zoom\nIn", "ctrl+plus", icon="magnifying-glass-plus"),
        ControlAction("Zoom\nOut", "ctrl+minus", icon="magnifying-glass"),
        ControlAction("Open", "ctrl+o", icon="folder-open"),
        ControlAction("Go to\nPage", "ctrl+g", icon="arrow-right"),
        ControlAction("Present", "ctrl+shift+p", icon="expand"),
        ControlAction("Print", "ctrl+p", icon="print"),
    ],
    app="org.kde.okular",
)

_ZATHURA = ControlPreset(
    "Zathura (PDF)",
    [
        ControlAction("Down", "j", icon="arrow-down"),
        ControlAction("Up", "k", icon="arrow-up"),
        ControlAction("Next\nPage", "space", icon="chevron-right"),
        ControlAction("Open", "o", icon="folder-open"),
        ControlAction("Index", "tab", icon="list-ul"),
        ControlAction("Rotate", "r", icon="rotate-right"),
        ControlAction("Zoom\nIn", "plus", icon="magnifying-glass-plus"),
        ControlAction("Zoom\nOut", "minus", icon="magnifying-glass"),
        ControlAction("Recolor", "ctrl+r", icon="palette"),
        ControlAction("Full\nScreen", "f", icon="expand"),
    ],
    app="zathura",
)

_LIBRE_WRITER = ControlPreset(
    "LibreOffice Writer",
    [
        ControlAction("New", "ctrl+n", icon="file"),
        ControlAction("Open", "ctrl+o", icon="folder-open"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Print", "ctrl+p", icon="print"),
        ControlAction("Bold", "ctrl+b", icon="bold"),
        ControlAction("Italic", "ctrl+i", icon="italic"),
        ControlAction("Underline", "ctrl+u", icon="underline"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+y", icon="rotate-right"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
    ],
    app="libreoffice-writer",
)

_LIBRE_CALC = ControlPreset(
    "LibreOffice Calc",
    [
        ControlAction("New", "ctrl+n", icon="file"),
        ControlAction("Save", "ctrl+s", icon="floppy-disk"),
        ControlAction("Print", "ctrl+p", icon="print"),
        ControlAction("Bold", "ctrl+b", icon="bold"),
        ControlAction("Sum", "alt+plus", icon="table"),
        ControlAction("Find", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Undo", "ctrl+z", icon="rotate-left"),
        ControlAction("Redo", "ctrl+y", icon="rotate-right"),
    ],
    app="libreoffice-calc",
)

_SPOTIFY = ControlPreset(
    "Spotify",
    [
        ControlAction("Play /\nPause", "space", icon="play"),
        ControlAction("Next", "ctrl+right", icon="forward-step"),
        ControlAction("Prev", "ctrl+left", icon="backward-step"),
        ControlAction("Vol +", "ctrl+up", icon="volume-high"),
        ControlAction("Vol -", "ctrl+down", icon="volume-low"),
        ControlAction("Search", "ctrl+l", icon="magnifying-glass"),
        ControlAction("Repeat", "ctrl+r", icon="repeat"),
        ControlAction("Shuffle", "ctrl+s", icon="shuffle"),
    ],
    app="spotify",
)

_MPV = ControlPreset(
    "mpv",
    [
        ControlAction("Play /\nPause", "space", icon="play"),
        ControlAction("Seek +", "right", icon="forward"),
        ControlAction("Seek -", "left", icon="backward"),
        ControlAction("Vol +", "up", icon="volume-high"),
        ControlAction("Vol -", "down", icon="volume-low"),
        ControlAction("Mute", "m", icon="volume-xmark"),
        ControlAction("Subtitle", "v", icon="closed-captioning"),
        ControlAction("Full\nScreen", "f", icon="expand"),
    ],
    app="mpv",
)

_AUDACIOUS = ControlPreset(
    "Audacious",
    [
        ControlAction("Play", "ctrl+enter", icon="play"),
        ControlAction("Stop", "v", icon="stop"),
        ControlAction("Prev", "z", icon="backward-step"),
        ControlAction("Next", "b", icon="forward-step"),
        ControlAction("Vol +", "up", icon="volume-high"),
        ControlAction("Vol -", "down", icon="volume-low"),
    ],
    app="audacious",
)

_SLACK = ControlPreset(
    "Slack",
    [
        ControlAction("Quick\nSwitch", "ctrl+k", icon="magnifying-glass"),
        ControlAction("Search", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Unreads", "ctrl+shift+a", icon="envelope"),
        ControlAction("Threads", "ctrl+shift+t", icon="comments"),
        ControlAction("DMs", "ctrl+shift+k", icon="comments"),
        ControlAction("Prev\nChannel", "alt+up", icon="chevron-up"),
        ControlAction("Next\nChannel", "alt+down", icon="chevron-down"),
        ControlAction("Back", "alt+left", icon="arrow-left"),
        ControlAction("Fwd", "alt+right", icon="arrow-right"),
        ControlAction("Mark\nRead", "esc", icon="check-double"),
    ],
    app="slack",
)

_TELEGRAM = ControlPreset(
    "Telegram",
    [
        ControlAction("Search", "ctrl+f", icon="magnifying-glass"),
        ControlAction("Next\nChat", "ctrl+tab", icon="chevron-down"),
        ControlAction("Prev\nChat", "ctrl+shift+tab", icon="chevron-up"),
        ControlAction("Back", "esc", icon="arrow-left"),
    ],
    app="telegram-desktop",
)

_ELEMENT = ControlPreset(
    "Element",
    [
        ControlAction("Search", "ctrl+k", icon="magnifying-glass"),
        ControlAction("Prev\nRoom", "alt+up", icon="chevron-up"),
        ControlAction("Next\nRoom", "alt+down", icon="chevron-down"),
        ControlAction("Prev\nUnread", "alt+shift+up", icon="envelope"),
        ControlAction("Next\nUnread", "alt+shift+down", icon="envelope"),
    ],
    app="element",
)

# Order shown in the menu.
CONTROL_PRESETS: List[ControlPreset] = [
    # Browsers
    _FIREFOX,
    _VIVALDI,
    _CHROMIUM,
    _CHROME,
    _BRAVE,
    _LIBREWOLF,
    _ZEN,
    # File managers
    _THUNAR,
    _DOLPHIN,
    _NAUTILUS,
    _NEMO,
    _PCMANFM,
    # Terminals
    _XFCE_TERMINAL,
    _KONSOLE,
    _GNOME_TERMINAL,
    _KITTY,
    # Editors / IDEs
    _VIM,
    _VSCODE,
    _SUBLIME,
    _OBSIDIAN,
    _GITTYUP,
    # Creative
    _GIMP,
    _KRITA,
    _INKSCAPE,
    _BLENDER,
    _KDENLIVE,
    # Documents
    _LIBRE_WRITER,
    _LIBRE_CALC,
    _OKULAR,
    _ZATHURA,
    # Communication
    _DISCORD,
    _SLACK,
    _TELEGRAM,
    _ELEMENT,
    _THUNDERBIRD,
    # Media
    _VLC,
    _SPOTIFY,
    _MPV,
    _AUDACIOUS,
    _MEDIA,
    # Games
    _TETRIO,
]


def preset_names() -> List[Tuple[str, ControlPreset]]:
    """Returns (name, preset) pairs in menu order."""
    return [(preset.name, preset) for preset in CONTROL_PRESETS]
