import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from streamdeck_ui import gui


@pytest.mark.serial
def test_dark_mode_action_present(api_and_window):
    """The View menu exposes a checkable Dark Mode action."""
    main_window, _api = api_and_window
    assert main_window.ui.menuView.title() == "View"
    assert main_window.ui.actionDarkMode.isCheckable()


@pytest.mark.serial
def test_toggle_dark_mode_applies_and_persists(api_and_window, mocker):
    """Toggling the action applies a dark palette and persists the preference."""
    main_window, _api = api_and_window

    # Avoid writing to the real user QSettings during the test.
    persist_spy = mocker.patch.object(gui, "set_dark_mode_enabled")

    # Establish a deterministic baseline (the saved preference may start it on).
    main_window.ui.actionDarkMode.setChecked(False)

    main_window.ui.actionDarkMode.setChecked(True)
    dark_window = QApplication.instance().palette().color(QPalette.ColorRole.Window)
    assert dark_window.lightness() < 128
    persist_spy.assert_called_with(main_window.settings, True)

    main_window.ui.actionDarkMode.setChecked(False)
    persist_spy.assert_called_with(main_window.settings, False)


@pytest.mark.serial
def test_xp_theme_action_present(api_and_window):
    """The View menu exposes a checkable Windows XP theme action."""
    main_window, _api = api_and_window
    assert main_window.ui.actionXPTheme.isCheckable()


@pytest.mark.serial
def test_modern_theme_action_present(api_and_window):
    """The View menu exposes a checkable modern theme action."""
    main_window, _api = api_and_window
    assert main_window.ui.actionModernTheme.isCheckable()


@pytest.mark.serial
def test_modern_theme_excludes_other_themes(api_and_window, mocker):
    """Enabling the modern theme applies its look and turns the others off."""
    main_window, _api = api_and_window

    mocker.patch.object(gui, "set_dark_mode_enabled")
    mocker.patch.object(gui, "set_xp_theme_enabled")
    mocker.patch.object(gui, "set_modern_theme_enabled")

    main_window.ui.actionModernTheme.setChecked(False)
    main_window.ui.actionXPTheme.setChecked(False)
    main_window.ui.actionDarkMode.setChecked(True)

    main_window.ui.actionModernTheme.setChecked(True)
    assert main_window.ui.actionDarkMode.isChecked() is False
    assert main_window.ui.actionXPTheme.isChecked() is False

    highlight = QApplication.instance().palette().color(QPalette.ColorRole.Highlight)
    assert (highlight.red(), highlight.green(), highlight.blue()) == (79, 70, 229)

    main_window.ui.actionModernTheme.setChecked(False)
    assert QApplication.instance().styleSheet() == ""


@pytest.mark.serial
def test_xp_theme_and_dark_mode_are_mutually_exclusive(api_and_window, mocker):
    """Enabling one theme turns the other off and applies the right look."""
    main_window, _api = api_and_window

    mocker.patch.object(gui, "set_dark_mode_enabled")
    mocker.patch.object(gui, "set_xp_theme_enabled")

    main_window.ui.actionDarkMode.setChecked(False)
    main_window.ui.actionXPTheme.setChecked(False)

    # Turn on dark mode, then the XP theme: dark mode must switch off.
    main_window.ui.actionDarkMode.setChecked(True)
    main_window.ui.actionXPTheme.setChecked(True)
    assert main_window.ui.actionDarkMode.isChecked() is False

    window = QApplication.instance().palette().color(QPalette.ColorRole.Window)
    assert (window.red(), window.green(), window.blue()) == (236, 233, 216)

    # Turning the XP theme back off restores the default look.
    main_window.ui.actionXPTheme.setChecked(False)
    assert QApplication.instance().styleSheet() == ""
