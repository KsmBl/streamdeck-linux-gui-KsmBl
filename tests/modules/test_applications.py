import os

import pytest

from streamdeck_ui.modules import applications


def _write_desktop(directory, file_name, contents):
    path = os.path.join(directory, file_name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(contents)
    return path


def test_parse_desktop_file_strips_field_codes(tmp_path):
    path = _write_desktop(
        tmp_path,
        "firefox.desktop",
        "[Desktop Entry]\nType=Application\nName=Firefox\nExec=firefox %u\nIcon=firefox\n",
    )

    app = applications.parse_desktop_file(path)

    assert app is not None
    assert app.name == "Firefox"
    assert app.command == "firefox"
    assert app.icon_name == "firefox"


def test_parse_desktop_file_keeps_arguments(tmp_path):
    path = _write_desktop(
        tmp_path,
        "thunar-bulk.desktop",
        "[Desktop Entry]\nType=Application\nName=Bulk Rename\nExec=thunar --bulk-rename %F\nIcon=thunar\n",
    )

    app = applications.parse_desktop_file(path)

    assert app is not None
    assert app.command == "thunar --bulk-rename"


@pytest.mark.parametrize(
    "contents",
    [
        # NoDisplay entries should be skipped
        "[Desktop Entry]\nType=Application\nName=Hidden\nExec=foo\nNoDisplay=true\n",
        # Hidden entries should be skipped
        "[Desktop Entry]\nType=Application\nName=Hidden\nExec=foo\nHidden=true\n",
        # Non-application types should be skipped
        "[Desktop Entry]\nType=Link\nName=Some Link\nURL=http://example.com\n",
        # Missing Exec should be skipped
        "[Desktop Entry]\nType=Application\nName=NoExec\n",
        # Missing Name should be skipped
        "[Desktop Entry]\nType=Application\nExec=foo\n",
    ],
)
def test_parse_desktop_file_skips_non_launchable(tmp_path, contents):
    path = _write_desktop(tmp_path, "entry.desktop", contents)
    assert applications.parse_desktop_file(path) is None


def test_parse_desktop_file_ignores_other_sections(tmp_path):
    path = _write_desktop(
        tmp_path,
        "app.desktop",
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Real App\n"
        "Exec=real-app\n"
        "Icon=real-app\n"
        "[Desktop Action new]\n"
        "Name=New Window\n"
        "Exec=real-app --new\n",
    )

    app = applications.parse_desktop_file(path)

    assert app is not None
    assert app.command == "real-app"


def test_list_desktop_applications_dedupes_and_sorts(tmp_path, monkeypatch):
    user_dir = tmp_path / "user"
    system_dir = tmp_path / "system"
    user_dir.mkdir()
    system_dir.mkdir()

    # Same desktop id in both locations: the user one must win.
    _write_desktop(
        str(user_dir),
        "editor.desktop",
        "[Desktop Entry]\nType=Application\nName=Editor (user)\nExec=user-editor\n",
    )
    _write_desktop(
        str(system_dir),
        "editor.desktop",
        "[Desktop Entry]\nType=Application\nName=Editor (system)\nExec=system-editor\n",
    )
    _write_desktop(
        str(system_dir),
        "browser.desktop",
        "[Desktop Entry]\nType=Application\nName=Browser\nExec=browser\n",
    )

    monkeypatch.setattr(applications, "_desktop_directories", lambda: [str(user_dir), str(system_dir)])

    apps = applications.list_desktop_applications()

    names = [app.name for app in apps]
    # Sorted alphabetically (case insensitive)
    assert names == ["Browser", "Editor (user)"]
    editor = next(app for app in apps if app.name.startswith("Editor"))
    assert editor.command == "user-editor"


def test_find_icon_file_absolute_path(tmp_path):
    icon = tmp_path / "logo.png"
    icon.write_bytes(b"not really a png but exists")

    assert applications.find_icon_file(str(icon)) == str(icon)
    assert applications.find_icon_file(str(tmp_path / "missing.png")) is None


def test_find_icon_file_prefers_largest_raster(tmp_path, monkeypatch):
    theme = tmp_path / "icons" / "hicolor"
    small = theme / "32x32" / "apps"
    large = theme / "256x256" / "apps"
    scalable = theme / "scalable" / "apps"
    for directory in (small, large, scalable):
        directory.mkdir(parents=True)

    (small / "myapp.png").write_bytes(b"small")
    (large / "myapp.png").write_bytes(b"large")
    (scalable / "myapp.svg").write_text("<svg/>")

    monkeypatch.setattr(applications, "_icon_search_directories", lambda: [str(tmp_path / "icons")])

    resolved = applications.find_icon_file("myapp")
    assert resolved is not None
    assert resolved.endswith(os.path.join("256x256", "apps", "myapp.png"))


def test_find_icon_file_falls_back_to_vector(tmp_path, monkeypatch):
    theme = tmp_path / "icons" / "hicolor"
    tiny = theme / "16x16" / "apps"
    scalable = theme / "scalable" / "apps"
    tiny.mkdir(parents=True)
    scalable.mkdir(parents=True)

    (tiny / "vectorapp.png").write_bytes(b"tiny")
    (scalable / "vectorapp.svg").write_text("<svg/>")

    monkeypatch.setattr(applications, "_icon_search_directories", lambda: [str(tmp_path / "icons")])

    resolved = applications.find_icon_file("vectorapp")
    assert resolved is not None
    assert resolved.endswith("vectorapp.svg")


def test_find_icon_file_strips_extension_in_name(tmp_path, monkeypatch):
    pixmaps = tmp_path / "pixmaps"
    pixmaps.mkdir()
    (pixmaps / "weird.png").write_bytes(b"icon")

    monkeypatch.setattr(applications, "_icon_search_directories", lambda: [str(pixmaps)])

    # Icon value mistakenly includes the extension
    assert applications.find_icon_file("weird.png") == str(pixmaps / "weird.png")


def test_resolve_icon_to_file_returns_existing_path(tmp_path, monkeypatch):
    pixmaps = tmp_path / "pixmaps"
    pixmaps.mkdir()
    icon = pixmaps / "app.png"
    icon.write_bytes(b"icon")

    monkeypatch.setattr(applications, "_icon_search_directories", lambda: [str(pixmaps)])

    cache_dir = str(tmp_path / "cache")
    assert applications.resolve_icon_to_file("app", cache_dir) == str(icon)


def test_resolve_icon_to_file_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(applications, "_icon_search_directories", lambda: [str(tmp_path)])
    assert applications.resolve_icon_to_file("", str(tmp_path / "cache")) is None
