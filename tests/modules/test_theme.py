from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette

from streamdeck_ui.modules import theme


def _temp_settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_dark_mode_setting_defaults_to_off(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.is_dark_mode_enabled(settings) is False


def test_dark_mode_setting_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)

    theme.set_dark_mode_enabled(settings, True)
    assert theme.is_dark_mode_enabled(settings) is True

    theme.set_dark_mode_enabled(settings, False)
    assert theme.is_dark_mode_enabled(settings) is False


def test_apply_theme_switches_palette(qapp):
    # Reset the cached "default" look and establish a known light palette so the
    # test does not depend on what other tests may have left on the shared app.
    theme._default_palette = None
    theme._default_style = None
    qapp.setPalette(QPalette(QColor(240, 240, 240)))

    theme.apply_theme(qapp, True)
    dark_window = qapp.palette().color(QPalette.ColorRole.Window)
    # A dark theme should have a dark window background.
    assert dark_window.lightness() < 128

    theme.apply_theme(qapp, False)
    restored_window = qapp.palette().color(QPalette.ColorRole.Window)
    # Turning dark mode off should restore the light background.
    assert restored_window.lightness() >= 128


def test_xp_theme_setting_defaults_to_off(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.is_xp_theme_enabled(settings) is False


def test_xp_theme_setting_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)

    theme.set_xp_theme_enabled(settings, True)
    assert theme.is_xp_theme_enabled(settings) is True

    theme.set_xp_theme_enabled(settings, False)
    assert theme.is_xp_theme_enabled(settings) is False


def test_apply_xp_theme_sets_luna_look(qapp):
    theme._default_palette = None
    theme._default_style = None
    qapp.setPalette(QPalette(QColor(240, 240, 240)))

    theme.apply_theme(qapp, xp=True)

    window = qapp.palette().color(QPalette.ColorRole.Window)
    # The Luna surface is the signature #ECE9D8 beige.
    assert (window.red(), window.green(), window.blue()) == (236, 233, 216)
    # The XP theme applies a full stylesheet, unlike the palette-only themes.
    assert "QPushButton" in qapp.styleSheet()

    theme.apply_theme(qapp, xp=False)
    # Disabling the theme clears the stylesheet again.
    assert qapp.styleSheet() == ""


def test_modern_theme_setting_defaults_to_off(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.is_modern_theme_enabled(settings) is False


def test_modern_theme_setting_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)

    theme.set_modern_theme_enabled(settings, True)
    assert theme.is_modern_theme_enabled(settings) is True

    theme.set_modern_theme_enabled(settings, False)
    assert theme.is_modern_theme_enabled(settings) is False


def test_apply_modern_theme_sets_sleek_look(qapp):
    theme._default_palette = None
    theme._default_style = None
    qapp.setPalette(QPalette(QColor(240, 240, 240)))

    theme.apply_theme(qapp, modern=True)

    window = qapp.palette().color(QPalette.ColorRole.Window)
    # The modern canvas is the soft off-white #F7F8FA.
    assert (window.red(), window.green(), window.blue()) == (247, 248, 250)
    # The accent drives the selection highlight (#4F46E5 indigo).
    highlight = qapp.palette().color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (79, 70, 229)
    # The modern theme applies a full stylesheet.
    assert "border-radius" in qapp.styleSheet()

    theme.apply_theme(qapp, modern=False)
    assert qapp.styleSheet() == ""
