from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from streamdeck_ui import gui
from streamdeck_ui.gui import AutoPagePanel
from tests.common import STREAMDECK_SERIAL


def _auto_tab(ui):
    for tab in range(ui.pages.count()):
        widget = ui.pages.widget(tab)
        if widget.property("auto_tab"):
            return widget
    raise AssertionError("Auto tab not found")


def test_auto_tab_is_present(api_and_window):
    main_window, _api = api_and_window
    auto_tab = _auto_tab(main_window.ui)
    assert auto_tab.property("auto_tab") is True
    assert auto_tab.property("page_id") is None


def test_auto_pages_hidden_from_normal_strip_and_listed_in_panel(api_and_window):
    main_window, api = api_and_window
    ui = main_window.ui
    api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    gui.build_device(ui, api)

    # No normal tab represents the auto page; it lives inside the Auto tab. Only
    # the synthetic Auto, Snake and Lights Out tabs carry no page id.
    auto_tab = _auto_tab(ui)
    page_ids = [ui.pages.widget(i).property("page_id") for i in range(ui.pages.count())]
    assert page_ids.count(None) == 3

    panel = auto_tab.findChild(AutoPagePanel)
    assert panel is not None
    assert panel.list.count() == 1


def test_auto_pages_listed_alphabetically(api_and_window):
    main_window, api = api_and_window
    ui = main_window.ui
    for app in ("zed", "alpha", "mid"):  # added out of order
        api.add_auto_page(STREAMDECK_SERIAL, app)
    gui.build_device(ui, api)

    panel = _auto_tab(ui).findChild(AutoPagePanel)
    apps = [panel.list.item(i).text().split("  —  ")[0] for i in range(panel.list.count())]
    assert apps == ["alpha", "mid", "zed"]


def test_resolve_auto_uses_focused_app(api_and_window):
    _main_window, api = api_and_window
    api.state[STREAMDECK_SERIAL].auto_pages = [0, 1]
    api.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    # The entry page is chosen from the watcher's cached focused app (no probe).
    gui._last_focused_app = "firefox"

    target = gui._resolve_switch_page_target(STREAMDECK_SERIAL, 0, gui.SWITCH_PAGE_AUTO)
    assert target == 1


def test_resolve_auto_falls_back_to_first_auto_page(api_and_window):
    _main_window, api = api_and_window
    api.state[STREAMDECK_SERIAL].auto_pages = [1]
    gui._last_focused_app = None

    target = gui._resolve_switch_page_target(STREAMDECK_SERIAL, 0, gui.SWITCH_PAGE_AUTO)
    assert target == 1


def test_resolve_leave_auto_returns_last_manual_page(api_and_window):
    _main_window, api = api_and_window
    api.state[STREAMDECK_SERIAL].auto_pages = [1]
    gui.last_manual_page[STREAMDECK_SERIAL] = 0

    target = gui._resolve_switch_page_target(STREAMDECK_SERIAL, 1, gui.SWITCH_PAGE_LEAVE_AUTO)
    assert target == 0


def test_build_device_seeds_default_auto_pages(api_and_window, mocker):
    from streamdeck_ui.modules.control_presets import CONTROL_PRESETS

    main_window, api = api_and_window
    ui = main_window.ui
    mocker.patch("streamdeck_ui.gui.update_focus_watcher")
    # Simulate a fresh, never-seeded deck.
    api.state[STREAMDECK_SERIAL].auto_pages = []
    api.state[STREAMDECK_SERIAL].auto_pages_seeded = False

    gui.build_device(ui, api)

    # One auto page per preset plus the Home page, listed in the Auto tab.
    assert len(api.get_auto_pages(STREAMDECK_SERIAL)) == len(CONTROL_PRESETS) + 1
    auto_tab = _auto_tab(ui)
    assert auto_tab.findChild(AutoPagePanel).list.count() == len(CONTROL_PRESETS) + 1
    page_ids = [ui.pages.widget(i).property("page_id") for i in range(ui.pages.count())]
    assert page_ids.count(None) == 3  # the Auto, Snake and Lights Out tabs


def test_prev_next_skip_auto_and_overlay_pages(api_and_window):
    _main_window, api = api_and_window
    auto = api.add_auto_page(STREAMDECK_SERIAL, "firefox")  # noqa: F841 - created to be skipped
    overlay = api.add_new_page(STREAMDECK_SERIAL)
    api.set_overlay_page(STREAMDECK_SERIAL, overlay)

    # Only the normal pages (0 and 1) are walked by Prev/Next.
    assert gui._resolve_switch_page_target(STREAMDECK_SERIAL, 0, gui.SWITCH_PAGE_NEXT) == 1
    assert gui._resolve_switch_page_target(STREAMDECK_SERIAL, 1, gui.SWITCH_PAGE_NEXT) == 0
    assert gui._resolve_switch_page_target(STREAMDECK_SERIAL, 0, gui.SWITCH_PAGE_PREVIOUS) == 1


def test_edit_auto_page_in_place_without_adding_a_tab(api_and_window):
    main_window, api = api_and_window
    ui = main_window.ui
    page = api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    gui.build_device(ui, api)

    # Select the Auto tab (as a user would) before editing.
    auto_tab = _auto_tab(ui)
    ui.pages.setCurrentWidget(auto_tab)
    panel = auto_tab.findChild(AutoPagePanel)
    tabs_before = ui.pages.count()

    panel.list.setCurrentRow(0)
    panel._edit()

    # No new tab was added; the in-place editor is shown for the auto page.
    assert ui.pages.count() == tabs_before
    assert auto_tab.editing_page == page
    assert auto_tab.auto_stack.currentWidget() is panel._editor

    panel._leave_editor()
    assert auto_tab.editing_page is None
    assert auto_tab.auto_stack.currentWidget() is panel


def test_editing_auto_page_greys_overlaid_keys(api_and_window, mocker):
    main_window, api = api_and_window
    ui = main_window.ui
    mocker.patch.object(api, "get_deck_layout", return_value=(1, 3))  # 3 on-screen keys
    page = api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    overlay = api.add_new_page(STREAMDECK_SERIAL)
    api.set_overlay_page(STREAMDECK_SERIAL, overlay)
    api.set_button_text(STREAMDECK_SERIAL, overlay, 0, "X")  # overlay covers key 0
    gui.build_device(ui, api)

    auto_tab = _auto_tab(ui)
    ui.pages.setCurrentWidget(auto_tab)
    panel = auto_tab.findChild(AutoPagePanel)
    for row in range(panel.list.count()):
        if panel.list.item(row).data(Qt.ItemDataRole.UserRole) == page:
            panel.list.setCurrentRow(row)
            break
    panel._edit()

    buttons = {b.property("index"): b for b in panel._grid.findChildren(QToolButton)}
    # Key 0 is covered by the overlay: greyed out and labelled, editing it is futile.
    assert buttons[0].text() == "overlay"
    assert not buttons[0].isEnabled()
    # An uncovered key stays editable.
    assert buttons[1].isEnabled()
