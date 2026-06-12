"""A tiny, UI-independent Snake game model.

The model knows nothing about Qt or the Stream Deck; it is pure logic so it can
be driven by the in-window game, the on-deck game and the tests alike. The grid
uses screen coordinates: ``x`` grows right, ``y`` grows down.
"""

import random
from collections import deque
from typing import Deque, List, Optional, Tuple

Cell = Tuple[int, int]


class SnakeModel:
    """Snake on a ``width`` x ``height`` grid. The snake is a deque with the tail
    at index 0 and the head at index -1."""

    def __init__(self, width: int, height: int):
        self.width = max(int(width), 3)
        self.height = max(int(height), 3)
        self.reset()

    def reset(self) -> None:
        cy = self.height // 2
        # Lay the snake flush against the left wall, heading right, so it always
        # fits on the board (even on a narrow on-deck playfield) with no
        # off-board segments.
        length = max(2, min(3, self.width - 1))
        self.snake: Deque[Cell] = deque((x, cy) for x in range(length))
        self.heading: Cell = (1, 0)
        self._pending: Cell = (1, 0)
        self.alive = True
        self.score = 0
        self.place_food()

    def place_food(self) -> None:
        free: List[Cell] = [(x, y) for x in range(self.width) for y in range(self.height) if (x, y) not in self.snake]
        self.food: Optional[Cell] = random.choice(free) if free else None

    @property
    def head(self) -> Cell:
        return self.snake[-1]

    def set_direction(self, delta: Cell) -> None:
        """Sets the absolute direction for the next step, ignoring a reversal
        straight back onto the neck."""
        if not self.alive:
            return
        if delta == (-self.heading[0], -self.heading[1]):
            return
        self._pending = delta

    def turn(self, left: bool) -> None:
        """Turns relative to the current heading (for two-button control)."""
        dx, dy = self.heading
        self.set_direction((dy, -dx) if left else (-dy, dx))

    def step(self) -> bool:
        """Advances the snake one cell. Returns True while the snake is alive."""
        if not self.alive:
            return False
        self.heading = self._pending
        head_x, head_y = self.snake[-1]
        new_head = (head_x + self.heading[0], head_y + self.heading[1])

        will_grow = new_head == self.food
        body = set(self.snake)
        if not will_grow:
            body.discard(self.snake[0])  # the tail moves out of the way this step
        if not (0 <= new_head[0] < self.width) or not (0 <= new_head[1] < self.height) or new_head in body:
            self.alive = False
            return False

        self.snake.append(new_head)
        if will_grow:
            self.score += 1
            self.place_food()
        else:
            self.snake.popleft()
        return True
