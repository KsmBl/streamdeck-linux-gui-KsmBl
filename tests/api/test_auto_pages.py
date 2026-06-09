from streamdeck_ui.modules.control_presets import ControlAction, ControlPreset
from tests.common import STREAMDECK_SERIAL


def test_auto_pages_default_empty(api_server):
    assert api_server.get_auto_pages(STREAMDECK_SERIAL) == []
    assert api_server.get_overlay_page(STREAMDECK_SERIAL) is None


def test_add_auto_page_marks_and_binds(api_server):
    page = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox")
    assert api_server.is_auto_page(STREAMDECK_SERIAL, page)
    assert api_server.get_auto_pages(STREAMDECK_SERIAL) == [page]
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, page) == "firefox"


def test_add_auto_page_seeds_from_preset(api_server):
    preset = ControlPreset("Test", [ControlAction("New", "ctrl+t"), ControlAction("Close", "ctrl+w")])
    page = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox", preset)
    assert api_server.get_button_text(STREAMDECK_SERIAL, page, 0) == "New"
    assert api_server.get_button_keys(STREAMDECK_SERIAL, page, 1) == "ctrl+w"


def test_remove_auto_page(api_server):
    page = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox")
    api_server.remove_auto_page(STREAMDECK_SERIAL, page)
    assert page not in api_server.get_auto_pages(STREAMDECK_SERIAL)
    assert page not in api_server.get_pages(STREAMDECK_SERIAL)
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {}


def test_set_overlay_page_unmarks_auto_and_binding(api_server):
    page = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox")
    api_server.set_overlay_page(STREAMDECK_SERIAL, page)
    assert api_server.get_overlay_page(STREAMDECK_SERIAL) == page
    # The overlay is not itself an auto page and carries no focus binding.
    assert not api_server.is_auto_page(STREAMDECK_SERIAL, page)
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, page) is None

    api_server.clear_overlay_page(STREAMDECK_SERIAL)
    assert api_server.get_overlay_page(STREAMDECK_SERIAL) is None


def test_resolve_overlay_passthrough_without_overlay(api_server):
    auto = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox")
    assert api_server.resolve_overlay(STREAMDECK_SERIAL, auto, 0) == (auto, 0)


def test_resolve_overlay_overrides_nonempty_button_on_auto_page(api_server):
    auto = api_server.add_auto_page(STREAMDECK_SERIAL, "firefox")
    overlay = api_server.add_new_page(STREAMDECK_SERIAL)
    api_server.set_overlay_page(STREAMDECK_SERIAL, overlay)
    # Button 0 has overlay content, button 1 does not.
    api_server.set_button_text(STREAMDECK_SERIAL, overlay, 0, "Leave")

    assert api_server.resolve_overlay(STREAMDECK_SERIAL, auto, 0) == (overlay, 0)
    assert api_server.resolve_overlay(STREAMDECK_SERIAL, auto, 1) == (auto, 1)


def test_seed_default_auto_pages(api_server):
    from streamdeck_ui.modules.control_presets import CONTROL_PRESETS

    api_server.state[STREAMDECK_SERIAL].auto_pages_seeded = False
    api_server.seed_default_auto_pages(STREAMDECK_SERIAL)

    assert api_server.is_auto_seeded(STREAMDECK_SERIAL)
    # One page per preset plus the Home dashboard page.
    assert len(api_server.get_auto_pages(STREAMDECK_SERIAL)) == len(CONTROL_PRESETS) + 1
    # The Home page exists, is an auto page and is bound to no application.
    home = api_server.get_home_page(STREAMDECK_SERIAL)
    assert home in api_server.get_auto_pages(STREAMDECK_SERIAL)
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, home) is None
    # Its live tiles are centred on a tinted tile, with larger, per-stat colours.
    assert api_server.get_button_text_vertical_align(STREAMDECK_SERIAL, home, 0) == "middle"
    assert api_server.get_button_text_horizontal_align(STREAMDECK_SERIAL, home, 0) == "center"
    assert api_server.get_button_background_color(STREAMDECK_SERIAL, home, 0) == "#1f2230"
    assert api_server.get_button_font_size(STREAMDECK_SERIAL, home, 0) == 18
    assert api_server.get_button_font_color(STREAMDECK_SERIAL, home, 0) == "#ff7043"
    # Presets with an application are bound to it.
    apps = set(api_server.get_focus_pages(STREAMDECK_SERIAL).keys())
    assert {"firefox", "vivaldi", "thunar", "gimp"} <= apps

    # Seeding is idempotent — running again creates nothing new.
    api_server.seed_default_auto_pages(STREAMDECK_SERIAL)
    assert len(api_server.get_auto_pages(STREAMDECK_SERIAL)) == len(CONTROL_PRESETS) + 1


def test_reset_auto_pages_restores_defaults(api_server):
    from streamdeck_ui.modules.control_presets import CONTROL_PRESETS

    # Start from an edited Auto group: an extra custom page and an overlay.
    api_server.state[STREAMDECK_SERIAL].auto_pages_seeded = True
    custom = api_server.add_auto_page(STREAMDECK_SERIAL, "custom-app")
    overlay = api_server.add_new_page(STREAMDECK_SERIAL)
    api_server.set_overlay_page(STREAMDECK_SERIAL, overlay)
    # Sit on a page that the reset will delete (this used to crash the display).
    api_server.set_page(STREAMDECK_SERIAL, custom)

    api_server.reset_auto_pages(STREAMDECK_SERIAL)

    # The deck ends up on a page that still exists.
    assert api_server.get_page(STREAMDECK_SERIAL) in api_server.get_pages(STREAMDECK_SERIAL)
    # The overlay is gone and the defaults (presets + Home) are back.
    assert api_server.get_overlay_page(STREAMDECK_SERIAL) is None
    assert len(api_server.get_auto_pages(STREAMDECK_SERIAL)) == len(CONTROL_PRESETS) + 1
    assert api_server.get_home_page(STREAMDECK_SERIAL) in api_server.get_auto_pages(STREAMDECK_SERIAL)
    apps = set(api_server.get_focus_pages(STREAMDECK_SERIAL).keys())
    assert {"firefox", "discord", "vlc"} <= apps
    assert "custom-app" not in apps


def test_resolve_overlay_passthrough_on_normal_page(api_server):
    overlay = api_server.add_new_page(STREAMDECK_SERIAL)
    api_server.set_overlay_page(STREAMDECK_SERIAL, overlay)
    api_server.set_button_text(STREAMDECK_SERIAL, overlay, 0, "Leave")
    # Page 0 is a normal page, so the overlay does not apply to it.
    assert api_server.resolve_overlay(STREAMDECK_SERIAL, 0, 0) == (0, 0)
