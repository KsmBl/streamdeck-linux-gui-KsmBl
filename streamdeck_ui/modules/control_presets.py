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

# Order shown in the menu.
CONTROL_PRESETS: List[ControlPreset] = [_FIREFOX, _VIVALDI, _THUNAR, _VIM, _MEDIA, _GIMP, _DISCORD, _VLC]


def preset_names() -> List[Tuple[str, ControlPreset]]:
    """Returns (name, preset) pairs in menu order."""
    return [(preset.name, preset) for preset in CONTROL_PRESETS]
