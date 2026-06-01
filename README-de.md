# Stream Deck UI für Linux — erweiterter Fork

Eine Desktop-Anwendung, um ein Elgato Stream Deck unter Linux einzurichten und zu steuern.

Dies ist ein persönlicher Fork von [streamdeck-linux-gui](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)
(der Community-Fortführung des ursprünglichen
[streamdeck_ui](https://github.com/timothycrosley/streamdeck-ui)). Er enthält alles, was das
Upstream-Projekt kann, und ergänzt einige praktische Komfortfunktionen. Upstream befindet sich im
reinen Wartungsmodus und nimmt keine neuen Funktionen mehr an, daher leben diese Ergänzungen hier.
Der Dank für die ursprüngliche Arbeit gebührt deren Autorinnen, Autoren und Mitwirkenden.

## Was dieser Fork ergänzt

* **Anwendungsauswahl** — eine Schaltfläche **App…** neben *Command* listet Ihre installierten
  Programme (aus deren Desktop-Einträgen) auf; wählen Sie eines aus, und der Startbefehl sowie ein
  passendes Icon werden automatisch gesetzt.
* **Icon-Bibliothek** — eine Schaltfläche **Icons…** öffnet eine durchsuchbare Auswahl mit
  mitgelieferten Symbolsätzen (Medien, Lautstärke, Helligkeit, Web, System), großen **Windows-XP**-
  Icon-Sätzen in den Größen 16/32/48 Pixel (Hunderte klassischer System-, Dateityp- und
  Geräte-Icons), den echten Icons Ihrer installierten Browser (Firefox, Chrome, Chromium, Edge,
  Vivaldi, Brave) und — falls Font Awesome installiert ist — den großen Kategorien *Font Awesome*
  und *Font Awesome Brands*. Icons gibt es in Weiß und in farbigen Varianten samt optionaler
  Einfärbung; getrennte Symbole für **Stream-Deck-Helligkeit** und **Bildschirmhelligkeit** machen
  beide leicht unterscheidbar.
* **Medien- & Helligkeitstasten** — ein **Media…**-Menü neben *Press Keys* fügt fertige Multimedia-
  und Helligkeitstasten ein (Lautstärke, Wiedergabe/Pause, vor/zurück, Helligkeit hoch/runter).
* **Live-Info-Tasten** — ein **Live info**-Auswahlfeld lässt eine Taste statt statischem Text einen
  sich jede Sekunde aktualisierenden Wert anzeigen: Uhr, Datum, CPU- oder Speicherauslastung, Akku
  oder Netzwerkdurchsatz (alles direkt aus dem Kernel gelesen, ohne zusätzliche Abhängigkeiten).
* **Umschalt-/Zyklustasten** — aktivieren Sie **Cycle states on press**, und jeder Tastendruck
  schaltet die Taste zum nächsten Zustand weiter (mit Umlauf) — so wird eine Taste mit mehreren
  Zuständen zu einem Umschalter wie Stumm/Laut oder An/Aus.
* **Seiten-Navigationstasten** — die Schaltflächen **◀ Prev Page** / **Next Page ▶** machen aus
  einer Taste mit einem Klick eine relative Seitenumschaltung (mit Umlauf) und setzen ein
  vorgefertigtes Pfeil-Icon.
* **Anwendung pro Seite** — binden Sie eine Seite an ein Programm (über das Zahnrad der Seite); sie
  wird automatisch angezeigt, sobald dieses Programm den Fokus hat. Wird ein Programm ohne eigene
  Seite fokussiert, kehrt das Deck zur zuletzt selbst gewählten Seite zurück. Das gebundene Programm
  steht im Seitenreiter. Die Erkennung funktioniert unter X11, Sway und Hyprland (sowie KDE mit
  `kdotool`); Compositoren, die das fokussierte Fenster nicht preisgeben (z. B. GNOME Wayland),
  lassen die Funktion einfach inaktiv.
* **Designs** — wählen Sie unter **View** ein Basis-Design: das **Default**-Design (Plattformlook),
  ein nostalgisches **Windows-XP**-Design (Luna) oder ein elegantes **Modern**-Design mit flachen,
  abgerundeten Bedienelementen und einem Indigo-Akzent (die Akzentfarbe ist über **View → Modern
  Accent Colour…** anpassbar). **Dark Mode** ist ein separater Schalter, der über jedem Design liegt,
  sodass jedes Design hell oder dunkel sein kann. Alle Einstellungen werden zwischen Sitzungen
  gemerkt.
* **Hintergrund-Daemon** — mit `streamdeck --daemon` losgelöst starten (ohne Fenster), mit
  `streamdeck --daemon-kill` beenden und mit `streamdeck --daemon-status` prüfen.
* **Installationsskript** — `scripts/install.sh` richtet alles in einer isolierten virtuellen
  Umgebung ein, inklusive Shell-Vervollständigungen (fish/bash/zsh) und optionalem Autostart-Dienst.

## Kernfunktionen

* **Linux-kompatibel** — unterstützt Stream Deck Original, MK2, Mini, XL und das Pedal.
* **Mehrere Geräte** — mehrere Stream Decks gleichzeitig verbinden und konfigurieren.
* **Aktionen pro Taste** — Befehle ausführen, Text schreiben, Tastenkürzel senden, Helligkeit
  ändern, Seite oder Tastenzustand wechseln — mehreres auf einer Taste kombinierbar.
* **Konfigurierbare Anzeige** — Icon und/oder Text pro Taste, Schriftarten, Farben und Ausrichtung;
  animierte GIFs werden unterstützt.
* **Seiten & Tastenzustände** — mehrere Seiten und mehrere Zustände pro Taste.
* **Helligkeitssteuerung, automatisches Abdunkeln, Import/Export, Drag & Drop, automatisches
  Wiederverbinden** sowie Betrieb als `systemd --user`-Dienst.

## Installation

Am schnellsten installieren Sie diesen Fork aus dem Quellcode mit dem mitgelieferten Skript:

```bash
git clone https://github.com/KsmBl/streamdeck-linux-gui-KsmBl.git
cd streamdeck-linux-gui-KsmBl
scripts/install.sh            # mit --enable-service im Hintergrund beim Anmelden starten
```

Es installiert die udev-Regeln, baut eine isolierte virtuelle Umgebung, verknüpft die Befehle
`streamdeck` und `streamdeckc` nach `~/.local/bin`, legt einen Anwendungsstarter an und installiert
Shell-Vervollständigungen für die vorhandenen Shells. Mit `scripts/uninstall.sh` wird alles wieder
entfernt (`--purge` löscht zusätzlich Ihre Konfiguration).

Die distributionsspezifischen Hinweise von Upstream gelten weiterhin — siehe die
[Installationsanleitungen](docs/installation) (Arch/Manjaro, CentOS, Fedora, NixOS, openSUSE,
Ubuntu/Mint) und die ursprüngliche [Dokumentationsseite](https://streamdeck-linux-gui.github.io/streamdeck-linux-gui/).
Die Skripte [`ubuntu_install.sh`](scripts/ubuntu_install.sh) und [`fedora_install.sh`](scripts/fedora_install.sh)
installieren stattdessen die Upstream-Version von PyPI.

Nach der Installation starten Sie `streamdeck` (oder *Stream Deck UI* aus Ihrem Anwendungsmenü).

## Bekannte Probleme

* Tastendrücke und Texteingaben werden mit [evdev](https://python-evdev.readthedocs.io/) über
  `uinput` simuliert. Wenn **Press Keys** oder **Write Text** nichts bewirken, prüfen Sie die
  `uinput`-Berechtigungen und das udev-Setup aus den Installationsanleitungen (das Skript fügt Sie
  der Gruppe `input` hinzu).
* Das Stream Deck benötigt einiges an Strom und hat strenge Bandbreitenanforderungen — wird es nicht
  erkannt, probieren Sie einen anderen USB-Anschluss.
* Wenn Sie über eine **Command**-Aktion ein Shell-Skript ausführen, geben Sie die passende Shebang-
  Zeile an (`#!/bin/bash`, `#!/usr/bin/python3`, …), sonst kann das Deck auf manchen Distributionen
  scheinbar hängen bleiben.

## Mitwirken & Danksagung

Die Kommunikation mit dem Gerät erfolgt über die
[Python-Elgato-Stream-Deck-Bibliothek](https://github.com/abcminiuser/python-elgato-streamdeck).
Dieser Fork baut auf [streamdeck-linux-gui](https://github.com/streamdeck-linux-gui/streamdeck-linux-gui)
und dem ursprünglichen [streamdeck_ui](https://github.com/timothycrosley/streamdeck-ui) auf — Dank an
alle, die dazu beigetragen haben. Das Projekt steht unter der MIT-Lizenz (siehe [LICENSE](LICENSE)).
