import os

from streamdeck_ui.modules import sample_icons


def _make(base, category, file_name):
    directory = os.path.join(base, category)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, file_name)
    open(path, "w").close()
    return path


def test_list_sample_icons_groups_and_sorts(tmp_path):
    base = str(tmp_path)
    _make(base, "volume", "volume_up.png")
    _make(base, "volume", "volume_down.png")
    _make(base, "media", "play.png")

    result = sample_icons.list_sample_icons(base)

    # Categories sorted, icons sorted, names prettified.
    assert list(result.keys()) == ["media", "volume"]
    assert [name for name, _ in result["volume"]] == ["Volume Down", "Volume Up"]
    assert result["media"][0][0] == "Play"
    assert result["media"][0][1].endswith(os.path.join("media", "play.png"))


def test_list_sample_icons_ignores_non_images_and_empty_categories(tmp_path):
    base = str(tmp_path)
    _make(base, "media", "play.png")
    _make(base, "media", "notes.txt")
    os.makedirs(os.path.join(base, "empty"))

    result = sample_icons.list_sample_icons(base)

    assert list(result.keys()) == ["media"]
    assert [name for name, _ in result["media"]] == ["Play"]


def test_list_sample_icons_missing_dir(tmp_path):
    assert sample_icons.list_sample_icons(str(tmp_path / "does-not-exist")) == {}


def test_bundled_sample_icons_present():
    # The icons shipped with the package should be discoverable.
    result = sample_icons.list_sample_icons()
    assert "media" in result
    assert "volume" in result


def test_bundled_windows_xp_pack_present():
    # The retro Windows XP style pack ships as its own category.
    result = sample_icons.list_sample_icons()
    assert "windows_xp" in result

    names = {name for name, _ in result["windows_xp"]}
    # A representative spread: window controls, file types and system icons.
    for expected in ("Window Close", "Folder", "Text File", "Recycle Empty"):
        assert expected in names
