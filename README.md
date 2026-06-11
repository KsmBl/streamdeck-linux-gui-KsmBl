# Stream Deck UI for Linux — enhanced fork

A desktop app to configure and drive an Elgato Stream Deck on Linux.

This is a personal fork of [streamdeck-linux-gui](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)
(itself the community continuation of the original
[streamdeck_ui](https://github.com/timothycrosley/streamdeck-ui)). It keeps everything the
upstream project does and adds a set of quality-of-life features on top. Upstream is in
maintenance mode and is not taking new features, so those additions live here instead. All
credit for the original work goes to its authors and contributors.

## What this fork adds

* **Application launcher picker** — an **App…** button next to *Command* lists your installed
  applications (from their desktop entries); pick one to fill in the launch command and a fitting
  icon automatically.
* **Icon library** — an **Icons…** button opens a searchable picker with bundled glyph sets
  (media, volume, brightness, web, system), large **Windows XP** icon sets at 16/32/48-pixel sizes
  (hundreds of classic system, file-type and device icons), your installed browsers' real icons
  (Firefox, Chrome, Chromium, Edge, Vivaldi, Brave), the *complete* *Font Awesome* and *Font Awesome
  Brands* sets (bundled, so they always work even when Font Awesome is not installed system wide) and —
  when a *Nerd Font* is installed — every *Nerd Font* glyph as well (thousands of icons, rendered
  straight from the fonts). Icons come in white and colourised variants, with an optional colour tint
  and a soft drop shadow in the picker so light icons stay visible on light backgrounds; separate
  **Stream Deck brightness** and **screen brightness** icons make the two easy to tell apart.
* **Media & brightness key presets** — a **Media…** menu next to *Press Keys* inserts ready-made
  multimedia and brightness key actions (volume, play/pause, next/previous, brightness up/down).
* **Live info buttons** — a **Live info** dropdown makes a key show a value that updates every
  second instead of static text: clock, date, CPU usage, CPU temperature, memory usage, battery, or
  network throughput (all read straight from the kernel, no extra dependencies).
* **Toggle / cycle keys** — tick **Cycle states on press** and each press advances the key to its
  next state (wrapping), turning a multi-state key into a toggle such as mute/unmute or on/off.
* **Page navigation keys** — one-click **◀ Prev Page** / **Next Page ▶** buttons turn a key into a
  relative page switch (with wrap-around) and apply a premade arrow icon; **Go to Auto** / **Leave
  Auto** buttons turn a key into one that enters or leaves the Auto group (see below).
* **Application control presets** — a **Controls…** button above the pages fills the current page in
  one click with a ready-made control surface for ~40 applications: browsers (**Firefox**, **Vivaldi**,
  **Chromium**, **Chrome**, **Brave**, **LibreWolf**, **Zen**), file managers (**Thunar**, **Dolphin**,
  **Nautilus**, **Nemo**, **PCManFM**), terminals (**Xfce Terminal**, **Konsole**, **GNOME Terminal**,
  **kitty**), editors/IDEs (**Vim**, **VS Code**, **Sublime Text**, **Obsidian**, **Gittyup**), creative
  apps (**GIMP**, **Krita**, **Inkscape**, **Blender**, **Kdenlive**), documents (**LibreOffice Writer/
  Calc**, **Okular**, **Zathura**), chat (**Discord**, **Slack**, **Telegram**, **Element**,
  **Thunderbird**), media (**VLC**, **Spotify**, **mpv**, **Audacious**, generic **media player**) and
  **TETR.IO**. Each preset lays out labelled, icon-bearing keys (New Tab, Back,
  Reload, Save, …) that drive the app through its keyboard shortcuts (or the global media keys); the
  matching Font Awesome icons are applied automatically (the font is bundled). Application shortcuts
  act on whichever window is focused, so pair a preset with an **Auto page** to switch to it
  automatically.
* **Auto pages** — an **Auto** tab collects a set of per-application pages that the deck follows
  automatically. It comes ready to use: on first run it is **pre-populated with a Home dashboard plus
  one page per control preset, each bound to its application** (Firefox, Vivaldi, Thunar, GIMP, …).
  Each auto page is shown the moment its app is focused — but only while the deck is *in* the Auto
  group, so the deck follows your focus only when you want it to. When the focused app has no preset —
  or nothing is focused at all — the deck falls back to the **Home** page: a live dashboard with CPU
  temperature, CPU and memory usage, network speed, a clock and a Leave Auto key (centred tiles that
  use a font with the up/down network arrows when one is available). Use a **Go to Auto** key to enter the group and a **Leave Auto**
  key to return to your normal pages (the **◀ Prev** / **Next ▶** page keys stay on your normal pages
  and never wander into the auto pages). From the Auto tab you can add an application (seeded with a
  control preset), change which application a page follows (with a **Detect application** button that
  waits five seconds so you can focus the target window first), edit each page's buttons in place,
  define an **overlay** — a layer whose keys are drawn on top of *every* auto page, perfect for a
  shared "Leave Auto" or media row — and **Reset to defaults** to wipe the group and restore the
  default presets. Detection works on X11, Sway and Hyprland (and KDE with `kdotool`);
  compositors that don't expose the focused window (e.g. GNOME Wayland) simply leave it inactive.
* **Snake mini-game** — a **🐍 Snake** tab with a playfield and direction controls (and a restart) down
  the right-hand side; play with the on-screen controls or the arrow / WASD keys.
* **Themes** — pick a base look under **View**: the **Default** (platform) theme, a nostalgic
  **Windows XP** (Luna) theme, or a sleek **Modern** theme with flat rounded controls and an indigo
  accent (the accent colour is customisable via **View → Modern Accent Colour…**). **Dark Mode** is a
  separate toggle layered on top, so any theme can be light or dark. All choices are remembered
  between sessions.
* **Background daemon** — run detached with `streamdeck --daemon` (no window needed); stop with
  `streamdeck --daemon-kill` and check with `streamdeck --daemon-status`.
* **Terminal (text) UI** — for machines with no graphical desktop (a headless server, an SSH
  session or a bare TTY), run `streamdeck-tui` (or `streamdeck --tui`). It is built on the standard
  library `curses`, so it needs no extra dependency, and it drives the deck for real: button
  presses run their commands, switch pages and update live tiles. The keys are drawn as a colourful
  grid of tiles — **colour-coded by action** (commands green, hotkeys blue, typed text amber, page
  switches magenta, live tiles cyan) with a glyph and label — alongside a header showing the deck,
  page dots and a brightness gauge, and a detail panel for the selected key. Move the selection with
  the arrow keys (or `hjkl`), change page with `[` / `]`, switch deck with `Tab`, adjust brightness
  with `+` / `-`, add/remove pages with `a` / `d`, press `Enter` to edit the selected key (text,
  command, keys, write, switch-page, brightness and live source), `?` for help and `q` to quit. It
  shares the single-instance lock with the GUI, so run one or the other.
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

It installs the udev rules, builds an isolated virtual environment, links the `streamdeck`,
`streamdeck-tui` and `streamdeckc` commands into `~/.local/bin`, adds an application launcher and installs shell
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
everyone who has contributed to them. The bundled [Font Awesome Free](https://fontawesome.com)
fonts in `streamdeck_ui/fonts/fontawesome` are used under the SIL Open Font License 1.1 (see the
licence file alongside them). The project is MIT licensed (see [LICENSE](LICENSE)).

A German version of this README is available in [README-de.md](README-de.md).
