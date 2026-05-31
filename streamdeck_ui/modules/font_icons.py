"""Render icons from an installed icon font (Font Awesome).

This module does not bundle any font or icon artwork. It locates a Font Awesome
font already installed on the user's system (via fontconfig) and renders
individual glyphs to PNG files in the cache directory at runtime, so they can be
used as Stream Deck button images. Only Unicode code points (factual data) are
referenced here.
"""

import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from streamdeck_ui.config import FONT_ICON_CACHE_DIR
from streamdeck_ui.modules.applications import find_icon_file, list_desktop_applications

# Keywords used to recognise an installed browser from its desktop entry when a
# direct icon-theme name is not found.
BROWSER_DESKTOP_KEYWORDS: Dict[str, List[str]] = {
    "Firefox": ["firefox"],
    "Chrome": ["google-chrome", "chrome"],
    "Chromium": ["chromium"],
    "Edge": ["microsoft-edge", "msedge"],
    "Vivaldi": ["vivaldi"],
    "Brave": ["brave"],
}

# Cache of {glyph name: code point} maps read from font files via fonttools.
_font_cmap_cache: Dict[str, Dict[str, int]] = {}

# Curated set of useful Font Awesome "Free Solid" glyphs, keyed by display name.
# The values are the code points used by the installed font (a mix of Unicode
# and private-use assignments).
FONT_AWESOME_SOLID: Dict[str, int] = {
    "Play": 0xF04B,  # play
    "Pause": 0xF04C,  # pause
    "Stop": 0xF04D,  # stop
    "Forward": 0xF04E,  # forward
    "Backward": 0xF04A,  # backward
    "Forward Step": 0xF051,  # forward-step
    "Backward Step": 0xF048,  # backward-step
    "Forward Fast": 0xF050,  # forward-fast
    "Backward Fast": 0xF049,  # backward-fast
    "Shuffle": 0x1F500,  # shuffle
    "Repeat": 0x1F501,  # repeat
    "Eject": 0xF052,  # eject
    "Circle Play": 0xF144,  # circle-play
    "Circle Pause": 0xF28C,  # circle-pause
    "Expand": 0xF065,  # expand
    "Compress": 0xF066,  # compress
    "Film": 0x1F39E,  # film
    "Clapperboard": 0xE131,  # clapperboard
    "Video": 0xF03D,  # video
    "Camera": 0xF332,  # camera
    "Volume High": 0x1F50A,  # volume-high
    "Volume Low": 0x1F508,  # volume-low
    "Volume Off": 0xF026,  # volume-off
    "Volume Xmark": 0xF6A9,  # volume-xmark
    "Music": 0x1F3B5,  # music
    "Microphone": 0xF130,  # microphone
    "Microphone Slash": 0xF131,  # microphone-slash
    "Headphones": 0x1F3A7,  # headphones
    "Bell": 0x1F514,  # bell
    "Bell Slash": 0x1F515,  # bell-slash
    "Sun": 0xF185,  # sun
    "Moon": 0x1F319,  # moon
    "Lightbulb": 0x1F4A1,  # lightbulb
    "Eye": 0x1F441,  # eye
    "Eye Slash": 0xF070,  # eye-slash
    "Desktop": 0x1F5A5,  # desktop
    "Tv": 0xF8E5,  # tv
    "Mobile Screen": 0xF3CF,  # mobile-screen
    "Laptop": 0x1F4BB,  # laptop
    "Display": 0xE163,  # display
    "Power Off": 0xF011,  # power-off
    "Gear": 0xF013,  # gear
    "Gears": 0xF085,  # gears
    "Sliders": 0xF1DE,  # sliders
    "Plug": 0x1F50C,  # plug
    "Battery Full": 0x1F50B,  # battery-full
    "Battery Half": 0xF242,  # battery-half
    "Battery Empty": 0xF244,  # battery-empty
    "Wifi": 0xF1EB,  # wifi
    "Signal": 0x1F4F6,  # signal
    "Lock": 0x1F512,  # lock
    "Unlock": 0x1F513,  # unlock
    "Key": 0x1F511,  # key
    "Shield Halved": 0xF3ED,  # shield-halved
    "Fingerprint": 0xF577,  # fingerprint
    "Microchip": 0xF2DB,  # microchip
    "Server": 0xF233,  # server
    "Database": 0xF1C0,  # database
    "Hard Drive": 0x1F5B4,  # hard-drive
    "Memory": 0xF538,  # memory
    "Arrow Up": 0xF062,  # arrow-up
    "Arrow Down": 0xF063,  # arrow-down
    "Arrow Left": 0xF060,  # arrow-left
    "Arrow Right": 0xF061,  # arrow-right
    "Arrows Rotate": 0x1F5D8,  # arrows-rotate
    "Rotate Right": 0xF2F9,  # rotate-right
    "Rotate Left": 0xF2EA,  # rotate-left
    "Chevron Up": 0xF077,  # chevron-up
    "Chevron Down": 0xF078,  # chevron-down
    "Chevron Left": 0xF053,  # chevron-left
    "Chevron Right": 0xF054,  # chevron-right
    "House": 0x1F3E0,  # house
    "Bars": 0xF0C9,  # bars
    "Ellipsis": 0xF141,  # ellipsis
    "Ellipsis Vertical": 0xF142,  # ellipsis-vertical
    "Check": 0xF00C,  # check
    "Xmark": 0x1F5D9,  # xmark
    "Plus": 0xF067,  # plus
    "Minus": 0xF068,  # minus
    "Ban": 0x1F6AB,  # ban
    "Trash": 0xF1F8,  # trash
    "Pen": 0x1F58A,  # pen
    "Pencil": 0xF303,  # pencil
    "Copy": 0xF0C5,  # copy
    "Paste": 0xF0EA,  # paste
    "Scissors": 0xF0C4,  # scissors
    "Floppy Disk": 0x1F5AA,  # floppy-disk
    "Download": 0xF019,  # download
    "Upload": 0xF093,  # upload
    "Print": 0x1F5B6,  # print
    "Magnifying Glass": 0x1F50D,  # magnifying-glass
    "Magnifying Glass Plus": 0xF00E,  # magnifying-glass-plus
    "Magnifying Glass Minus": 0xF010,  # magnifying-glass-minus
    "Filter": 0xF0B0,  # filter
    "Folder": 0x1F5BF,  # folder
    "Folder Open": 0x1F5C1,  # folder-open
    "File": 0x1F5CB,  # file
    "File Lines": 0x1F5CE,  # file-lines
    "Image": 0xF03E,  # image
    "Images": 0xF302,  # images
    "Cloud": 0xF0C2,  # cloud
    "Cloud Arrow Up": 0xF382,  # cloud-arrow-up
    "Cloud Arrow Down": 0xF381,  # cloud-arrow-down
    "Envelope": 0x1F582,  # envelope
    "Comment": 0x1F5E9,  # comment
    "Comments": 0x1F5EA,  # comments
    "Phone": 0x1F57B,  # phone
    "Paper Plane": 0xF1D9,  # paper-plane
    "Share": 0xF064,  # share
    "Share Nodes": 0xF1E0,  # share-nodes
    "Link": 0x1F517,  # link
    "At": 0xF1FA,  # at
    "Star": 0xF006,  # star
    "Heart": 0x1F9E1,  # heart
    "Thumbs Up": 0x1F44D,  # thumbs-up
    "Thumbs Down": 0x1F44E,  # thumbs-down
    "Flag": 0x1F3F4,  # flag
    "Bookmark": 0x1F516,  # bookmark
    "Fire": 0x1F525,  # fire
    "Bolt": 0xF0E7,  # bolt
    "Circle": 0x1F7E4,  # circle
    "Square": 0xF0C8,  # square
    "Triangle Exclamation": 0xF071,  # triangle-exclamation
    "Circle Info": 0xF05A,  # circle-info
    "Circle Question": 0xF29C,  # circle-question
    "Circle Check": 0xF05D,  # circle-check
    "Circle Xmark": 0xF05C,  # circle-xmark
    "Clock": 0x1F553,  # clock
    "Calendar": 0x1F4C6,  # calendar
    "Calendar Days": 0xF073,  # calendar-days
    "Location Dot": 0xF3C5,  # location-dot
    "Map": 0x1F5FA,  # map
    "Globe": 0x1F310,  # globe
    "Terminal": 0xF120,  # terminal
    "Code": 0xF121,  # code
    "Keyboard": 0xF11C,  # keyboard
    "Gamepad": 0xF11B,  # gamepad
    "Robot": 0x1F916,  # robot
    "Cube": 0xF1B2,  # cube
    "Palette": 0x1F3A8,  # palette
    "Brush": 0xF55D,  # brush
    "Wrench": 0x1F527,  # wrench
    "Hammer": 0x1F528,  # hammer
    "Screwdriver Wrench": 0xF7D9,  # screwdriver-wrench
    "Gauge High": 0xF625,  # gauge-high
    "Temperature High": 0xF769,  # temperature-high
    "Snowflake": 0xF2DC,  # snowflake
    "Droplet": 0x1F4A7,  # droplet
    "Plane": 0xF072,  # plane
    "Car": 0x1F698,  # car
    "Rocket": 0xF135,  # rocket
    "Mug Hot": 0xF7B6,  # mug-hot
    "Cart Shopping": 0x1F6D2,  # cart-shopping
    "Credit Card": 0x1F4B3,  # credit-card
    "Dollar Sign": 0x1F4B2,  # dollar-sign
    "User": 0x1F464,  # user
    "Users": 0xF0C0,  # users
    "Gauge": 0xF624,  # gauge
    "Tag": 0x1F3F7,  # tag
    "Tags": 0xF02C,  # tags
    "Wand Magic Sparkles": 0xE2CA,  # wand-magic-sparkles
    "Face Smile": 0x1F642,  # face-smile
    "Language": 0xF1AB,  # language
    "Earth Europe": 0xF7A2,  # earth-europe
}

# Curated set of common Font Awesome "Brands" glyphs (logos), keyed by display
# name.
FONT_AWESOME_BRANDS: Dict[str, int] = {
    "Github": 0xF09B,  # github
    "Gitlab": 0xF296,  # gitlab
    "Git Alt": 0xF841,  # git-alt
    "Docker": 0xF395,  # docker
    "Linux": 0xF17C,  # linux
    "Ubuntu": 0xF7DF,  # ubuntu
    "Fedora": 0xF798,  # fedora
    "Windows": 0xF17A,  # windows
    "Apple": 0xF179,  # apple
    "Android": 0xF17B,  # android
    "Python": 0xF3E2,  # python
    "Js": 0xF3B8,  # js
    "Node Js": 0xF3D3,  # node-js
    "React": 0xF41B,  # react
    "Vuejs": 0xF41F,  # vuejs
    "Angular": 0xF420,  # angular
    "Npm": 0xF3D4,  # npm
    "Java": 0xF4E4,  # java
    "Php": 0xF457,  # php
    "Html5": 0xF13B,  # html5
    "Css3": 0xF13C,  # css3
    "Rust": 0xE07A,  # rust
    "Golang": 0xE40F,  # golang
    "Aws": 0xF375,  # aws
    "Google": 0xF1A0,  # google
    "Microsoft": 0xF3CA,  # microsoft
    "Discord": 0xF392,  # discord
    "Slack": 0xF3EF,  # slack
    "Telegram": 0xF3FE,  # telegram
    "Whatsapp": 0xF232,  # whatsapp
    "Spotify": 0xF1BC,  # spotify
    "Youtube": 0xF16A,  # youtube
    "Twitch": 0xF1E8,  # twitch
    "Steam": 0xF1B6,  # steam
    "Raspberry Pi": 0xF7BB,  # raspberry-pi
    "Bluetooth": 0xF293,  # bluetooth
    "Wordpress": 0xF19A,  # wordpress
    "Stack Overflow": 0xF16C,  # stack-overflow
    "Markdown": 0xF60F,  # markdown
}

# Brand glyphs and colours used to render a colourised browser icon when the
# real, installed browser icon is not found in the system theme.
FONT_AWESOME_BROWSER_BRANDS: Dict[str, int] = {
    "Firefox": 0xF269,
    "Chrome": 0xF268,
    "Edge": 0xF282,
    "Brave": 0xE63C,
}
BROWSER_BRAND_COLORS: Dict[str, Tuple[int, int, int, int]] = {
    "Firefox": (255, 113, 57, 255),
    "Chrome": (66, 133, 244, 255),
    "Edge": (15, 143, 224, 255),
    "Brave": (251, 84, 43, 255),
}

# A code point that is not assigned in the Font Awesome fonts. It is used as a
# reference for the font's ".notdef" glyph so missing glyphs (which some fonts
# render as a visible box) can be detected and skipped.
_ABSENT_CODE_POINT = 0x10FFFD

# Browsers offered in the picker, mapped to the icon theme names to try first
# (so the real, installed browser logo is used when available).
BROWSER_THEME_NAMES: Dict[str, List[str]] = {
    "Firefox": ["firefox", "firefox-esr", "org.mozilla.firefox"],
    "Chrome": ["google-chrome", "google-chrome-stable", "chrome"],
    "Chromium": ["chromium", "chromium-browser", "org.chromium.Chromium"],
    "Edge": ["microsoft-edge", "microsoft-edge-stable", "microsoft-edge-dev"],
    "Vivaldi": ["vivaldi", "vivaldi-stable"],
    "Brave": ["brave-browser", "brave", "com.brave.Browser"],
}

_WHITE = (255, 255, 255, 255)


def find_font_awesome_fonts() -> Dict[str, Optional[str]]:
    """Returns the file paths of the installed Font Awesome "solid" and "brands"
    fonts, or ``None`` for each that is not found."""
    fonts: Dict[str, Optional[str]] = {"solid": None, "brands": None}
    try:
        output = subprocess.run(["fc-list"], capture_output=True, text=True, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return fonts

    for line in output.splitlines():
        path = line.split(":", 1)[0].strip()
        if not path or "awesome" not in line.lower():
            continue
        lowered = line.lower()
        if fonts["brands"] is None and "brands" in lowered:
            fonts["brands"] = path
        elif fonts["solid"] is None and "solid" in lowered:
            fonts["solid"] = path

    return fonts


def _font_name_to_codepoint(font_path: str) -> Dict[str, int]:
    """Returns the font's {glyph name: code point} map using fonttools, if it is
    available. Cached per font; empty when fonttools is missing or fails."""
    if font_path in _font_cmap_cache:
        return _font_cmap_cache[font_path]

    mapping: Dict[str, int] = {}
    try:
        from fontTools.ttLib import TTFont  # optional dependency

        mapping = {name: code_point for code_point, name in TTFont(font_path).getBestCmap().items()}
    except Exception:  # noqa: BLE001 - fonttools missing or font unreadable; fall back gracefully
        mapping = {}

    _font_cmap_cache[font_path] = mapping
    return mapping


def _resolve_codepoint(font_path: str, display_name: str, fallback: int) -> int:
    """Resolves a curated icon's code point from the installed font by its Font
    Awesome glyph name (robust across font versions). Falls back to the bundled
    code point when fonttools is unavailable or the name is not present."""
    glyph_name = display_name.lower().replace(" ", "-")
    return _font_name_to_codepoint(font_path).get(glyph_name, fallback)


def recolor_icon(src_path: str, color_hex: str, cache_dir: str = FONT_ICON_CACHE_DIR) -> str:
    """Returns a recoloured copy of a monochrome icon, tinting its opaque pixels
    to ``color_hex`` (e.g. ``#ff8800``). Returns the original path unchanged if
    the image cannot be processed."""
    try:
        image = Image.open(src_path).convert("RGBA")
    except (OSError, ValueError):
        return src_path

    red, green, blue = (int(color_hex[i : i + 2], 16) for i in (1, 3, 5))
    tinted = Image.new("RGBA", image.size, (red, green, blue, 255))
    tinted.putalpha(image.getchannel("A"))
    image = tinted

    out_dir = os.path.join(cache_dir, "recolored")
    os.makedirs(out_dir, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(src_path))
    out_path = os.path.join(out_dir, f"{color_hex[1:]}_{safe}")
    if not out_path.lower().endswith(".png"):
        out_path += ".png"
    image.save(out_path, "PNG")
    return out_path


def _browser_icon_from_desktop(name: str) -> Optional[str]:
    """Finds an installed browser's real icon by matching its desktop entry."""
    keywords = BROWSER_DESKTOP_KEYWORDS.get(name, [])
    if not keywords:
        return None
    for application in list_desktop_applications():
        haystack = f"{application.name} {application.command}".lower()
        if any(keyword in haystack for keyword in keywords):
            icon = find_icon_file(application.icon_name)
            if icon:
                return icon
    return None


def _font_supports(font: "ImageFont.FreeTypeFont", code_point: int) -> bool:
    """True if the font has a real glyph for the code point.

    Handles both fonts whose missing glyph is empty (empty bounding box) and
    fonts that render a visible ".notdef" box (detected by comparing against a
    code point known to be absent)."""
    glyph_mask = font.getmask(chr(code_point))
    if glyph_mask.getbbox() is None:
        return False
    return bytes(glyph_mask) != bytes(font.getmask(chr(_ABSENT_CODE_POINT)))


def render_glyph(
    font_path: str, code_point: int, out_path: str, size: int = 256, color: Tuple[int, int, int, int] = _WHITE
) -> Optional[str]:
    """Renders a single glyph centered on a transparent image and saves it as a
    PNG. Returns ``out_path`` on success, or ``None`` if the font has no glyph
    for the code point."""
    try:
        font = ImageFont.truetype(font_path, int(size * 0.8))
    except OSError:
        return None

    if not _font_supports(font, code_point):
        return None

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph = chr(code_point)
    left, top, right, bottom = font.getbbox(glyph)
    x = (size - (right - left)) / 2 - left
    y = (size - (bottom - top)) / 2 - top
    ImageDraw.Draw(image).text((x, y), glyph, font=font, fill=color)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    image.save(out_path, "PNG")
    return out_path


def _render_catalog(
    font_path: Optional[str], glyphs: Dict[str, int], cache_subdir: str, cache_dir: str
) -> List[Tuple[str, str]]:
    """Renders a catalog of named glyphs to the cache, returning the icons that
    the font actually provides."""
    if not font_path:
        return []
    icons: List[Tuple[str, str]] = []
    for name, fallback_code_point in glyphs.items():
        code_point = _resolve_codepoint(font_path, name, fallback_code_point)
        out_path = os.path.join(cache_dir, cache_subdir, f"{code_point:04x}.png")
        if os.path.isfile(out_path) or render_glyph(font_path, code_point, out_path):
            icons.append((name, out_path))
    return icons


def build_font_awesome_icons(cache_dir: str = FONT_ICON_CACHE_DIR) -> List[Tuple[str, str]]:
    """Renders the curated Font Awesome solid icons. Empty if no solid font is
    installed."""
    return _render_catalog(find_font_awesome_fonts()["solid"], FONT_AWESOME_SOLID, "solid", cache_dir)


def build_font_awesome_brand_icons(cache_dir: str = FONT_ICON_CACHE_DIR) -> List[Tuple[str, str]]:
    """Renders the curated Font Awesome brand icons. Empty if no brands font is
    installed."""
    return _render_catalog(find_font_awesome_fonts()["brands"], FONT_AWESOME_BRANDS, "brands", cache_dir)


def build_browser_icons(cache_dir: str = FONT_ICON_CACHE_DIR) -> List[Tuple[str, str]]:
    """Returns real browser icons as ``(display_name, path)`` tuples.

    For each browser the installed system theme icon (a real, full-colour logo)
    is preferred; if none is found, the Font Awesome brand glyph is rendered in
    the brand's colour as a fallback. Browsers for which neither source is
    available are omitted.
    """
    brands = find_font_awesome_fonts()["brands"]
    icons: List[Tuple[str, str]] = []

    for name, theme_names in BROWSER_THEME_NAMES.items():
        path: Optional[str] = None
        for theme_name in theme_names:
            path = find_icon_file(theme_name)
            if path:
                break

        # Fall back to the icon declared by the browser's desktop entry.
        if not path:
            path = _browser_icon_from_desktop(name)

        if not path and brands and name in FONT_AWESOME_BROWSER_BRANDS:
            out_path = os.path.join(cache_dir, "browsers", f"{name.lower()}.png")
            if os.path.isfile(out_path):
                path = out_path
            else:
                path = render_glyph(
                    brands,
                    FONT_AWESOME_BROWSER_BRANDS[name],
                    out_path,
                    color=BROWSER_BRAND_COLORS.get(name, _WHITE),
                )

        if path:
            icons.append((name, path))

    return icons
