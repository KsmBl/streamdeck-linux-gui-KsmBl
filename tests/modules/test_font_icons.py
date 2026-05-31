import os
from unittest.mock import patch

from PIL import Image

from streamdeck_ui.config import DEFAULT_FONT_FALLBACK_PATH
from streamdeck_ui.modules import font_icons

# A real, always-present font is used to exercise the rendering logic without
# depending on Font Awesome being installed.
ROBOTO = DEFAULT_FONT_FALLBACK_PATH


def test_find_font_awesome_fonts_parses_fclist():
    sample = (
        "/usr/share/fonts/OTF/Font Awesome 7 Free-Solid-900.otf: "
        "Font Awesome 7 Free,Font Awesome 7 Free Solid:style=Solid,Regular\n"
        "/usr/share/fonts/OTF/Font Awesome 7 Brands-Regular-400.otf: Font Awesome 7 Brands:style=Regular\n"
        "/usr/share/fonts/TTF/DejaVuSans.ttf: DejaVu Sans:style=Book\n"
    )
    with patch("subprocess.run") as run:
        run.return_value.stdout = sample
        fonts = font_icons.find_font_awesome_fonts()

    assert fonts["solid"].endswith("Free-Solid-900.otf")
    assert fonts["brands"].endswith("Brands-Regular-400.otf")


def test_find_font_awesome_fonts_none_found():
    with patch("subprocess.run") as run:
        run.return_value.stdout = "/usr/share/fonts/TTF/DejaVuSans.ttf: DejaVu Sans:style=Book\n"
        fonts = font_icons.find_font_awesome_fonts()
    assert fonts == {"solid": None, "brands": None}


def test_render_glyph_renders_existing_character(tmp_path):
    out = str(tmp_path / "a.png")
    result = font_icons.render_glyph(ROBOTO, ord("A"), out, size=128)
    assert result == out
    image = Image.open(out)
    assert image.size == (128, 128)
    assert image.getbbox() is not None  # something was drawn


def test_render_glyph_missing_character_returns_none(tmp_path):
    out = str(tmp_path / "missing.png")
    # A high private-use code point the font does not provide.
    assert font_icons.render_glyph(ROBOTO, 0x10FFFD, out, size=128) is None
    assert not os.path.exists(out)


def test_build_font_awesome_icons_without_font():
    with patch.object(font_icons, "find_font_awesome_fonts", return_value={"solid": None, "brands": None}):
        assert font_icons.build_font_awesome_icons("/tmp/sd-fonticons-test") == []


def test_build_font_awesome_brand_icons_without_font():
    with patch.object(font_icons, "find_font_awesome_fonts", return_value={"solid": None, "brands": None}):
        assert font_icons.build_font_awesome_brand_icons("/tmp/sd-fonticons-test") == []


def test_curated_sets_are_substantial():
    # The "big curated set" should be well over the original handful.
    assert len(font_icons.FONT_AWESOME_SOLID) > 100
    assert len(font_icons.FONT_AWESOME_BRANDS) > 20


def test_build_browser_icons_prefers_system_theme(tmp_path):
    def fake_theme(name):
        return "/themes/firefox.png" if name == "firefox" else None

    with patch.object(font_icons, "find_icon_file", side_effect=fake_theme), patch.object(
        font_icons, "find_font_awesome_fonts", return_value={"solid": None, "brands": None}
    ):
        icons = dict(font_icons.build_browser_icons(str(tmp_path)))

    # Firefox resolved from the system theme; others have neither theme nor font.
    assert icons.get("Firefox") == "/themes/firefox.png"
    assert "Chrome" not in icons
