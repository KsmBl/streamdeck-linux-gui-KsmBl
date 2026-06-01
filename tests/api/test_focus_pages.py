from tests.common import STREAMDECK_SERIAL


def test_focus_pages_default_empty(api_server):
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {}


def test_set_and_get_focus_page(api_server):
    api_server.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {"firefox": 1}
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, 1) == "firefox"
    assert api_server.get_focus_app_for_page(STREAMDECK_SERIAL, 0) is None


def test_remove_focus_page(api_server):
    api_server.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api_server.set_focus_page(STREAMDECK_SERIAL, "chromium", 0)
    api_server.remove_focus_page(STREAMDECK_SERIAL, 1)
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {"chromium": 0}


def test_removing_a_page_clears_its_focus_binding(api_server):
    api_server.set_focus_page(STREAMDECK_SERIAL, "firefox", 1)
    api_server.set_focus_page(STREAMDECK_SERIAL, "chromium", 0)

    api_server.remove_page(STREAMDECK_SERIAL, 1)

    # The deleted page's binding is gone; the other page keeps its binding.
    assert api_server.get_focus_pages(STREAMDECK_SERIAL) == {"chromium": 0}
