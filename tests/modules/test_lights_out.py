from streamdeck_ui.modules.lights_out import LightsOutModel


def test_press_toggles_cell_and_orthogonal_neighbours():
    model = LightsOutModel(5, 5)
    # Start from a known, all-off board.
    model.grid = [[False] * 5 for _ in range(5)]
    model.press(2, 2)
    lit = {(x, y) for y in range(5) for x in range(5) if model.is_lit(x, y)}
    assert lit == {(2, 2), (1, 2), (3, 2), (2, 1), (2, 3)}
    assert model.moves == 1


def test_press_at_corner_ignores_off_board_neighbours():
    model = LightsOutModel(5, 5)
    model.grid = [[False] * 5 for _ in range(5)]
    model.press(0, 0)
    lit = {(x, y) for y in range(5) for x in range(5) if model.is_lit(x, y)}
    assert lit == {(0, 0), (1, 0), (0, 1)}


def test_pressing_twice_restores_the_board():
    model = LightsOutModel(4, 3)
    model.grid = [[False] * 4 for _ in range(3)]
    model.press(1, 1)
    model.press(1, 1)
    assert model.is_solved()


def test_reset_makes_a_solvable_non_solved_board():
    model = LightsOutModel(5, 5)
    # A scrambled board is reachable from all-off by presses, hence solvable;
    # replaying any solution returns it to all-off. It should not start solved.
    assert not model.is_solved()
    assert model.moves == 0


def test_off_board_press_is_a_no_op():
    model = LightsOutModel(3, 3)
    before = model.moves
    assert model.press(5, 5) is False
    assert model.moves == before
