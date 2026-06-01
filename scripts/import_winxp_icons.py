#!/usr/bin/env python3
"""Slice the bundled Windows XP icon-map sheets into individual sample icons.

The source artwork lives in ``WinXp/`` at the repository root:

* ``Icons/WinIcons_16.png``, ``WinIcons_32.png``, ``WinIcons_48.png`` are tightly
  packed grids of 16/32/48-pixel icons on a transparent background. Each is
  sliced cell-by-cell; fully transparent cells are skipped.
* ``Logo/WindowsLogo-small.png`` is a single small logo, imported as one icon.

Every extracted icon is scaled up by the largest integer factor that fits and
centred on a 256x256 transparent canvas (nearest-neighbour, so the pixels stay
crisp), matching the size of the other bundled sample icons.

Run from the repository root:

    python scripts/import_winxp_icons.py
"""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "WinXp")
SAMPLES_DIR = os.path.join(ROOT, "streamdeck_ui", "icons", "samples")
OUT = 256
ALPHA_THRESHOLD = 16  # a cell with no pixel above this alpha is treated as empty

# Source sheet -> (cell size in px, destination category directory).
SHEETS = {
    os.path.join(SRC_DIR, "Icons", "WinIcons_16.png"): (16, "windows_xp_16"),
    os.path.join(SRC_DIR, "Icons", "WinIcons_32.png"): (32, "windows_xp_32"),
    os.path.join(SRC_DIR, "Icons", "WinIcons_48.png"): (48, "windows_xp_48"),
}


def _is_empty(cell: Image.Image) -> bool:
    """Returns True when the cell has no meaningfully opaque pixel."""
    alpha = cell.getchannel("A")
    return alpha.getextrema()[1] <= ALPHA_THRESHOLD


def _to_canvas(cell: Image.Image, cell_size: int) -> Image.Image:
    """Scales a cell up by an integer factor and centres it on a 256 canvas."""
    factor = max(1, OUT // cell_size)
    scaled = cell.resize((cell_size * factor, cell_size * factor), Image.NEAREST)
    canvas = Image.new("RGBA", (OUT, OUT), (0, 0, 0, 0))
    offset = ((OUT - scaled.width) // 2, (OUT - scaled.height) // 2)
    canvas.alpha_composite(scaled, offset)
    return canvas


def _slice_sheet(path: str, cell_size: int, category: str) -> int:
    sheet = Image.open(path).convert("RGBA")
    width, height = sheet.size
    cols, rows = width // cell_size, height // cell_size

    out_dir = os.path.join(SAMPLES_DIR, category)
    os.makedirs(out_dir, exist_ok=True)

    count = 0
    for row in range(rows):
        for col in range(cols):
            box = (col * cell_size, row * cell_size, (col + 1) * cell_size, (row + 1) * cell_size)
            cell = sheet.crop(box)
            if _is_empty(cell):
                continue
            count += 1
            _to_canvas(cell, cell_size).save(os.path.join(out_dir, f"icon_{count:03d}.png"))
    return count


def _import_logo() -> None:
    logo_path = os.path.join(SRC_DIR, "Logo", "WindowsLogo-small.png")
    if not os.path.isfile(logo_path):
        return
    logo = Image.open(logo_path).convert("RGBA")
    factor = max(1, OUT // max(logo.size))
    scaled = logo.resize((logo.width * factor, logo.height * factor), Image.NEAREST)
    canvas = Image.new("RGBA", (OUT, OUT), (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((OUT - scaled.width) // 2, (OUT - scaled.height) // 2))
    out_dir = os.path.join(SAMPLES_DIR, "windows_xp_48")
    os.makedirs(out_dir, exist_ok=True)
    canvas.save(os.path.join(out_dir, "windows_logo.png"))


def main() -> None:
    total = 0
    for path, (cell_size, category) in SHEETS.items():
        n = _slice_sheet(path, cell_size, category)
        total += n
        print(f"{os.path.basename(path)} -> {category}: {n} icons")
    _import_logo()
    print(f"Imported {total} icons (+ logo).")


if __name__ == "__main__":
    main()
