import pytest

from streamdeck_ui import gui
from tests.common import STREAMDECK_SERIAL


@pytest.mark.serial
def test_lights_out_press_toggles_cross(qtbot):
    game = gui.LightsOutGame()
    qtbot.addWidget(game)
    w, h = game.model.width, game.model.height
    # A known board with a single far corner lit (so it is not already solved,
    # which would make clicking a no-op), then click an interior cell.
    game.model.grid = [[False] * w for _ in range(h)]
    game.model.grid[h - 1][w - 1] = True
    game._press(2, 1)
    lit = {(x, y) for y in range(h) for x in range(w) if game.model.is_lit(x, y)}
    assert {(2, 1), (1, 1), (3, 1), (2, 0), (2, 2)} <= lit


@pytest.mark.serial
def test_lights_out_new_game_resets_moves(qtbot):
    game = gui.LightsOutGame()
    qtbot.addWidget(game)
    game._press(0, 0)
    game._new_game()
    assert game.model.moves == 0


@pytest.mark.serial
def test_lights_out_solved_status(qtbot):
    game = gui.LightsOutGame()
    qtbot.addWidget(game)
    game.model.grid = [[False] * game.model.width for _ in range(game.model.height)]
    game._render()
    assert "Solved" in game._status.text()


@pytest.mark.serial
def test_deck_lights_out_takes_over_and_restores(api_and_window, mocker):
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(3, 5))
    handler = api.display_handlers[STREAMDECK_SERIAL]
    try:
        game = gui.DeckLightsOut(main_window.ui, STREAMDECK_SERIAL)
        game.start()
        assert gui.deck_game is game
        handler.stop.assert_called()  # normal render loop paused

        game.model.grid = [[False] * game.cols for _ in range(game.rows)]
        game.on_key(2 * 5 + 1)  # press the cell at column 1, row 2
        lit = {(x, y) for y in range(game.rows) for x in range(game.cols) if game.model.is_lit(x, y)}
        assert (1, 2) in lit and (0, 2) in lit and (1, 1) in lit

        game.stop()
        assert gui.deck_game is None
        handler.start.assert_called()  # normal rendering resumed
    finally:
        gui.deck_game = None


@pytest.mark.serial
def test_lights_out_window_mirrors_deck(api_and_window, qtbot, mocker):
    """The on-screen board reflects the on-deck puzzle's live state."""
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(4, 8))
    try:
        deck = gui.DeckLightsOut(main_window.ui, STREAMDECK_SERIAL)
        deck.start()
        window = gui.LightsOutGame()
        qtbot.addWidget(window)
        window._deck = deck
        deck.mirror = window._render_from_deck
        deck.model.grid = [[False] * deck.model.width for _ in range(deck.model.height)]
        deck.on_key(0)  # press cell (0,0); the window mirrors the lit cross
        assert gui.LightsOutGame._ON in window._cells[(0, 0)].styleSheet()
    finally:
        gui.deck_game = None


@pytest.mark.serial
def test_handle_keypress_routes_to_lights_out(api_and_window, mocker):
    main_window, api = api_and_window
    mocker.patch.object(api, "get_deck_layout", return_value=(3, 5))
    try:
        game = gui.DeckLightsOut(main_window.ui, STREAMDECK_SERIAL)
        game.start()
        game.model.grid = [[False] * game.cols for _ in range(game.rows)]
        gui.handle_keypress(main_window.ui, STREAMDECK_SERIAL, 0, True)  # press key 0 -> cell (0,0)
        assert game.model.is_lit(0, 0)
    finally:
        if gui.deck_game is not None:
            gui.deck_game.stop()
        gui.deck_game = None
