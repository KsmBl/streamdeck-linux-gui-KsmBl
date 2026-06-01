import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from streamdeck_ui import gui


def _palette_color(role=QPalette.ColorRole.Window):
    return QApplication.instance().palette().color(role)


@pytest.mark.serial
def test_view_menu_theme_actions_present(api_and_window):
    """The View menu exposes the three base-theme actions plus a Dark Mode toggle."""
    main_window, _api = api_and_window
    ui = main_window.ui
    assert ui.menuView.title() == "View"
    assert ui.actionThemeDefault.isCheckable()
    assert ui.actionThemeXP.isCheckable()
    assert ui.actionThemeModern.isCheckable()
    assert ui.actionDarkMode.isCheckable()


@pytest.mark.serial
def test_base_themes_are_mutually_exclusive(api_and_window, mocker):
    """Choosing a base theme unchecks the others (an exclusive choice)."""
    main_window, _api = api_and_window
    mocker.patch.object(gui, "set_theme")
    ui = main_window.ui

    ui.actionThemeXP.trigger()
    assert ui.actionThemeXP.isChecked() is True
    assert ui.actionThemeDefault.isChecked() is False
    assert ui.actionThemeModern.isChecked() is False

    ui.actionThemeModern.trigger()
    assert ui.actionThemeModern.isChecked() is True
    assert ui.actionThemeXP.isChecked() is False


@pytest.mark.serial
def test_select_modern_theme_applies_and_persists(api_and_window, mocker):
    """Selecting the modern theme applies its accent and persists the choice."""
    main_window, _api = api_and_window
    theme_spy = mocker.patch.object(gui, "set_theme")
    # Independent of any accent the user may have persisted in real settings.
    mocker.patch.object(gui, "get_modern_accent", return_value="#4F46E5")

    main_window.ui.actionDarkMode.setChecked(False)
    main_window.ui.actionThemeModern.trigger()

    highlight = _palette_color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (79, 70, 229)
    theme_spy.assert_called_with(main_window.settings, gui.THEME_MODERN)


@pytest.mark.serial
def test_select_xp_theme_applies_luna_beige(api_and_window, mocker):
    """Selecting the Windows XP theme applies the Luna beige surface."""
    main_window, _api = api_and_window
    mocker.patch.object(gui, "set_theme")

    main_window.ui.actionDarkMode.setChecked(False)
    main_window.ui.actionThemeXP.trigger()

    window = _palette_color()
    assert (window.red(), window.green(), window.blue()) == (236, 233, 216)


@pytest.mark.serial
def test_toggle_dark_mode_applies_and_persists(api_and_window, mocker):
    """Toggling Dark Mode over the default theme darkens it and persists."""
    main_window, _api = api_and_window
    mocker.patch.object(gui, "set_theme")
    persist_spy = mocker.patch.object(gui, "set_dark_mode_enabled")

    main_window.ui.actionThemeDefault.trigger()
    main_window.ui.actionDarkMode.setChecked(False)

    main_window.ui.actionDarkMode.setChecked(True)
    assert _palette_color().lightness() < 128
    persist_spy.assert_called_with(main_window.settings, True)

    main_window.ui.actionDarkMode.setChecked(False)
    assert QApplication.instance().styleSheet() == ""
    persist_spy.assert_called_with(main_window.settings, False)


@pytest.mark.serial
def test_dark_mode_layers_over_any_theme(api_and_window, mocker):
    """Dark Mode darkens whichever base theme is selected, keeping its style."""
    main_window, _api = api_and_window
    mocker.patch.object(gui, "set_theme")
    mocker.patch.object(gui, "set_dark_mode_enabled")
    # Use the default accent so the dark variant's built-in accent is asserted,
    # regardless of any accent the user may have persisted in real settings.
    mocker.patch.object(gui, "get_modern_accent", return_value="#4F46E5")

    main_window.ui.actionDarkMode.setChecked(False)
    main_window.ui.actionThemeModern.trigger()
    main_window.ui.actionDarkMode.setChecked(True)

    # The base theme is still selected and its stylesheet still applies...
    assert main_window.ui.actionThemeModern.isChecked() is True
    assert "border-radius" in QApplication.instance().styleSheet()
    # ...but the surface is now dark with the modern dark accent.
    assert _palette_color().lightness() < 128
    highlight = _palette_color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (99, 102, 241)
