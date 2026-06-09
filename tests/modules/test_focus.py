from unittest.mock import patch

from streamdeck_ui.modules import focus


def test_normalize():
    assert focus._normalize("  Firefox  ") == "firefox"
    assert focus._normalize("") is None
    assert focus._normalize(None) is None


def test_find_focused_node():
    tree = {
        "focused": False,
        "nodes": [
            {"focused": False, "nodes": [{"focused": True, "app_id": "kitty", "nodes": []}]},
        ],
        "floating_nodes": [],
    }
    node = focus._find_focused_node(tree)
    assert node is not None and node["app_id"] == "kitty"


def test_from_sway_uses_app_id():
    tree = '{"focused": false, "nodes": [{"focused": true, "app_id": "Firefox", "nodes": []}]}'
    with patch.dict("os.environ", {"SWAYSOCK": "/run/sway"}, clear=False), patch.object(
        focus.shutil, "which", return_value="/usr/bin/swaymsg"
    ), patch.object(focus, "_run", return_value=tree):
        assert focus._from_sway() == "firefox"


def test_from_hyprland_uses_class():
    with patch.dict("os.environ", {"HYPRLAND_INSTANCE_SIGNATURE": "abc"}, clear=False), patch.object(
        focus.shutil, "which", return_value="/usr/bin/hyprctl"
    ), patch.object(focus, "_run", return_value='{"class": "Alacritty"}'):
        assert focus._from_hyprland() == "alacritty"


def test_from_xprop_extracts_class():
    def fake_run(command):
        if "_NET_ACTIVE_WINDOW" in command:
            return "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x3c00007"
        return 'WM_CLASS(STRING) = "navigator", "firefox"'

    with patch.dict("os.environ", {"DISPLAY": ":0"}, clear=False), patch.object(
        focus.shutil, "which", return_value="/usr/bin/xprop"
    ), patch.object(focus, "_run", side_effect=fake_run):
        assert focus._from_xprop() == "firefox"


def _no_wayland():
    # Disable the Wayland-compositor fast paths so the _DETECTORS chain is used.
    return patch.dict("os.environ", {"SWAYSOCK": "", "HYPRLAND_INSTANCE_SIGNATURE": ""}, clear=False)


def test_get_focused_app_returns_first_match():
    with _no_wayland(), patch.object(focus, "_DETECTORS", [lambda: None, lambda: "kitty", lambda: "ignored"]):
        assert focus.get_focused_app() == "kitty"


def test_get_focused_app_none_when_unsupported():
    with _no_wayland(), patch.object(focus, "_DETECTORS", [lambda: None, lambda: None]):
        assert focus.get_focused_app() is None
        assert focus.focus_detection_available() is False


def test_wayland_is_authoritative_when_nothing_focused():
    # Sway reports no focused window (e.g. an empty workspace); get_focused_app
    # must return None instead of falling through to a stale X11 active window.
    with patch.dict("os.environ", {"SWAYSOCK": "/run/sway"}, clear=False), patch.object(
        focus.shutil, "which", return_value="/usr/bin/swaymsg"
    ), patch.object(focus, "_from_sway", return_value=None), patch.object(
        focus, "_DETECTORS", [lambda: "stale-x11-window"]
    ):
        assert focus.get_focused_app() is None


def test_detector_exceptions_are_swallowed():
    def boom():
        raise RuntimeError("nope")

    with _no_wayland(), patch.object(focus, "_DETECTORS", [boom, lambda: "safe"]):
        assert focus.get_focused_app() == "safe"


def test_collect_sway_apps():
    tree = {
        "app_id": None,
        "nodes": [
            {"app_id": "Firefox", "nodes": []},
            {"window_properties": {"class": "Code"}, "nodes": []},
        ],
        "floating_nodes": [{"app_id": "kitty", "nodes": []}],
    }
    found = set()
    focus._collect_sway_apps(tree, found)
    assert found == {"firefox", "code", "kitty"}


def test_open_from_hyprland():
    with patch.dict("os.environ", {"HYPRLAND_INSTANCE_SIGNATURE": "abc"}, clear=False), patch.object(
        focus.shutil, "which", return_value="/usr/bin/hyprctl"
    ), patch.object(focus, "_run", return_value='[{"class": "Alacritty"}, {"class": "firefox"}]'):
        assert focus._open_from_hyprland() == {"alacritty", "firefox"}


def test_list_open_apps_sorted_and_deduped():
    with patch.object(focus, "_open_from_sway", return_value={"firefox", "kitty"}), patch.object(
        focus, "_open_from_hyprland", return_value=set()
    ), patch.object(focus, "_open_from_x11", return_value={"kitty", "code"}):
        assert focus.list_open_apps() == ["code", "firefox", "kitty"]
