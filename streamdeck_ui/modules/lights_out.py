"""A tiny, UI-independent Lights Out game model.

Lights Out is a grid of two-state cells. Pressing a cell toggles that cell and
its four orthogonal neighbours (up/down/left/right) between the two states; the
puzzle is solved when every cell is in the "off" state. The model is pure logic
with no Qt or Stream Deck dependency, so the in-window game, the on-deck game
and the tests can all drive it. Coordinates are ``x`` (column, grows right) and
``y`` (row, grows down).
"""

import random
from typing import List

_NEIGHBOURS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))


class LightsOutModel:
    """Lights Out on a ``width`` x ``height`` grid of on/off cells."""

    def __init__(self, width: int, height: int):
        self.width = max(int(width), 2)
        self.height = max(int(height), 2)
        self.grid: List[List[bool]] = []
        self.moves = 0
        self.reset()

    def reset(self, scramble: int = -1) -> None:
        """Starts a fresh, solvable puzzle.

        The board begins fully off and is scrambled by applying ``scramble``
        random presses. Because every press is reversible, a board reached this
        way is always solvable. ``scramble`` defaults to roughly half the cells.
        """
        self.grid = [[False] * self.width for _ in range(self.height)]
        presses = scramble if scramble >= 0 else max(3, (self.width * self.height) // 2)
        # Re-scramble in the unlikely event the random presses cancel out.
        for _attempt in range(8):
            for _ in range(presses):
                self._toggle_cross(random.randrange(self.width), random.randrange(self.height))
            if not self.is_solved():
                break
        self.moves = 0

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _toggle(self, x: int, y: int) -> None:
        if self.in_bounds(x, y):
            self.grid[y][x] = not self.grid[y][x]

    def _toggle_cross(self, x: int, y: int) -> None:
        for dx, dy in _NEIGHBOURS:
            self._toggle(x + dx, y + dy)

    def press(self, x: int, y: int) -> bool:
        """Toggles the cell and its orthogonal neighbours. Returns True if the
        press was on the board."""
        if not self.in_bounds(x, y):
            return False
        self._toggle_cross(x, y)
        self.moves += 1
        return True

    def is_lit(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.grid[y][x]

    def is_solved(self) -> bool:
        return all(not cell for row in self.grid for cell in row)
