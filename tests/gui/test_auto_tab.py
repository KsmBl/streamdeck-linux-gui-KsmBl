from streamdeck_ui import gui
from streamdeck_ui.gui import AutoPagePanel
from tests.common import STREAMDECK_SERIAL


def test_auto_tab_is_appended(api_and_window):
    main_window, _api = api_and_window
    ui = main_window.ui
    # The last tab is always the synthetic Auto tab (no page id).
    last = ui.pages.widget(ui.pages.count() - 1)
    assert last.property("auto_tab") is True
    assert last.property("page_id") is None


def test_auto_pages_hidden_from_normal_strip_and_listed_in_panel(api_and_window):
    main_window, api = api_and_window
    ui = main_window.ui
    api.add_auto_page(STREAMDECK_SERIAL, "firefox")
    gui.build_device(ui, api)

    # No normal tab represents the auto page; it lives inside the Auto tab.
    auto_tab = ui.pages.widget(ui.pages.count() - 1)
    page_ids = [ui.pages.widget(i).property("page_id") for i in range(ui.pages.count())]
    assert page_ids.count(None) == 1  # only the Auto tab has no page id

    panel = auto_tab.findChild(AutoPagePanel)
    assert panel is not None
    assert panel.list.count() == 1


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
    auto_tab = ui.pages.widget(ui.pages.count() - 1)
    assert auto_tab.findChild(AutoPagePanel).list.count() == len(CONTROL_PRESETS) + 1
    page_ids = [ui.pages.widget(i).property("page_id") for i in range(ui.pages.count())]
    assert page_ids.count(None) == 1


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
    ui.pages.setCurrentIndex(ui.pages.count() - 1)
    auto_tab = ui.pages.currentWidget()
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
