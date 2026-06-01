"""Theme handling for the Stream Deck UI window.

The look is chosen along two independent axes:

* a *base theme* — ``default`` (the platform look), ``xp`` (a Windows XP "Luna"
  style) or ``modern`` (a flat, rounded, accent-driven style); and
* a *dark mode* toggle that darkens whichever base theme is selected.

Each base theme therefore has a light and a dark variant. The palette (and, for
the XP and modern themes, a full stylesheet) is applied to the whole Qt
application, and the platform default look is restored for the light default
theme. Both preferences are persisted with :class:`~PySide6.QtCore.QSettings`
so they survive restarts.
"""

from string import Template
from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Base theme keys (persisted as a string).
THEME_DEFAULT = "default"
THEME_XP = "xp"
THEME_MODERN = "modern"
THEMES = (THEME_DEFAULT, THEME_XP, THEME_MODERN)

THEME_SETTING = "theme"
DARK_MODE_SETTING = "dark_mode"

# Tooltips are not covered by the palette consistently across styles, so the
# default dark theme gets an explicit stylesheet for them.
_DARK_TOOLTIP_STYLE = "QToolTip { color: #dcdcdc; background-color: #2a2a2a; border: 1px solid #3a3a3a; }"

# The platform default look, captured the first time a theme is applied so it
# can be restored for the light default theme.
_default_palette: Optional[QPalette] = None
_default_style: Optional[str] = None


# ---------------------------------------------------------------------------
# Windows XP ("Luna" light / graphite dark) stylesheet
# ---------------------------------------------------------------------------

_XP_TEMPLATE = Template("""
QMainWindow, QDialog, QWidget#centralwidget {
    background-color: ${face};
}
* {
    font-family: "Tahoma", "Segoe UI", "DejaVu Sans", sans-serif;
}

QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${menubar0}, stop:1 ${menubar1});
    border-bottom: 1px solid ${line};
}
QMenuBar::item { background: transparent; padding: 3px 8px; }
QMenuBar::item:selected {
    background: ${mb_sel_bg};
    border: 1px solid ${mb_sel_border};
    border-radius: 2px;
}
QMenu { background-color: ${menu_bg}; border: 1px solid ${line}; }
QMenu::item { padding: 3px 24px 3px 20px; }
QMenu::item:selected { background-color: ${sel}; color: ${sel_text}; }
QMenu::separator { height: 1px; background: ${line}; margin: 3px 0; }

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${btn0}, stop:0.45 ${btn1}, stop:0.5 ${btn2}, stop:1 ${btn3});
    border: 1px solid ${btn_border};
    border-radius: 3px;
    padding: 3px 12px;
    min-height: 18px;
    color: ${text};
}
QPushButton:hover {
    border: 1px solid ${hover_border};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${hov0}, stop:0.45 ${hov1}, stop:0.5 ${hov2}, stop:1 ${hov3});
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${press0}, stop:1 ${press1});
    border: 1px solid ${press_border};
}
QPushButton:default { border: 1px solid ${default_border}; }
QPushButton:disabled {
    color: ${disabled_text};
    border: 1px solid ${disabled_border};
    background: ${face};
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: ${input_bg};
    border: 1px solid ${input_border};
    border-radius: 0px;
    padding: 2px;
    color: ${text};
    selection-background-color: ${sel};
    selection-color: ${sel_text};
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid ${focus_border}; }

QComboBox {
    background-color: ${input_bg};
    border: 1px solid ${input_border};
    border-radius: 0px;
    padding: 2px 4px;
    min-height: 18px;
    color: ${text};
}
QComboBox:focus { border: 1px solid ${focus_border}; }
QComboBox::drop-down {
    width: 18px;
    border-left: 1px solid ${input_border};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${dd0}, stop:1 ${dd1});
}
QComboBox QAbstractItemView {
    background-color: ${input_bg};
    border: 1px solid ${input_border};
    color: ${text};
    selection-background-color: ${sel};
    selection-color: ${sel_text};
}

QTabWidget::pane { border: 1px solid ${tab_border}; background: ${face}; top: -1px; }
QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${tab0}, stop:1 ${tab1});
    border: 1px solid ${tab_border};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 4px 12px;
    margin-right: 2px;
    color: ${text};
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${tabsel0}, stop:1 ${tabsel1});
    border-bottom: 1px solid ${face};
}
QTabBar::tab:hover:!selected { background: ${tab_hover}; }

QGroupBox {
    border: 1px solid ${line};
    border-radius: 3px;
    margin-top: 8px;
    background: ${face};
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 3px;
    color: ${group_title};
}

QProgressBar {
    border: 1px solid ${input_border};
    border-radius: 0px;
    background: ${input_bg};
    text-align: center;
    color: ${text};
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #A6E27F, stop:1 #4CA11E);
    width: 8px;
    margin: 1px;
}

QCheckBox::indicator, QRadioButton::indicator { width: 13px; height: 13px; }
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    background: ${input_bg};
    border: 1px solid ${input_border};
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: ${input_bg};
    border: 1px solid ${default_border};
}

QScrollBar:vertical { background: ${face}; width: 16px; margin: 0; }
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 ${scroll0}, stop:1 ${scroll1});
    border: 1px solid ${tab_border};
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar:horizontal { background: ${face}; height: 16px; margin: 0; }
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 ${scroll0}, stop:1 ${scroll1});
    border: 1px solid ${tab_border};
    border-radius: 2px;
    min-width: 20px;
}
QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }

QMenuBar, QStatusBar { color: ${text}; }
QToolTip {
    color: ${tooltip_text};
    background-color: ${tooltip_bg};
    border: 1px solid ${tooltip_border};
    padding: 2px;
}
""")

_XP_LIGHT = {
    "face": "#ECE9D8",
    "menubar0": "#FBFBF8",
    "menubar1": "#ECE9D8",
    "line": "#ACA899",
    "mb_sel_bg": "#C1D2EE",
    "mb_sel_border": "#316AC5",
    "menu_bg": "#FFFFFF",
    "sel": "#316AC5",
    "sel_text": "#FFFFFF",
    "btn0": "#FFFFFF",
    "btn1": "#F5F4EE",
    "btn2": "#ECE9D8",
    "btn3": "#DEDACA",
    "btn_border": "#8A8A7A",
    "text": "#000000",
    "hover_border": "#E8A200",
    "hov0": "#FFFFFF",
    "hov1": "#FEFBF0",
    "hov2": "#FDF4D8",
    "hov3": "#FCEEBE",
    "press0": "#DEDACA",
    "press1": "#ECE9D8",
    "press_border": "#707064",
    "default_border": "#316AC5",
    "disabled_text": "#A0A0A0",
    "disabled_border": "#C5C2B8",
    "input_bg": "#FFFFFF",
    "input_border": "#7F9DB9",
    "focus_border": "#316AC5",
    "dd0": "#FFFFFF",
    "dd1": "#DEDACA",
    "tab_border": "#919B9C",
    "tab0": "#FCFCFB",
    "tab1": "#E3DFD0",
    "tabsel0": "#FFFFFF",
    "tabsel1": "#ECE9D8",
    "tab_hover": "#FDF4D8",
    "group_title": "#15428B",
    "scroll0": "#F5F4EE",
    "scroll1": "#C9C5B4",
    "tooltip_text": "#000000",
    "tooltip_bg": "#FFFFE1",
    "tooltip_border": "#000000",
}

_XP_DARK = {
    "face": "#3A3A3A",
    "menubar0": "#4A4A4A",
    "menubar1": "#3A3A3A",
    "line": "#2A2A2A",
    "mb_sel_bg": "#4A5A7A",
    "mb_sel_border": "#6E8FC9",
    "menu_bg": "#2E2E2E",
    "sel": "#3A6EA5",
    "sel_text": "#FFFFFF",
    "btn0": "#6A6A6A",
    "btn1": "#5A5A5A",
    "btn2": "#4A4A4A",
    "btn3": "#3C3C3C",
    "btn_border": "#222222",
    "text": "#E0E0E0",
    "hover_border": "#E8A200",
    "hov0": "#767676",
    "hov1": "#6A6A6A",
    "hov2": "#5A5A5A",
    "hov3": "#4C4C4C",
    "press0": "#3C3C3C",
    "press1": "#4A4A4A",
    "press_border": "#222222",
    "default_border": "#6E8FC9",
    "disabled_text": "#7A7A7A",
    "disabled_border": "#333333",
    "input_bg": "#2A2A2A",
    "input_border": "#555555",
    "focus_border": "#6E8FC9",
    "dd0": "#5A5A5A",
    "dd1": "#3C3C3C",
    "tab_border": "#2A2A2A",
    "tab0": "#555555",
    "tab1": "#3C3C3C",
    "tabsel0": "#6A6A6A",
    "tabsel1": "#3A3A3A",
    "tab_hover": "#4C4C4C",
    "group_title": "#9DB4D8",
    "scroll0": "#5A5A5A",
    "scroll1": "#444444",
    "tooltip_text": "#E0E0E0",
    "tooltip_bg": "#1F1F1F",
    "tooltip_border": "#000000",
}

_XP_STYLESHEET_LIGHT = _XP_TEMPLATE.substitute(_XP_LIGHT)
_XP_STYLESHEET_DARK = _XP_TEMPLATE.substitute(_XP_DARK)


# ---------------------------------------------------------------------------
# Modern (flat, rounded, indigo accent) stylesheet
# ---------------------------------------------------------------------------

_MODERN_TEMPLATE = Template("""
QMainWindow, QDialog, QWidget#centralwidget {
    background-color: ${canvas};
}
* {
    font-family: "Inter", "Segoe UI", "Cantarell", "Noto Sans", sans-serif;
}

QMenuBar { background-color: ${canvas}; border: none; padding: 2px; }
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
    color: ${text};
}
QMenuBar::item:selected { background: ${menu_hover}; }
QMenu {
    background-color: ${card};
    border: 1px solid ${border};
    border-radius: 10px;
    padding: 6px;
    color: ${text};
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 6px; }
QMenu::item:selected { background-color: ${accent}; color: #FFFFFF; }
QMenu::separator { height: 1px; background: ${menu_hover}; margin: 6px 8px; }

QPushButton {
    background-color: ${card};
    border: 1px solid ${border};
    border-radius: 8px;
    padding: 6px 14px;
    color: ${text};
    min-height: 18px;
}
QPushButton:hover { background-color: ${hover}; border-color: ${border_strong}; }
QPushButton:pressed { background-color: ${pressed}; }
QPushButton:default {
    background-color: ${accent};
    border: 1px solid ${accent};
    color: #FFFFFF;
}
QPushButton:default:hover { background-color: ${accent_hover}; border-color: ${accent_hover}; }
QPushButton:disabled {
    color: ${disabled};
    background-color: ${disabled_bg};
    border-color: ${border};
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: ${card};
    border: 1px solid ${border_strong};
    border-radius: 8px;
    padding: 5px 8px;
    min-height: 18px;
    color: ${text};
    selection-background-color: ${accent};
    selection-color: #FFFFFF;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid ${accent}; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: ${card};
    border: 1px solid ${border};
    border-radius: 8px;
    padding: 4px;
    color: ${text};
    selection-background-color: ${accent};
    selection-color: #FFFFFF;
}

QTabWidget::pane { border: none; background: transparent; top: -1px; }
QTabBar::tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    margin-right: 4px;
    color: ${muted};
}
QTabBar::tab:selected { color: ${accent}; border-bottom: 2px solid ${accent}; }
QTabBar::tab:hover:!selected { color: ${text}; }

QGroupBox {
    border: 1px solid ${border};
    border-radius: 12px;
    margin-top: 10px;
    padding-top: 6px;
    background: ${card};
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: ${muted};
}

QProgressBar {
    border: none;
    border-radius: 6px;
    background: ${track};
    text-align: center;
    color: ${text};
    min-height: 8px;
}
QProgressBar::chunk { background: ${accent}; border-radius: 6px; }

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    background: ${card};
    border: 1px solid ${border_strong};
}
QCheckBox::indicator { border-radius: 5px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: ${accent};
    border: 1px solid ${accent};
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: ${scroll}; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: ${scroll_hover}; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: ${scroll}; border-radius: 5px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: ${scroll_hover}; }
QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QToolTip {
    color: ${tooltip_fg};
    background-color: ${tooltip_bg};
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
}
""")

_MODERN_LIGHT = {
    "canvas": "#F7F8FA",
    "text": "#1F2430",
    "card": "#FFFFFF",
    "border": "#E2E5EA",
    "border_strong": "#D8DCE2",
    "hover": "#F0F1F4",
    "pressed": "#E6E8EC",
    "menu_hover": "#ECEDF1",
    "accent": "#4F46E5",
    "accent_hover": "#4338CA",
    "muted": "#6B7280",
    "disabled": "#B4B8C0",
    "disabled_bg": "#F2F3F5",
    "track": "#ECEDF1",
    "scroll": "#C7CCD4",
    "scroll_hover": "#AEB4BE",
    "tooltip_bg": "#1F2430",
    "tooltip_fg": "#FFFFFF",
}

_MODERN_DARK = {
    "canvas": "#15171E",
    "text": "#E6E8EC",
    "card": "#1E212B",
    "border": "#2A2E3A",
    "border_strong": "#353A48",
    "hover": "#262A36",
    "pressed": "#2E333F",
    "menu_hover": "#262A36",
    "accent": "#6366F1",
    "accent_hover": "#7B7EF5",
    "muted": "#9AA0AB",
    "disabled": "#5A606C",
    "disabled_bg": "#1A1D26",
    "track": "#262A36",
    "scroll": "#3A4150",
    "scroll_hover": "#4A5161",
    "tooltip_bg": "#2A2E3A",
    "tooltip_fg": "#E6E8EC",
}

_MODERN_STYLESHEET_LIGHT = _MODERN_TEMPLATE.substitute(_MODERN_LIGHT)
_MODERN_STYLESHEET_DARK = _MODERN_TEMPLATE.substitute(_MODERN_DARK)


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------


def _build_dark_palette() -> QPalette:
    """Builds the default dark colour palette suitable for the Fusion style."""
    window = QColor(53, 53, 53)
    base = QColor(35, 35, 35)
    alternate_base = QColor(45, 45, 45)
    text = QColor(220, 220, 220)
    disabled_text = QColor(127, 127, 127)
    highlight = QColor(42, 130, 218)

    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, window)
    palette.setColor(role.WindowText, text)
    palette.setColor(role.Base, base)
    palette.setColor(role.AlternateBase, alternate_base)
    palette.setColor(role.ToolTipBase, window)
    palette.setColor(role.ToolTipText, text)
    palette.setColor(role.Text, text)
    palette.setColor(role.Button, window)
    palette.setColor(role.ButtonText, text)
    palette.setColor(role.BrightText, QColor(255, 80, 80))
    palette.setColor(role.Link, highlight)
    palette.setColor(role.Highlight, highlight)
    palette.setColor(role.HighlightedText, QColor(0, 0, 0))
    palette.setColor(role.PlaceholderText, disabled_text)

    for disabled_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, disabled_text)
    palette.setColor(group.Disabled, role.Highlight, QColor(80, 80, 80))
    palette.setColor(group.Disabled, role.HighlightedText, disabled_text)

    return palette


def _palette_from(colors: dict) -> QPalette:
    """Builds a Fusion palette from a colour mapping (keys as used below)."""
    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, QColor(colors["window"]))
    palette.setColor(role.WindowText, QColor(colors["text"]))
    palette.setColor(role.Base, QColor(colors["base"]))
    palette.setColor(role.AlternateBase, QColor(colors["alternate_base"]))
    palette.setColor(role.ToolTipBase, QColor(colors["tooltip_base"]))
    palette.setColor(role.ToolTipText, QColor(colors["tooltip_text"]))
    palette.setColor(role.Text, QColor(colors["text"]))
    palette.setColor(role.Button, QColor(colors["button"]))
    palette.setColor(role.ButtonText, QColor(colors["text"]))
    palette.setColor(role.BrightText, QColor(colors["bright_text"]))
    palette.setColor(role.Link, QColor(colors["highlight"]))
    palette.setColor(role.Highlight, QColor(colors["highlight"]))
    palette.setColor(role.HighlightedText, QColor(colors["highlighted_text"]))
    palette.setColor(role.PlaceholderText, QColor(colors["disabled_text"]))

    for disabled_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, QColor(colors["disabled_text"]))

    return palette


def _build_xp_palette(dark: bool = False) -> QPalette:
    """Builds the Windows XP palette (Luna light or graphite dark)."""
    if dark:
        return _palette_from(
            {
                "window": "#3C3C3C",
                "text": "#E0E0E0",
                "base": "#2A2A2A",
                "alternate_base": "#333333",
                "tooltip_base": "#1F1F1F",
                "tooltip_text": "#E0E0E0",
                "button": "#4A4A4A",
                "bright_text": "#FF5050",
                "highlight": "#3A6EA5",
                "highlighted_text": "#FFFFFF",
                "disabled_text": "#7A7A7A",
            }
        )
    return _palette_from(
        {
            "window": "#ECE9D8",
            "text": "#000000",
            "base": "#FFFFFF",
            "alternate_base": "#F5F4EE",
            "tooltip_base": "#FFFFE1",
            "tooltip_text": "#000000",
            "button": "#ECE9D8",
            "bright_text": "#FF0000",
            "highlight": "#316AC5",
            "highlighted_text": "#FFFFFF",
            "disabled_text": "#A0A0A0",
        }
    )


def _build_modern_palette(dark: bool = False) -> QPalette:
    """Builds the modern palette (light off-white or dark slate)."""
    if dark:
        return _palette_from(
            {
                "window": "#15171E",
                "text": "#E6E8EC",
                "base": "#1E212B",
                "alternate_base": "#1A1D26",
                "tooltip_base": "#2A2E3A",
                "tooltip_text": "#E6E8EC",
                "button": "#1E212B",
                "bright_text": "#F87171",
                "highlight": "#6366F1",
                "highlighted_text": "#FFFFFF",
                "disabled_text": "#5A606C",
            }
        )
    return _palette_from(
        {
            "window": "#F7F8FA",
            "text": "#1F2430",
            "base": "#FFFFFF",
            "alternate_base": "#F2F3F5",
            "tooltip_base": "#1F2430",
            "tooltip_text": "#FFFFFF",
            "button": "#FFFFFF",
            "bright_text": "#DC2626",
            "highlight": "#4F46E5",
            "highlighted_text": "#FFFFFF",
            "disabled_text": "#B4B8C0",
        }
    )


# ---------------------------------------------------------------------------
# Applying and persisting
# ---------------------------------------------------------------------------


def _capture_default_look(app: QApplication) -> None:
    """Remembers the platform default palette/style on first use."""
    global _default_palette, _default_style

    if _default_palette is None:
        _default_palette = app.palette()
    if _default_style is None:
        current_style = app.style()
        _default_style = current_style.objectName() if current_style else ""


def apply_theme(app: QApplication, theme: str = THEME_DEFAULT, dark: bool = False) -> None:
    """Applies the chosen base theme and dark-mode state to the application."""
    _capture_default_look(app)

    if theme == THEME_MODERN:
        app.setStyle("Fusion")
        app.setPalette(_build_modern_palette(dark))
        app.setStyleSheet(_MODERN_STYLESHEET_DARK if dark else _MODERN_STYLESHEET_LIGHT)
    elif theme == THEME_XP:
        app.setStyle("Fusion")
        app.setPalette(_build_xp_palette(dark))
        app.setStyleSheet(_XP_STYLESHEET_DARK if dark else _XP_STYLESHEET_LIGHT)
    elif dark:
        # Default theme, dark mode: the classic Fusion dark palette.
        app.setStyle("Fusion")
        app.setPalette(_build_dark_palette())
        app.setStyleSheet(_DARK_TOOLTIP_STYLE)
    else:
        # Default theme, light mode: restore the platform default look.
        if _default_style:
            app.setStyle(_default_style)
        if _default_palette is not None:
            app.setPalette(_default_palette)
        app.setStyleSheet("")


def get_theme(settings: QSettings) -> str:
    """Returns the persisted base theme key (defaults to the platform look)."""
    value = settings.value(THEME_SETTING, THEME_DEFAULT, type=str)
    return value if value in THEMES else THEME_DEFAULT


def set_theme(settings: QSettings, theme: str) -> None:
    """Persists the base theme key."""
    settings.setValue(THEME_SETTING, theme if theme in THEMES else THEME_DEFAULT)


def is_dark_mode_enabled(settings: QSettings) -> bool:
    """Returns the persisted dark mode preference (defaults to off)."""
    return bool(settings.value(DARK_MODE_SETTING, False, type=bool))


def set_dark_mode_enabled(settings: QSettings, enabled: bool) -> None:
    """Persists the dark mode preference."""
    settings.setValue(DARK_MODE_SETTING, enabled)
