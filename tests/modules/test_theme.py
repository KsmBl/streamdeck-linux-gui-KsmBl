from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette

from streamdeck_ui.modules import theme


def _temp_settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_theme_setting_defaults_to_default(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.get_theme(settings) == theme.THEME_DEFAULT


def test_theme_setting_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)

    theme.set_theme(settings, theme.THEME_XP)
    assert theme.get_theme(settings) == theme.THEME_XP

    theme.set_theme(settings, theme.THEME_MODERN)
    assert theme.get_theme(settings) == theme.THEME_MODERN


def test_unknown_theme_falls_back_to_default(tmp_path):
    settings = _temp_settings(tmp_path)
    theme.set_theme(settings, "nonsense")
    assert theme.get_theme(settings) == theme.THEME_DEFAULT


def test_dark_mode_setting_defaults_to_off(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.is_dark_mode_enabled(settings) is False


def test_dark_mode_setting_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)

    theme.set_dark_mode_enabled(settings, True)
    assert theme.is_dark_mode_enabled(settings) is True

    theme.set_dark_mode_enabled(settings, False)
    assert theme.is_dark_mode_enabled(settings) is False


def _reset_default_look(qapp):
    # Reset the cached "default" look and establish a known light palette so the
    # tests do not depend on what other tests may have left on the shared app.
    theme._default_palette = None
    theme._default_style = None
    qapp.setPalette(QPalette(QColor(240, 240, 240)))


def _window_lightness(qapp):
    return qapp.palette().color(QPalette.ColorRole.Window).lightness()


def test_default_theme_light_restores_platform_look(qapp):
    _reset_default_look(qapp)
    # Move away from the default first, then back.
    theme.apply_theme(qapp, theme.THEME_DEFAULT, dark=True)
    theme.apply_theme(qapp, theme.THEME_DEFAULT, dark=False)
    assert qapp.styleSheet() == ""
    assert _window_lightness(qapp) >= 128


def test_default_theme_dark_applies_dark_palette(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_DEFAULT, dark=True)
    assert _window_lightness(qapp) < 128


def test_xp_theme_light_is_luna_beige(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_XP, dark=False)
    window = qapp.palette().color(QPalette.ColorRole.Window)
    assert (window.red(), window.green(), window.blue()) == (236, 233, 216)
    assert "QPushButton" in qapp.styleSheet()


def test_xp_theme_dark_is_dark_with_stylesheet(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_XP, dark=True)
    assert _window_lightness(qapp) < 128
    assert "QPushButton" in qapp.styleSheet()


def test_modern_theme_light_uses_accent(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_MODERN, dark=False)
    window = qapp.palette().color(QPalette.ColorRole.Window)
    assert (window.red(), window.green(), window.blue()) == (247, 248, 250)
    highlight = qapp.palette().color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (79, 70, 229)
    assert "border-radius" in qapp.styleSheet()


def test_modern_theme_dark_is_dark_with_accent(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_MODERN, dark=True)
    assert _window_lightness(qapp) < 128
    highlight = qapp.palette().color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (99, 102, 241)
    assert "border-radius" in qapp.styleSheet()


def test_switching_back_to_default_clears_stylesheet(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_MODERN, dark=False)
    assert qapp.styleSheet() != ""
    theme.apply_theme(qapp, theme.THEME_DEFAULT, dark=False)
    assert qapp.styleSheet() == ""


def test_modern_accent_setting_defaults_and_roundtrip(tmp_path):
    settings = _temp_settings(tmp_path)
    assert theme.get_modern_accent(settings) == theme.DEFAULT_MODERN_ACCENT

    theme.set_modern_accent(settings, "#FF8800")
    assert theme.get_modern_accent(settings) == "#FF8800"

    # An invalid colour is ignored and the previous value is kept.
    theme.set_modern_accent(settings, "not-a-colour")
    assert theme.get_modern_accent(settings) == "#FF8800"


def test_custom_modern_accent_drives_highlight_and_stylesheet(qapp):
    _reset_default_look(qapp)
    theme.apply_theme(qapp, theme.THEME_MODERN, dark=False, modern_accent="#FF8800")
    highlight = qapp.palette().color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (255, 136, 0)
    assert "#FF8800" in qapp.styleSheet()
