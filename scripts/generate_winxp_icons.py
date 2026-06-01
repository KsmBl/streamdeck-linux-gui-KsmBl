#!/usr/bin/env python3
"""Generate the bundled "Windows XP" style retro icon pack.

These are *original* pixel-art icons drawn from simple primitives in the spirit
of early-2000s desktop iconography (chunky 3D bevels, a pixelated look). They
are not copies of any third party's artwork: each icon is built here from
rectangles, polygons and ellipses on a small grid and then scaled up with
nearest-neighbour sampling so the pixels stay crisp.

Run from the repository root:

    python scripts/generate_winxp_icons.py

Icons are written as 256x256 RGBA PNGs into
``streamdeck_ui/icons/samples/windows_xp/``.
"""

import math
import os

from PIL import Image, ImageDraw

GRID = 32  # logical drawing resolution
SCALE = 8  # 32 * 8 = 256 px output
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "streamdeck_ui",
    "icons",
    "samples",
    "windows_xp",
)

# --- palette -----------------------------------------------------------------
LINE = (74, 74, 74)
DARK = (40, 40, 40)
WHITE = (255, 255, 255)
PAPER = (252, 252, 250)
PAPER_EDGE = (120, 120, 120)
FOLD = (220, 220, 214)
FACE = (236, 233, 216)  # XP "Luna" control face

BLUE = (60, 120, 215)
BLUE_DK = (34, 78, 168)
BLUE_LT = (130, 178, 242)
RED = (208, 72, 40)
RED_DK = (165, 46, 26)
RED_LT = (240, 120, 92)
GREEN = (92, 176, 84)
GREEN_DK = (48, 128, 52)
GREEN_LT = (152, 214, 140)
YELLOW = (248, 204, 74)
YELLOW_DK = (224, 164, 44)
YELLOW_LT = (255, 226, 140)
GREY = (198, 198, 192)
GREY_DK = (138, 138, 132)
GREY_LT = (236, 236, 230)
SILVER = (208, 210, 214)
TEAL = (40, 168, 168)
PURPLE = (150, 92, 200)
ORANGE = (240, 150, 44)
BROWN = (150, 96, 50)


def _canvas():
    img = Image.new("RGBA", (GRID, GRID), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img, name):
    big = img.resize((GRID * SCALE, GRID * SCALE), Image.NEAREST)
    big.save(os.path.join(OUT_DIR, f"{name}.png"))


def bevel(d, box, face, light, dark):
    """Draws a 1px-bevelled filled box (top/left light, bottom/right dark)."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=face)
    d.line([(x0, y0), (x1, y0)], fill=light)
    d.line([(x0, y0), (x0, y1)], fill=light)
    d.line([(x0, y1), (x1, y1)], fill=dark)
    d.line([(x1, y0), (x1, y1)], fill=dark)


def page(d, fold_fill=FOLD):
    """Draws a document page with a folded top-right corner. Returns its box."""
    x0, y0, x1, y1, fl = 7, 2, 24, 30, 7
    body = [(x0, y0), (x1 - fl, y0), (x1, y0 + fl), (x1, y1), (x0, y1)]
    d.polygon(body, fill=PAPER, outline=PAPER_EDGE)
    d.polygon([(x1 - fl, y0), (x1 - fl, y0 + fl), (x1, y0 + fl)], fill=fold_fill, outline=PAPER_EDGE)
    return (x0, y0, x1, y1, fl)


# --- window controls ---------------------------------------------------------


def window_close(d):
    bevel(d, (4, 4, 27, 27), RED, RED_LT, RED_DK)
    for off in (-1, 0, 1):
        d.line([(11, 10 + off), (20, 19 + off)], fill=WHITE)
        d.line([(20, 10 + off), (11, 19 + off)], fill=WHITE)


def window_minimize(d):
    bevel(d, (4, 4, 27, 27), BLUE, BLUE_LT, BLUE_DK)
    d.rectangle((10, 20, 21, 22), fill=WHITE)


def window_maximize(d):
    bevel(d, (4, 4, 27, 27), BLUE, BLUE_LT, BLUE_DK)
    d.rectangle((10, 9, 21, 22), outline=WHITE)
    d.rectangle((10, 9, 21, 11), fill=WHITE)


def window_restore(d):
    bevel(d, (4, 4, 27, 27), BLUE, BLUE_LT, BLUE_DK)
    d.rectangle((13, 8, 22, 17), outline=WHITE)
    d.rectangle((13, 8, 22, 10), fill=WHITE)
    d.rectangle((9, 13, 18, 22), fill=BLUE, outline=WHITE)
    d.rectangle((9, 13, 18, 15), fill=WHITE)


# --- folders & files ---------------------------------------------------------


def folder(d):
    d.polygon([(4, 9), (12, 9), (15, 12), (27, 12), (27, 25), (4, 25)], fill=YELLOW_DK)
    bevel(d, (4, 13, 27, 25), YELLOW, YELLOW_LT, YELLOW_DK)


def folder_open(d):
    d.polygon([(4, 9), (12, 9), (15, 12), (27, 12), (27, 16), (4, 16)], fill=YELLOW_DK)
    d.polygon([(4, 16), (27, 16), (30, 26), (1, 26)], fill=YELLOW)
    d.line([(1, 26), (4, 16)], fill=YELLOW_DK)
    d.line([(30, 26), (27, 16)], fill=YELLOW_DK)
    d.polygon([(4, 16), (8, 16), (5, 26), (1, 26)], fill=YELLOW_LT)


def file_generic(d):
    page(d)


def text_file(d):
    page(d)
    widths = [13, 11, 14, 9, 13, 11]
    for i, yy in enumerate(range(9, 27, 3)):
        d.line([(10, yy), (10 + widths[i % len(widths)], yy)], fill=(110, 110, 110))


def image_file(d):
    page(d)
    d.rectangle((9, 8, 22, 27), fill=(150, 205, 245), outline=(90, 90, 90))
    d.ellipse((11, 10, 15, 14), fill=YELLOW)  # sun
    d.polygon([(9, 27), (15, 18), (19, 23), (22, 19), (22, 27)], fill=GREEN)  # hills


def video_file(d):
    bevel(d, (4, 6, 27, 26), (38, 38, 44), (80, 80, 88), (18, 18, 22))
    for yy in (8, 12, 16, 20):
        d.rectangle((5, yy, 8, yy + 2), fill=YELLOW_LT)
        d.rectangle((23, yy, 26, yy + 2), fill=YELLOW_LT)
    d.rectangle((10, 8, 21, 24), fill=(20, 20, 26))
    d.polygon([(13, 11), (13, 21), (20, 16)], fill=WHITE)  # play triangle


def audio_file(d):
    page(d)
    d.ellipse((10, 21, 15, 26), fill=BLUE_DK)
    d.ellipse((17, 18, 22, 23), fill=BLUE_DK)
    d.rectangle((14, 9, 15, 23), fill=BLUE_DK)
    d.rectangle((21, 9, 22, 20), fill=BLUE_DK)
    d.rectangle((14, 9, 22, 11), fill=BLUE_DK)  # note beam


def code_file(d):
    page(d)
    d.line([(14, 11), (10, 16), (14, 21)], fill=BLUE, joint="curve")
    d.line([(18, 11), (22, 16), (18, 21)], fill=RED, joint="curve")
    d.line([(15, 22), (17, 10)], fill=(120, 120, 120))


def pdf_file(d):
    page(d, fold_fill=(245, 200, 195))
    bevel(d, (9, 17, 22, 27), RED, RED_LT, RED_DK)
    for yy in (20, 23):
        d.line([(11, yy), (20, yy)], fill=WHITE)


def archive(d):
    bevel(d, (5, 8, 26, 26), YELLOW, YELLOW_LT, YELLOW_DK)
    d.rectangle((14, 8, 17, 26), fill=GREY_LT, outline=GREY_DK)  # zipper strip
    for yy in range(9, 26, 2):
        d.line([(14, yy), (17, yy)], fill=GREY_DK)
    d.rectangle((13, 11, 18, 15), fill=GREY, outline=GREY_DK)  # zip pull


# --- system / places ---------------------------------------------------------


def my_computer(d):
    bevel(d, (5, 6, 26, 21), SILVER, GREY_LT, GREY_DK)
    d.rectangle((7, 8, 24, 18), fill=BLUE_DK)
    d.rectangle((8, 9, 23, 13), fill=BLUE_LT)
    d.rectangle((11, 21, 20, 24), fill=GREY_DK)  # stand
    bevel(d, (8, 24, 23, 27), SILVER, GREY_LT, GREY_DK)  # base


def monitor(d):
    bevel(d, (3, 5, 28, 23), SILVER, GREY_LT, GREY_DK)
    d.rectangle((5, 7, 26, 21), fill=BLUE)
    d.polygon([(5, 21), (12, 12), (17, 17), (21, 11), (26, 18), (26, 21)], fill=GREEN_DK)
    d.ellipse((19, 8, 23, 12), fill=YELLOW)
    d.rectangle((13, 23, 18, 26), fill=GREY_DK)
    bevel(d, (9, 26, 22, 29), SILVER, GREY_LT, GREY_DK)


def recycle_empty(d):
    d.polygon([(8, 9), (24, 9), (22, 28), (10, 28)], fill=GREEN, outline=GREEN_DK)
    d.polygon([(8, 9), (12, 9), (11, 28), (10, 28)], fill=GREEN_LT)
    for xx in (13, 16, 19):
        d.line([(xx, 12), (xx, 25)], fill=GREEN_DK)
    d.rectangle((6, 6, 26, 9), fill=GREEN_DK)  # lid
    d.rectangle((13, 4, 19, 6), fill=GREEN_DK)  # handle


def recycle_full(d):
    recycle_empty(d)
    d.rectangle((11, 2, 14, 6), fill=BLUE)
    d.rectangle((15, 1, 18, 6), fill=RED)
    d.rectangle((19, 3, 22, 6), fill=YELLOW)
    d.polygon([(10, 5), (13, 1), (16, 5)], fill=GREEN_LT)


def settings(d):
    cx, cy = 16, 16
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        x = cx + int(round(11 * math.cos(rad)))
        y = cy + int(round(11 * math.sin(rad)))
        d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=GREY_DK)
    d.ellipse((6, 6, 26, 26), fill=SILVER, outline=GREY_DK)
    d.ellipse((11, 11, 21, 21), fill=BLUE_DK)
    d.ellipse((13, 13, 19, 19), fill=BLUE_LT)


def search(d):
    d.ellipse((6, 6, 21, 21), outline=BLUE_DK, width=3)
    d.ellipse((9, 9, 18, 18), fill=BLUE_LT)
    d.line([(19, 19), (27, 27)], fill=GREY_DK, width=4)


def help_icon(d):
    d.ellipse((4, 4, 27, 27), fill=BLUE, outline=BLUE_DK)
    d.ellipse((6, 6, 25, 25), outline=BLUE_LT)
    d.arc((11, 9, 21, 18), start=150, end=20, fill=WHITE, width=3)
    d.line([(16, 17), (16, 20)], fill=WHITE, width=3)
    d.rectangle((15, 23, 17, 25), fill=WHITE)


def save_disk(d):
    bevel(d, (4, 4, 27, 27), BLUE, BLUE_LT, BLUE_DK)
    d.rectangle((9, 4, 22, 13), fill=GREY_LT, outline=GREY_DK)  # metal shutter
    d.rectangle((17, 5, 20, 12), fill=GREY_DK)
    d.rectangle((8, 17, 23, 27), fill=WHITE, outline=GREY_DK)  # label
    d.line([(10, 20), (21, 20)], fill=GREY_DK)
    d.line([(10, 23), (21, 23)], fill=GREY_DK)


def cd_disc(d):
    d.ellipse((4, 4, 27, 27), fill=SILVER, outline=GREY_DK)
    d.ellipse((6, 6, 25, 25), outline=BLUE_LT)
    d.pieslice((5, 5, 26, 26), start=200, end=320, fill=(180, 210, 245))
    d.ellipse((12, 12, 19, 19), fill=GREY_LT, outline=GREY_DK)
    d.ellipse((14, 14, 17, 17), fill=(0, 0, 0, 0))


def printer(d):
    d.rectangle((8, 5, 24, 13), fill=WHITE, outline=GREY_DK)  # paper in
    bevel(d, (4, 12, 28, 23), SILVER, GREY_LT, GREY_DK)  # body
    d.rectangle((22, 15, 25, 17), fill=GREEN)  # led
    d.rectangle((8, 21, 24, 29), fill=WHITE, outline=GREY_DK)  # paper out
    d.line([(10, 25), (21, 25)], fill=(150, 150, 150))


def network(d):
    bevel(d, (3, 4, 16, 13), SILVER, GREY_LT, GREY_DK)
    d.rectangle((5, 6, 14, 11), fill=BLUE)
    bevel(d, (16, 19, 29, 28), SILVER, GREY_LT, GREY_DK)
    d.rectangle((18, 21, 27, 26), fill=BLUE)
    d.line([(9, 13), (9, 16), (22, 16), (22, 19)], fill=GREEN_DK, width=2, joint="curve")


def start_button(d):
    bevel(d, (2, 9, 29, 23), GREEN, GREEN_LT, GREEN_DK)
    d.ellipse((5, 11, 14, 20), fill=WHITE)
    d.ellipse((6, 12, 11, 17), fill=GREEN_LT)
    d.polygon([(18, 12), (18, 20), (24, 16)], fill=WHITE)  # generic play/forward glyph


def clock(d):
    d.ellipse((3, 3, 28, 28), fill=WHITE, outline=GREY_DK, width=2)
    d.ellipse((5, 5, 26, 26), outline=BLUE_LT)
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        x = 16 + int(round(10 * math.cos(rad)))
        y = 16 + int(round(10 * math.sin(rad)))
        d.point((x, y), fill=DARK)
    d.line([(16, 16), (16, 8)], fill=DARK, width=2)  # hour hand
    d.line([(16, 16), (22, 19)], fill=RED, width=2)  # minute hand
    d.ellipse((14, 14, 18, 18), fill=BLUE_DK)


def email(d):
    bevel(d, (3, 7, 28, 25), WHITE, WHITE, GREY_DK)
    d.polygon([(3, 7), (16, 18), (28, 7)], fill=GREY_LT, outline=GREY_DK)
    d.line([(3, 25), (13, 16)], fill=GREY_DK)
    d.line([(28, 25), (18, 16)], fill=GREY_DK)
    d.polygon([(3, 7), (16, 18), (28, 7)], outline=BLUE)


ICONS = {
    "window_close": window_close,
    "window_minimize": window_minimize,
    "window_maximize": window_maximize,
    "window_restore": window_restore,
    "folder": folder,
    "folder_open": folder_open,
    "file": file_generic,
    "text_file": text_file,
    "image_file": image_file,
    "video_file": video_file,
    "audio_file": audio_file,
    "code_file": code_file,
    "pdf_file": pdf_file,
    "archive": archive,
    "my_computer": my_computer,
    "monitor": monitor,
    "recycle_empty": recycle_empty,
    "recycle_full": recycle_full,
    "settings": settings,
    "search": search,
    "help": help_icon,
    "save": save_disk,
    "cd": cd_disc,
    "printer": printer,
    "network": network,
    "start": start_button,
    "clock": clock,
    "email": email,
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in ICONS.items():
        img, d = _canvas()
        fn(d)
        _save(img, name)
    print(f"Wrote {len(ICONS)} icons to {OUT_DIR}")


if __name__ == "__main__":
    main()
