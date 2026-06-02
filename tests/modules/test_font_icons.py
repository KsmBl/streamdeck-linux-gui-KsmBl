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


def test_recolor_icon_tints_opaque_pixels(tmp_path):
    # A white square on transparent background.
    src = tmp_path / "white.png"
    image = Image.new("RGBA", (8, 8), (255, 255, 255, 255))
    image.save(src)

    out = font_icons.recolor_icon(str(src), "#ff8800", str(tmp_path / "cache"))
    recolored = Image.open(out).convert("RGBA")
    assert recolored.getpixel((0, 0)) == (255, 136, 0, 255)


def test_recolor_icon_bad_file_returns_original(tmp_path):
    bad = tmp_path / "not-an-image.txt"
    bad.write_text("nope")
    assert font_icons.recolor_icon(str(bad), "#ffffff", str(tmp_path / "cache")) == str(bad)


def test_browser_icon_from_desktop(tmp_path):
    from streamdeck_ui.modules.applications import DesktopApplication

    apps = [DesktopApplication(name="Firefox Web Browser", command="firefox %u", icon_name="firefox")]
    with patch.object(font_icons, "list_desktop_applications", return_value=apps), patch.object(
        font_icons, "find_icon_file", return_value="/themes/firefox.png"
    ):
        assert font_icons._browser_icon_from_desktop("Firefox") == "/themes/firefox.png"
        assert font_icons._browser_icon_from_desktop("Vivaldi") is None


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


def test_in_ranges():
    ranges = ((0x10, 0x20), (0x100, 0x100))
    assert font_icons._in_ranges(0x10, ranges)
    assert font_icons._in_ranges(0x18, ranges)
    assert font_icons._in_ranges(0x100, ranges)
    assert not font_icons._in_ranges(0x21, ranges)
    assert not font_icons._in_ranges(0x99, ranges)


def test_pretty_glyph_name():
    assert font_icons._pretty_glyph_name("arrow-left") == "Arrow Left"
    assert font_icons._pretty_glyph_name("magnifying_glass") == "Magnifying Glass"
    # Opaque uXXXX / uniXXXX names yield an empty string (caller uses a U+ label).
    assert font_icons._pretty_glyph_name("uni0041") == ""
    assert font_icons._pretty_glyph_name("uF04B") == ""


def test_font_codepoint_to_name_reads_real_font():
    # Roboto has a real cmap, so fonttools should map 'A' to a glyph name.
    font_icons._font_reverse_cmap_cache.clear()
    mapping = font_icons._font_codepoint_to_name(ROBOTO)
    assert mapping  # non-empty with fonttools installed
    assert ord("A") in mapping


def test_name_to_codepoint_falls_back_to_presets():
    # A glyph name the (non-FA) Roboto cmap does not contain falls back to the
    # bundled preset code points.
    assert font_icons._name_to_codepoint(ROBOTO, "arrow-left") == font_icons.PRESET_ICON_CODEPOINTS["arrow-left"]
    assert font_icons._name_to_codepoint(ROBOTO, "not-a-real-glyph") is None


def test_render_named_solid_icon_without_font_returns_none():
    with patch.object(font_icons, "find_font_awesome_fonts", return_value={"solid": None, "brands": None}):
        assert font_icons.render_named_solid_icon("arrow-left") is None


def test_render_named_solid_icon_renders(tmp_path):
    # Use Roboto as a stand-in solid font and an ASCII code point that exists.
    with patch.object(
        font_icons, "find_font_awesome_fonts", return_value={"solid": ROBOTO, "brands": None}
    ), patch.dict(font_icons.PRESET_ICON_CODEPOINTS, {"test-glyph": ord("A")}):
        out = font_icons.render_named_solid_icon("test-glyph", str(tmp_path))
    assert out is not None and os.path.isfile(out)


def test_render_all_glyphs_enumerates_font(tmp_path):
    # Enumerate the basic-Latin uppercase letters from Roboto via its cmap.
    icons = font_icons._render_all_glyphs(ROBOTO, ((ord("A"), ord("Z")),), "latin", str(tmp_path))
    assert len(icons) == 26
    names = {name for name, _ in icons}
    assert "A" in names  # Roboto's glyph name for U+0041 is just "A"
    for _, path in icons:
        assert os.path.isfile(path)


def test_find_nerd_fonts_prefers_symbols():
    sample = (
        "/usr/share/fonts/Hack Nerd Font Mono.ttf: Hack Nerd Font Mono:style=Regular\n"
        "/usr/share/fonts/Symbols Nerd Font.ttf: Symbols Nerd Font:style=Regular\n"
        "/usr/share/fonts/DejaVuSans.ttf: DejaVu Sans:style=Book\n"
    )
    with patch("subprocess.run") as run:
        run.return_value.stdout = sample
        assert font_icons.find_nerd_fonts().endswith("Symbols Nerd Font.ttf")


def test_find_nerd_fonts_none_found():
    with patch("subprocess.run") as run:
        run.return_value.stdout = "/usr/share/fonts/DejaVuSans.ttf: DejaVu Sans:style=Book\n"
        assert font_icons.find_nerd_fonts() is None


def test_build_nerd_font_icons_without_font():
    with patch.object(font_icons, "find_nerd_fonts", return_value=None):
        assert font_icons.build_nerd_font_icons("/tmp/sd-nerd-test") == []
