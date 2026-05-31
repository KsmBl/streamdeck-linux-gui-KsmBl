[![Stream Deck UI - a Linux UI for the Elgato Stream Deck](docs/art/logo_large.png)](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)

_________________

**Stream Deck UI for Linux — enhanced fork.**

This is a personal fork of [streamdeck-linux-gui](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)
(itself the community continuation of the original
[streamdeck_ui](https://github.com/timothycrosley/streamdeck-ui)). It keeps everything the
upstream project does — a desktop app to configure and drive an Elgato Stream Deck on Linux —
and adds a set of quality-of-life features on top. Upstream is in maintenance mode and is not
taking new features, so those additions live here instead. All credit for the original work goes
to its authors and contributors.

![Stream Deck UI usage example](docs/art/example.gif)

## What this fork adds

* **Application launcher picker** — an **App…** button next to *Command* lists your installed
  applications (from their desktop entries); pick one to fill in the launch command and a fitting
  icon automatically.
* **Icon library** — an **Icons…** button opens a searchable picker with bundled glyph sets
  (media, volume, brightness, web, system), your installed browsers' real icons (Firefox, Chrome,
  Chromium, Edge, Vivaldi, Brave), and — when Font Awesome is installed — large *Font Awesome* and
  *Font Awesome Brands* categories. Icons come in white and colourised variants, with an optional
  colour tint, and there are separate **Stream Deck brightness** and **screen brightness** icons so
  the two are easy to tell apart.
* **Media & brightness key presets** — a **Media…** menu next to *Press Keys* inserts ready-made
  multimedia and brightness key actions (volume, play/pause, next/previous, brightness up/down).
* **Page navigation keys** — one-click **◀ Prev Page** / **Next Page ▶** buttons turn a key into a
  relative page switch (with wrap-around) and apply a premade arrow icon.
* **Per-page application binding** — bind a page to an application (via the page's gear button) and
  it is shown automatically whenever that app is focused; focusing an app with no page returns the
  deck to the last page you chose yourself. The bound app is shown in the page tab. Detection works
  on X11, Sway and Hyprland (and KDE with `kdotool`); compositors that don't expose the focused
  window (e.g. GNOME Wayland) simply leave it inactive.
* **Dark mode** — a dark interface theme under **View → Dark Mode**, remembered between sessions.
* **Background daemon** — run detached with `streamdeck --daemon` (no window needed); stop with
  `streamdeck --daemon-kill` and check with `streamdeck --daemon-status`.
* **Installer** — `scripts/install.sh` sets everything up into an isolated virtual environment,
  with shell completions (fish/bash/zsh) and an optional autostart service.

## Core features

* **Linux compatible** — supports Stream Deck Original, MK2, Mini, XL and the Pedal.
* **Multi-device** — connect and configure several Stream Decks at once.
* **Per-key actions** — run commands, type text, press hotkeys, change brightness, switch page or
  button state — combine several on one key.
* **Configurable display** — icon and/or text per key, fonts, colours and alignment; animated GIFs
  are supported.
* **Pages & button states** — multiple pages and multiple states per button.
* **Brightness control, auto-dim, import/export, drag-and-drop, auto-reconnect** and running as a
  `systemd --user` service.

## Installation

The quickest way to install this fork from source is the bundled script:

```bash
git clone https://github.com/KsmBl/streamdeck-linux-gui-KsmBl.git
cd streamdeck-linux-gui-KsmBl
scripts/install.sh            # add --enable-service to start in the background on login
```

It installs the udev rules, builds an isolated virtual environment, links the `streamdeck` and
`streamdeckc` commands into `~/.local/bin`, adds an application launcher and installs shell
completions for the shells you have. Remove everything again with `scripts/uninstall.sh`
(`--purge` also deletes your configuration).

Distribution-specific notes from upstream still apply — see the
[installation guides](docs/installation) (Arch/Manjaro, CentOS, Fedora, NixOS, openSUSE,
Ubuntu/Mint) and the original [documentation site](https://streamdeck-linux-gui.github.io/streamdeck-linux-gui/).
The [`ubuntu_install.sh`](scripts/ubuntu_install.sh) and [`fedora_install.sh`](scripts/fedora_install.sh)
scripts install the upstream PyPI release instead of this checkout.

After installation, run `streamdeck` (or launch *Stream Deck UI* from your application menu).

## Known issues

* Key presses and text are simulated with [evdev](https://python-evdev.readthedocs.io/) via
  `uinput`. If **Press Keys** or **Write Text** do nothing, check your `uinput` permissions and the
  udev setup from the installation guides (the installer adds you to the `input` group).
* The Stream Deck draws a fair amount of power and has strict bandwidth needs — if it isn't
  detected, try a different USB port.
* When running a shell script from a **Command**, include the appropriate shebang
  (`#!/bin/bash`, `#!/usr/bin/python3`, …) or the deck may appear to hang on some distributions.

## Contributing & credits

Communication with the device is powered by the
[Python Elgato Stream Deck library](https://github.com/abcminiuser/python-elgato-streamdeck).
This fork builds on [streamdeck-linux-gui](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)
and the original [streamdeck_ui](https://github.com/timothycrosley/streamdeck-ui) — thanks to
everyone who has contributed to them. The project is MIT licensed (see [LICENSE](LICENSE)).

A German version of this README is available in [README-de.md](README-de.md).
