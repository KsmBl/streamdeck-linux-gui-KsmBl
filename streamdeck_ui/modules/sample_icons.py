"""Discovery of the bundled sample icons.

Sample icons live under :data:`~streamdeck_ui.config.SAMPLE_ICONS_DIR`, grouped
into one sub-directory per category. New icons can be added simply by dropping
image files into a category directory; they are picked up automatically.
"""

import os
from typing import Dict, List, Tuple

from streamdeck_ui.config import SAMPLE_ICONS_DIR

_IMAGE_EXTENSIONS = (".png", ".svg", ".jpg", ".jpeg", ".bmp", ".gif")


def _pretty_name(file_name: str) -> str:
    """Turns a file name like ``volume_up.png`` into ``Volume Up``."""
    return os.path.splitext(file_name)[0].replace("_", " ").replace("-", " ").title()


def list_sample_icons(base_dir: str = SAMPLE_ICONS_DIR) -> Dict[str, List[Tuple[str, str]]]:
    """Returns the bundled sample icons grouped by category.

    The result maps a category name to a list of ``(display_name, path)`` tuples,
    sorted alphabetically. Categories without any images are omitted.
    """
    categories: Dict[str, List[Tuple[str, str]]] = {}
    if not os.path.isdir(base_dir):
        return categories

    for category in sorted(os.listdir(base_dir)):
        category_dir = os.path.join(base_dir, category)
        if not os.path.isdir(category_dir):
            continue

        icons: List[Tuple[str, str]] = []
        for file_name in sorted(os.listdir(category_dir)):
            if file_name.lower().endswith(_IMAGE_EXTENSIONS):
                icons.append((_pretty_name(file_name), os.path.join(category_dir, file_name)))

        if icons:
            categories[category] = icons

    return categories
