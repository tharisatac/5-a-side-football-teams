import pytest

from src.player import Attributes, Player


@pytest.fixture
def default_player():
    """
    Creates a default player with balanced attributes.
    """
    player_data = {
        "shooting": 5,
        "dribbling": 5,
        "passing": 5,
        "tackling": 5,
        "fitness": 5,
        "goalkeeping": 5,
    }
    attributes = Attributes.from_values(player_data)
    return Player(name="John Doe", attributes=attributes, form=5)


def test_default_player_attributes(default_player):
    """
    Ensures that the default player has the expected attributes.
    """
    player = default_player
    assert player.name == "John Doe"
    assert player.attributes.shooting.score == 5
    assert player.attributes.dribbling.score == 5
    assert player.attributes.passing.score == 5
    assert player.attributes.tackling.score == 5
    assert player.attributes.fitness.score == 5
    assert player.attributes.goalkeeping.score == 5


def test_player_base_rating(default_player):
    """
    Tests that the base rating is calculated correctly.
    """
    player = default_player
    expected_base_rating = 5  # Since all attributes are 5
    assert player._get_base_rating() == expected_base_rating


def test_player_overall_rating(default_player):
    """
    Tests that the overall rating is calculated correctly based on attributes and form.
    Overall Rating = (Base Rating) * (1 + 0.05 * (form - 5))
    """
    player = default_player
    base_rating = player._get_base_rating()
    multiplier = 1 + 0.05 * (player.form - 5)
    expected_overall = base_rating * multiplier

    assert player.get_overall_rating() == pytest.approx(
        expected_overall, rel=1e-2
    )


def test_update_on_win(default_player):
    """
    Ensures that updating form after a win increases the form and overall rating.
    """
    player = default_player
    old_overall = player.get_overall_rating()
    player.update_form(won=True)
    # Form should increase from 5 to 6
    assert player.form == 6
    # Overall rating should improve
    assert player.get_overall_rating() > old_overall


def test_update_on_loss(default_player):
    """
    Ensures that updating form after a loss decreases the form and overall rating.
    """
    player = default_player
    old_overall = player.get_overall_rating()
    player.update_form(won=False)
    # Form should decrease from 5 to 4
    assert player.form == 4
    # Overall rating should drop
    assert player.get_overall_rating() < old_overall


def test_form_clamping():
    """
    Ensures that form values are clamped between 0 and 10.
    """
    player_low = Player(
        name="Low Form",
        attributes=Attributes.from_values(
            {
                "shooting": 5,
                "dribbling": 5,
                "passing": 5,
                "tackling": 5,
                "fitness": 5,
                "goalkeeping": 5,
            }
        ),
        form=-3,
    )
    player_high = Player(
        name="High Form",
        attributes=Attributes.from_values(
            {
                "shooting": 5,
                "dribbling": 5,
                "passing": 5,
                "tackling": 5,
                "fitness": 5,
                "goalkeeping": 5,
            }
        ),
        form=15,
    )

    assert player_low.form == 0  # Clamped to 0
    assert player_high.form == 10  # Clamped to 10


def test_attributes_remain_fixed_after_rating():
    """
    Ensures that the player's attribute values remain unchanged after calculating the overall rating.
    """
    player = Player(
        name="Fixed Attr",
        attributes=Attributes.from_values(
            {
                "shooting": 6,
                "dribbling": 5,
                "passing": 6,
                "tackling": 4,
                "fitness": 6,
                "goalkeeping": 5,
            }
        ),
        form=5,
    )

    original_attributes = {
        attr: getattr(player.attributes, attr).get_score()
        for attr in vars(player.attributes)
    }
    _ = player.get_overall_rating()

    for attr, original_value in original_attributes.items():
        assert getattr(player.attributes, attr).get_score() == original_value


def test_identical_players_different_form():
    """
    Ensures that identical players with different form values have different overall ratings.
    """
    player1 = Player(
        name="Player 1",
        attributes=Attributes.from_values(
            {
                "shooting": 5,
                "dribbling": 5,
                "passing": 5,
                "tackling": 5,
                "fitness": 5,
                "goalkeeping": 5,
            }
        ),
        form=3,
    )
    player2 = Player(
        name="Player 2",
        attributes=Attributes.from_values(
            {
                "shooting": 5,
                "dribbling": 5,
                "passing": 5,
                "tackling": 5,
                "fitness": 5,
                "goalkeeping": 5,
            }
        ),
        form=9,
    )

    breakpoint()
    assert (
        player2.get_overall_rating() > player1.get_overall_rating()
    )  # Higher form = higher rating


def test_edge_case_attributes():
    """
    Ensures that a player with extreme attribute values gets the correct overall rating.
    """
    player = Player(
        name="Extreme",
        attributes=Attributes.from_values(
            {
                "shooting": 1,
                "dribbling": 10,
                "passing": 10,
                "tackling": 1,
                "fitness": 5,
                "goalkeeping": 10,
            }
        ),
        form=10,
    )

    base_rating = player._get_base_rating()
    multiplier = 1 + 0.05 * (player.form - 5)
    expected_overall = base_rating * multiplier

    assert player.get_overall_rating() == pytest.approx(
        expected_overall, rel=1e-2
    )


def test_invalid_input():
    """
    Ensures that non-numeric attribute values raise a ValueError.
    """
    invalid_player_data = {
        "shooting": "invalid",
        "dribbling": "invalid",
        "passing": "invalid",
        "tackling": "invalid",
        "fitness": "invalid",
        "goalkeeping": "invalid",
    }

    with pytest.raises(ValueError):
        Attributes.from_values(invalid_player_data)
