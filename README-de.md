[![streamdeck_ui - Linux kompatibles UI für das Elgato Stream Deck](art/logo_large.png)](https://timothycrosley.github.io/streamdeck-ui/)
_________________

[![PyPI version](https://badge.fury.io/py/streamdeck-ui.svg)](http://badge.fury.io/py/streamdeck-ui)
[![Test Status](https://github.com/timothycrosley/streamdeck-ui/workflows/Test/badge.svg?branch=master)](https://github.com/timothycrosley/streamdeck-ui/actions?query=workflow%3ATest)
[![codecov](https://codecov.io/gh/timothycrosley/streamdeck-ui/branch/master/graph/badge.svg)](https://codecov.io/gh/timothycrosley/streamdeck-ui)
[![Join the chat at https://gitter.im/timothycrosley/streamdeck-ui](https://badges.gitter.im/timothycrosley/streamdeck-ui.svg)](https://gitter.im/timothycrosley/streamdeck-ui?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/streamdeck-ui/)
[![Downloads](https://pepy.tech/badge/streamdeck-ui)](https://pepy.tech/project/streamdeck-ui)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://timothycrosley.github.io/isort/)

_________________

[Lese die neueste Dokumentation](https://timothycrosley.github.io/streamdeck-ui/)
[Release notes](CHANGELOG.md)
_________________

> WARNUNG: Diese Dokumentation ist veraltet und möglicherweise nicht korrekt.

**streamdeck_ui** Ein Linux kompatibles UserInterface für das Elgato Stream Deck.

![Streamdeck UI Usage Example](art/example.gif)

## Eigenschaften

* **Linux Kompatibel**: Ermöglicht die Nutzung aller Stream Deck Geräte mit Linux ohne code zu benötigen.
* **Mehrere Geräte**: Ermöglicht die Verbindung und Konfiguration mehrere Stream Deck Geräte an einem Computer.
* **Helligkeits-Steuerung**: Unterstützt die Einstellung der Helligkeit von der Konfigurations-Oberfläche und den Knöpfen am Gerät selbst.
* **Konfigurierbares Tastenbild**: Icon + Text, nur Icon und nur Text sind pro Taste des Stream Decks konfigurierbar.
* **Multi-Action Unterstützung**: Kommandos starten, Text schreiben und Hotkey-Kombinationen drücken mit einem einzigen Tastendruck auf dem Stream Deck.
* **Medien- & Helligkeitstasten**: Ein **Media…**-Menü neben *Press Keys* fügt fertige Multimedia- und Helligkeitstasten-Aktionen ein (Lautstärke, Wiedergabe/Pause, vor/zurück, Helligkeit hoch/runter).
* **Installierte Programme starten**: Klicken Sie neben dem Befehlsfeld auf **App…**, um aus einer durchsuchbaren Liste ein installiertes Programm auszuwählen. Der Startbefehl wird automatisch eingetragen und ein passendes Icon (aus Ihrem Icon-Thema) der Taste zugewiesen.
* **Dunkles Design**: Schalten Sie über **View → Dark Mode** ein dunkles Oberflächendesign ein. Ihre Auswahl wird zwischen Sitzungen gespeichert.
* **Anwendung pro Seite**: Eine Seite kann automatisch angezeigt werden, wenn eine bestimmte Anwendung fokussiert ist – so kann sie Aktionen für das gerade genutzte Programm bereitstellen. Öffnen Sie die Seiteneinstellungen (das Zahnrad über den Seiten) und legen Sie die Anwendung fest – wählen Sie ein laufendes Programm aus der Liste oder geben Sie dessen Kennung ein. Die Funktion ist aktiv, sobald einer Seite eine Anwendung zugewiesen ist. Die Erkennung funktioniert unter X11, Sway und Hyprland (sowie KDE mit `kdotool`); manche Wayland-Compositoren wie GNOME geben das fokussierte Fenster nicht preis, dort bleibt die Funktion inaktiv.
* **Seiten-Navigationstasten**: Neben *Switch Page* verwandeln die Tasten **◀ Prev Page** / **Next Page ▶** die ausgewählte Taste in eine relative Seitennavigationstaste (mit Umlauf) und weisen automatisch ein vorgefertigtes Pfeil-Icon zu.
* **Beispiel-Icons**: Über die Schaltfläche **Icons…** stehen fertige Tastenbilder bereit: mitgelieferte Sätze (Medien, Lautstärke, Helligkeit, Web, System); die echten, farbigen Icons Ihrer installierten Browser (Firefox, Chrome, Chromium, Edge, Vivaldi, Brave), ersatzweise eingefärbte Font-Awesome-Markensymbole; und – falls Font Awesome installiert ist – große Kategorien *Font Awesome* (Free Solid) und *Font Awesome Brands*. Der Dialog bietet eine Suche und eine optionale Einfärbung für einfarbige Icons. Browser- und Font-Awesome-Icons werden aus den bereits auf Ihrem System vorhandenen Schriften/Themen erzeugt.
* **Tasten-Seiten**: streamdeck_ui bietet mehrere Seiten von Tasten mit dynamischer Einstellung von Tasten zum Umschalten zwischen ihnen.
* **Automatisches Wiederverbinden**: Das Gerät wird automatisch und problemlos wieder verbunden, falls das Gerät ab- und wieder angesteckt wurde.
* **Import/Export**: Bietet das Abspeichern und Wiederherstellen ganzer Stream Deck Konfigurationen.
* **Hintergrund-Daemon**: Mit `streamdeck --daemon` (oder `-d`) löst sich das Programm vom Terminal und das Stream Deck funktioniert weiter, ohne dass das Konfigurationsfenster geöffnet bleiben muss. Beenden mit `streamdeck --daemon-kill`, Status prüfen mit `streamdeck --daemon-status`.
* **Läuft unter systemd**: Läuft automatisch im Hintergrund als systemd --user Service.

Die Kommunikation mit dem Streamdeck erfolgt durch die [Python Elgato Stream Deck Library](https://github.com/abcminiuser/python-elgato-streamdeck#python-elgato-stream-deck-library).

## Linux Schnellstart

**Python 3.10** wird benötigt. Sie können die Version, die sie installiert haben, überprüfen mit `python3 --version`.

### Vorgefertigte Skripte

Es gibt fertige Skripte um streamdeck_ui auf [Debian/Ubuntu](scripts/ubuntu_install.sh) und [Fedora](scripts/fedora_install.sh) zu installieren.

Um **dieses Quellverzeichnis** (distributionsunabhängig) zu installieren, führen Sie [`scripts/install.sh`](scripts/install.sh) aus. Das Skript installiert die udev-Regeln, richtet eine eigene virtuelle Umgebung ein, verknüpft die Befehle `streamdeck`/`streamdeckc` nach `~/.local/bin`, legt einen Anwendungsstarter an und installiert Shell-Vervollständigungen für fish, bash und zsh (für die installierten Shells). Mit `--enable-service` wird zusätzlich ein systemd-`--user`-Service installiert und aktiviert, der das Stream Deck beim Anmelden im Hintergrund startet. Mit [`scripts/uninstall.sh`](scripts/uninstall.sh) wird alles wieder entfernt (mit `--purge` wird auch Ihre Konfiguration gelöscht).

### Manuelle Installation

Um streamdeck_ui unter Linux zu verwenden, müssen einige System-Bibliotheken als Voraussetzung installiert werden.
Die Namen dieser Bibliotheken können, abhängig von ihrem Betriebssystem, variieren.  
Debian / Ubuntu:

```bash
sudo apt install python3-pip libhidapi-libusb0 libxcb-xinerama0
```

Fedora:

```bash
sudo dnf install python3-pip python3-devel hidapi
```

Wenn sie die GNOME shell verwenden, könnten sie eine Erweiterung, die den [KStatusNotifierItem/AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/) bietet, manuell installieren müssen um das Tray-Icon anzuzeigen.

Um streamdeck_ui ohne root-Rechte zu benutzen, müssen sie ihrem user vollen Zugriff auf das Gerät erlauben.

Fügen sie die folgenden udev rules mit Hilfe ihres Editors hinzu:

```bash
sudoedit /etc/udev/rules.d/70-streamdeck.rules
# Wenn das nicht funktioniert, versuchen sie:
sudo nano /etc/udev/rules.d/70-streamdeck.rules
```

Fügen sie die folgenden Zeilen ein:

```ini
SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", TAG+="uaccess"
```

Aktivieren sie die Regeln:

```bash
sudo udevadm trigger
```

Die Installation der Anwendung selbst erfolgt via pip:

```bash
pip3 install streamdeck-ui --user
```

Stellen sie sicher, dass `$HOME/.local/bin` in ihrem PATH enthalten ist.  
Wenn das nicht der Fall ist, fügen sie

```ini
PATH=$PATH:$HOME/.local/bin
```

an das Ende ihrer shell Konfigurationsdatei (wahrscheinlich .bashrc in ihrem home directory) hinzu.

Jetzt können sie `streamdeck` starten um mit der Konfiguration zu beginnen.

```bash
streamdeck
```

Es wird empfohlen `streamdeck` in die Autostart-Liste ihrer Fenster-Umgebung aufzunehmen. Wenn sie es verwenden wollen ohne dass das Benutzer-Interface angezeigt wird, verwenden sie`streamdeck -n`.

## Allgemeiner Schnellstart

Auf anderen Betriebssystemen müssen sie die benötigten [Abhängigkeiten](https://github.com/abcminiuser/python-elgato-streamdeck#package-dependencies) der Bibliothek installieren.
Danach verwenden sie pip zur Installation der Anwendung:

```bash
pip3 install streamdeck-ui --user
streamdeck
```

Beachten sie auch die Anleitungen für

* [Arch/Manjaro](docs/installation/arch.md)
* [CentOS](docs/installation/centos.md)
* [Fedora](docs/installation/fedora.md)
* [NixOS](docs/installation/nixos.md)
* [openSUSE](docs/installation/opensuse.md)
* [Ubuntu/Mint](docs/installation/ubuntu.md)

## Hilfe

### Befehl (Command)

Geben sie einen Befehl in das Feld "Command" ein, um ihn auszuführen. In Ubuntu/Fedora starten sie ein Terminal mit `gnome-terminal`, `obs` startet OBS.

#### Beispiele (Ubuntu)

Sie können ein tool wie `xdotool` verwenden, um mit anderen Programmen zu interagieren.

Finden sie das Fenster, das mit `Meet -` beginnt, und setzen sie den Fokus darauf. Das hilft ihnen, wenn sie eine Google Meet Sitzung auf irgend einem Tab haben, die aber hinter anderen Fenstern verloren gegangen ist.

```bash
xdotool search --name '^Meet - .+$' windowactivate 
```

> Der Meeting-Tab muss aktiv sein wenn sie mehrere Tabs offen haben, da der Fenstertitel vom derzeit aktiven Tab gesetzt wird.

Finden sie das Fenster, das mit `Meet -` beginnt, und senden sie `ctrl+d` dorthin. Das bewirkt das Umschalten der Stummschaltung (mute button) in Google Meet.

```bash
xdotool search --name '^Meet - .+$' windowactivate --sync key ctrl+d
```

Drehen sie die System-Lautstärke um einen gewissen Prozentsatz hoch (oder runter). Wir nehmen an, sie verwenden PulseAudio/Alsa Mixer.

```bash
amixer -D pulse sset Master 20%+
```

Wenn sie einen Befehl abgeben wollen der shell-script spezifische Dinge wie `&&` oder `|` enthält, dann starten sie ihn via bash. Dieser Befehl wird de Fokus auf Firefox setzen, indem es `wmctrl` nutzt, und dann den Fokus auf den ersten Tab verschieben:

```bash
bash -c "wmctrl -a firefox  && xdotool key alt+1"
```

### Tasten drücken

Simuliert Tasten-Kombinationen (hot keys). Grundsätzlich werden Tasten, die gleichzeitig betätigt werden, mit einem `+` Zeichen verbunden. Trennen sie Tasten-Kombinationen mit einem `,` , wenn zusätzliche Kombinationen benötigt werden. Die Zeichenfolge `alt+F4,f` zum Beispiel bedeutet drücke und halte `alt`, gefolgt von `F4` und lass dann beide los. Drücke anschließend `f` und lass es wieder los.

Verwenden sie Tasten-Namen direkt (zum Beispiel `t`, `capslock` oder `numpad_divide`).
Hex-Keysyms aus Tools wie `xev` (zum Beispiel `0x74`, `0xffe5`, `0xffaf`) werden vom `evdev` Backend nicht unterstützt.

> Sie können das Tool `evtest` verwenden, um das Verhalten einer Taste zu prüfen und auf einen `evdev` Tasten-Namen zuzuordnen.
>
> Verwenden sie `comma` oder `plus`, wenn sie ein `,` oder ein `+` *ausgeben* wollen.
>
> Verwenden sie `delay <n>` um eine Verzögerung einzufügen, wobei `<n>` die Anzahl (float oder integer) der Sekunden ist. Wenn `<n>` nicht angegeben wird, wird eine Standardverzögerung von 0.5 Sekundenverwendet. Wenn `<n>` nicht als gültige Zahl erkannt wird, erfolgt keine Verzögerung.
>

#### Beispiele

* `F11` - drückt F11. Wenn der Fokus auf einem Browser ist, schaltet das zwischen Vollbild und Normalbild hin und her.
* `alt+F4` - schließt das aktuelle Fenster.
* `ctrl+w` - schließt den aktuellen Browser-Tab.
* `cmd+left` - verkleinert das Fenster auf seine linke Hälfte. Achtung, `cmd` ist die **super** Taste (entsprechend der Windows Taste).
* `alt+plus` - drückt die  alt und die `+` Taste gleichzeitin.
* `alt+delay+F4` - drücke alt, warte dann 0.5 Sekunden, drücke dann F4. Lass beide Tasten los.
* `1,delay,delay,2,delay,delay,3` - tippe 123 mit 1-Sekunden Pausen zwischen den Tastendrucken (unter Verwendung der Standardpausen).
* `1,delay 1,2,delay 1,3` - tippe 123 mit 1-Sekunden Pausen zwischen den Tastendrucken (unter Verwendung selbst definierter Pausen).
* `e,c,h,o,space,",t,e,s,t,",enter` - tippe `echo "test"` und drücke Enter.
* `ctrl+alt+t` - öffnet in vielen Desktop-Umgebungen ein neues Terminalfenster.
* `capslock` - Caps Lock umschalten.
* `numpad_divide` - Die `/` Taste im Ziffernblock der Tastatur.

Die unterstützten Tasten-Namen stammen aus den `evdev` Tasten plus Aliasen in `streamdeck_ui/modules/keyboard.py`.

Die `super` Taste (Windows-Taste) kann bei einigen Linux-Versionen problematisch sein. Statt der Tastendruck-Funktion können sie dann die Befehls-Funktion wie folgt benutzen. In diesem Beispiel wollen wir die `Super` Taste und `4` drücken, was die Anwendung Nummer 4 ihrer Favoriten startet (Ubuntu).

```bash
xdotool key "Super_L+4"
```

### Text schreiben

Das ist ein schneller Weg um längere Textstücke zu schreiben (Wort für Wort). Beachten sie, dass anders als in der Tastendruck-Funtion,
hier keine Spezial-(Modifikations-)Tasten akzeptiert werden. Wenn sie jedoch Enter drücken (um eine neue Zeile zu beginnen) wird auch Enter bei der Ausgabe ausgegeben.

#### Beispiele

```console
Unfortunately that's a hard no.
Kind regards,
Joe
```

![nope](art/nope.gif)

## bekannte Probleme

Stellen sie sicher, dass sie die neueste Version verwenden mit `pip3 show streamdeck-ui`. Vergleichen sie es mit: [![PyPI version](https://badge.fury.io/py/streamdeck-ui.svg)](http://badge.fury.io/py/streamdeck-ui)

* Streamdeck verwendet [evdev](https://python-evdev.readthedocs.io/) mit `uinput` zur Simulation von **Tasten-Betätigungen** und **Text schreiben**. Wenn das nicht funktioniert, prüfen sie die `uinput`-Berechtigungen und die udev-Konfiguration aus den Installationsanleitungen.
* **Taste drücken** oder **Text schreiben** funktioniert nicht unter Fedora (außerhalb von streamdeck selbst), was nicht besonders hilfreich ist. Die **Befehls-Funktion** kann aber trotzdem eine Menge.
* Version [1.0.2](https://pypi.org/project/streamdeck-ui/) hat keine Fehler-Behandlung bei der **Befehls-** und der **Taste drücken** Funktion. Deshalb müssen sie vorsichtig sein - ein ungültiger Befehl oder Tastendruck stoppt auch alle anderen Prozesse. Bitte upgraden sie zur neuesten Version.
* Einige Anwender haben berichtet, dass das Stream Deck Gerätnicht an allen USB-ports funktioniert, da es einiges an Strom verbraucht und/oder [strenge Bandbreitenanforderungen](https://github.com/timothycrosley/streamdeck-ui/issues/69#issuecomment-715887397) hat. Versuchen sie einen anderen Anschluß.
* Wenn sie einen shell script mit der Befehls-Funktion ausführen, vergessen sie nicht das shebang für die entsprechende Sprache am Anfangihrer Datei haben. `#!/bin/bash` oder `#!/usr/bin/python3` etc. Das streamdeck könnte sich andernfalls unter einigen Distros aufhängen.
