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


def test_get_focused_app_returns_first_match():
    with patch.object(focus, "_DETECTORS", [lambda: None, lambda: "kitty", lambda: "ignored"]):
        assert focus.get_focused_app() == "kitty"


def test_get_focused_app_none_when_unsupported():
    with patch.object(focus, "_DETECTORS", [lambda: None, lambda: None]):
        assert focus.get_focused_app() is None
        assert focus.focus_detection_available() is False


def test_detector_exceptions_are_swallowed():
    def boom():
        raise RuntimeError("nope")

    with patch.object(focus, "_DETECTORS", [boom, lambda: "safe"]):
        assert focus.get_focused_app() == "safe"
