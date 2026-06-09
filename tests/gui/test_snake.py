import pytest

from streamdeck_ui import gui


@pytest.mark.serial
def test_snake_starts_and_moves(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)

    head_before = game._snake[-1]
    # A direction press starts the game; a tick advances the head.
    game._control("right")
    assert game._timer.isActive()
    game._tick()
    assert game._snake[-1] == (head_before[0] + 1, head_before[1])
    assert game._alive


@pytest.mark.serial
def test_snake_cannot_reverse_into_itself(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)
    game._control("right")
    # Reversing straight back is ignored (it would eat the neck).
    game._control("left")
    assert game._next_dir == (1, 0)


@pytest.mark.serial
def test_snake_dies_on_wall(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)
    # Drive the head straight into the right wall.
    game._control("right")
    for _ in range(game._width + 2):
        game._tick()
    assert not game._alive
    assert "Game over" in game._status.text()


@pytest.mark.serial
def test_snake_restart_revives(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)
    game._alive = False
    game._control("restart")
    assert game._alive
    assert game._score == 0
