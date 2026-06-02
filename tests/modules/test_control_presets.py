from streamdeck_ui.modules import control_presets
from streamdeck_ui.modules.font_icons import PRESET_ICON_CODEPOINTS
from streamdeck_ui.modules.keyboard import parse_keys_as_keycodes


def test_requested_apps_have_presets():
    names = {preset.name for preset in control_presets.CONTROL_PRESETS}
    assert "Firefox" in names
    assert "Vivaldi" in names
    assert any(name.startswith("Thunar") for name in names)
    assert "Vim" in names


def test_presets_are_non_empty_and_labelled():
    for preset in control_presets.CONTROL_PRESETS:
        assert preset.name
        assert preset.actions
        for action in preset.actions:
            assert action.text
            # A control key must actually do something.
            assert action.keys or action.write or action.command


def test_every_preset_key_combo_is_valid():
    """All keys strings must parse to real key codes, so applying a preset never
    produces a button that raises when pressed."""
    for preset in control_presets.CONTROL_PRESETS:
        for action in preset.actions:
            if action.keys:
                parsed = parse_keys_as_keycodes(action.keys)
                assert parsed, f"{preset.name} / {action.text!r}: {action.keys!r} parsed to nothing"


def test_every_preset_action_has_a_resolvable_icon():
    """Every control key carries an icon whose glyph name has a known Font
    Awesome code point, so applying a preset can render an icon for each key."""
    for preset in control_presets.CONTROL_PRESETS:
        for action in preset.actions:
            assert action.icon, f"{preset.name} / {action.text!r}: missing icon"
            assert (
                action.icon in PRESET_ICON_CODEPOINTS
            ), f"{preset.name} / {action.text!r}: unknown icon {action.icon!r}"


def test_preset_names_helper_matches_presets():
    pairs = control_presets.preset_names()
    assert [name for name, _ in pairs] == [preset.name for preset in control_presets.CONTROL_PRESETS]
