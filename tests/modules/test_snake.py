from streamdeck_ui.modules.snake import SnakeModel


def test_reset_starts_alive_moving_right():
    model = SnakeModel(6, 5)
    assert model.alive
    assert model.heading == (1, 0)
    assert len(model.snake) == 3
    assert model.food is not None


def test_step_advances_head():
    model = SnakeModel(6, 5)
    head = model.head
    model.step()
    assert model.head == (head[0] + 1, head[1])


def test_cannot_reverse_onto_neck():
    model = SnakeModel(6, 5)
    model.set_direction((-1, 0))  # straight back is ignored
    model.step()
    assert model.alive  # did not eat itself


def test_turn_is_relative_to_heading():
    model = SnakeModel(6, 5)
    # Heading right: a left turn points up, a right turn points down (y grows down).
    model.turn(left=True)
    assert model._pending == (0, -1)
    model = SnakeModel(6, 5)
    model.turn(left=False)
    assert model._pending == (0, 1)


def test_running_into_wall_ends_the_game():
    model = SnakeModel(6, 5)
    for _ in range(model.width + 2):
        model.step()
    assert not model.alive


def test_eating_food_grows_and_scores():
    model = SnakeModel(6, 5)
    # Put food directly ahead of the head.
    head = model.head
    model.food = (head[0] + 1, head[1])
    length = len(model.snake)
    model.step()
    assert model.score == 1
    assert len(model.snake) == length + 1
