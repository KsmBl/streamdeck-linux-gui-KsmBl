import pytest

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


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
def test_snake_auto_restarts_after_game_over(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)
    game._control("right")
    for _ in range(game._width + 2):
        game._tick()
    assert not game._alive
    assert game._dead_timer.isActive()  # an automatic restart is scheduled


@pytest.mark.serial
def test_snake_restart_revives(qtbot):
    game = gui.SnakeGame()
    qtbot.addWidget(game)
    game._alive = False
    game._control("restart")
    assert game._alive
    assert game._score == 0


@pytest.mark.serial
def test_deck_snake_takes_over_and_restores(api_and_window, mocker):
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(3, 5))
    handler = api.display_handlers[STREAMDECK_SERIAL]
    try:
        game = gui.DeckSnake(main_window.ui, STREAMDECK_SERIAL)
        game.start()
        assert gui.deck_game is game
        handler.stop.assert_called()  # normal render loop paused

        # The right two columns hold a four-arrow d-pad.
        game.on_key(0 * 5 + 4)  # the "up" arrow
        assert game.model._pending == (0, -1)

        game.stop()
        assert gui.deck_game is None
        handler.start.assert_called()  # normal rendering resumed
    finally:
        gui.deck_game = None


@pytest.mark.serial
def test_deck_snake_starts_on_press_and_auto_restarts(api_and_window, mocker):
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(3, 5))
    try:
        game = gui.DeckSnake(main_window.ui, STREAMDECK_SERIAL)
        game.start()
        assert not game.timer.isActive()  # idle until an arrow is pressed
        game.on_key(1 * 5 + 4)  # the "right" arrow starts the game
        assert game.timer.isActive()
        for _ in range(8):  # drive into the wall
            game._tick()
        assert not game.model.alive
        assert game._dead_timer.isActive()  # a restart is scheduled
        game._revive()
        assert game.model.alive
    finally:
        if gui.deck_game is not None:
            gui.deck_game.stop()
        gui.deck_game = None


@pytest.mark.serial
def test_handle_keypress_routes_to_deck_game(api_and_window, mocker):
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(3, 5))
    try:
        game = gui.DeckSnake(main_window.ui, STREAMDECK_SERIAL)
        game.start()
        # A hardware key press is routed to the game, not to button actions.
        gui.handle_keypress(main_window.ui, STREAMDECK_SERIAL, 2 * 5 + 4, True)  # the "down" arrow
        assert game.model._pending == (0, 1)
    finally:
        if gui.deck_game is not None:
            gui.deck_game.stop()
        gui.deck_game = None
