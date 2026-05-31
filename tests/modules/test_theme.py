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
