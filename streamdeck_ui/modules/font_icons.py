"""Render icons from an installed icon font (Font Awesome).

This module does not bundle any font or icon artwork. It locates a Font Awesome
font already installed on the user's system (via fontconfig) and renders
individual glyphs to PNG files in the cache directory at runtime, so they can be
used as Stream Deck button images. Only Unicode code points are referenced here.
"""

import os
import subprocess
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from streamdeck_ui.config import FONT_ICON_CACHE_DIR
from streamdeck_ui.modules.applications import find_icon_file

# Curated set of generally useful Font Awesome "Free Solid" glyphs, keyed by a
# display name. The values are Unicode code points in the font's private use
# area (these assignments are stable across Font Awesome releases).
FONT_AWESOME_SOLID: Dict[str, int] = {
    "Play": 0xF04B,
    "Pause": 0xF04C,
    "Stop": 0xF04D,
    "Forward": 0xF04E,
    "Backward": 0xF04A,
    "Volume High": 0xF028,
    "Volume Low": 0xF027,
    "Volume Mute": 0xF6A9,
    "Sun": 0xF185,
    "Moon": 0xF186,
    "House": 0xF015,
    "Lock": 0xF023,
    "Power": 0xF011,
    "Gear": 0xF013,
    "Search": 0xF002,
    "Heart": 0xF004,
    "Star": 0xF005,
    "Bell": 0xF0F3,
    "Envelope": 0xF0E0,
    "Microphone": 0xF130,
    "Camera": 0xF030,
    "Terminal": 0xF120,
    "Folder": 0xF07B,
    "Trash": 0xF1F8,
    "Wifi": 0xF1EB,
    "Music": 0xF001,
    "Image": 0xF03E,
    "Desktop": 0xF108,
    "Keyboard": 0xF11C,
}

# Browser brand glyphs available in the Font Awesome "Brands" font, used as a
# fallback when a real system icon is not installed for the browser.
FONT_AWESOME_BROWSER_BRANDS: Dict[str, int] = {
    "Firefox": 0xF269,
    "Chrome": 0xF268,
    "Edge": 0xF282,
    "Brave": 0xE63C,
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
    # Center using the glyph's bounding box.
    left, top, right, bottom = font.getbbox(glyph)
    x = (size - (right - left)) / 2 - left
    y = (size - (bottom - top)) / 2 - top
    ImageDraw.Draw(image).text((x, y), glyph, font=font, fill=color)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    image.save(out_path, "PNG")
    return out_path


def build_font_awesome_icons(cache_dir: str = FONT_ICON_CACHE_DIR) -> List[Tuple[str, str]]:
    """Renders the curated Font Awesome solid icons to the cache and returns
    ``(display_name, path)`` tuples. Empty if no solid font is installed."""
    fonts = find_font_awesome_fonts()
    solid = fonts["solid"]
    if not solid:
        return []

    icons: List[Tuple[str, str]] = []
    for name, code_point in FONT_AWESOME_SOLID.items():
        out_path = os.path.join(cache_dir, "solid", f"{code_point:04x}.png")
        if os.path.isfile(out_path) or render_glyph(solid, code_point, out_path):
            icons.append((name, out_path))
    return icons


def build_browser_icons(cache_dir: str = FONT_ICON_CACHE_DIR) -> List[Tuple[str, str]]:
    """Returns real browser icons as ``(display_name, path)`` tuples.

    For each browser the installed system theme icon is preferred; if none is
    found, the Font Awesome brand glyph is rendered as a fallback. Browsers for
    which neither source is available are omitted.
    """
    brands = find_font_awesome_fonts()["brands"]
    icons: List[Tuple[str, str]] = []

    for name, theme_names in BROWSER_THEME_NAMES.items():
        path: Optional[str] = None
        for theme_name in theme_names:
            path = find_icon_file(theme_name)
            if path:
                break

        if not path and brands and name in FONT_AWESOME_BROWSER_BRANDS:
            out_path = os.path.join(cache_dir, "brands", f"{name.lower()}.png")
            path = (
                out_path
                if os.path.isfile(out_path)
                else render_glyph(brands, FONT_AWESOME_BROWSER_BRANDS[name], out_path)
            )

        if path:
            icons.append((name, path))

    return icons
