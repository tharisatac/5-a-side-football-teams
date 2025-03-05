import pytest
import trueskill

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
    Ensures that the TrueSkill rating is initialized correctly.
    """
    player = default_player

    base_rating = player._get_base_rating()
    expected_trueskill = trueskill.Rating(
        mu=base_rating, sigma=max(10 - player.form, player.min_sigma)
    )

    assert player.get_overall_rating() == pytest.approx(
        expected_trueskill.mu * (1 + 0.05 * player.form), rel=1e-2
    )


def test_trueskill_update_on_win(default_player):
    """
    Ensures TrueSkill updates correctly after a win.
    """
    player = default_player
    old_mu = player.get_overall_rating()

    player.update_trueskill(won=True)

    assert player.form == 6  # Form should increase
    assert player.get_overall_rating() > old_mu  # Rating should improve


def test_trueskill_update_on_loss(default_player):
    """
    Ensures TrueSkill updates correctly after a loss.
    """
    player = default_player
    old_mu = player.get_overall_rating()

    player.update_trueskill(won=False)

    assert player.form == 4  # Form should decrease
    assert player.get_overall_rating() < old_mu  # Rating should drop


def test_form_clamping():
    """
    Ensures form values stay between 0 and 10.
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

    assert player_low.form == 0  # Should be clamped to 0
    assert player_high.form == 10  # Should be clamped to 10


def test_attributes_remain_fixed_after_rating():
    """
    Ensures attributes remain unchanged after calling `get_overall_rating`.
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

    original_attributes = vars(player.attributes).copy()
    _ = player.get_overall_rating()

    for attr, original_value in original_attributes.items():
        assert (
            getattr(player.attributes, attr).get_score()
            == original_value.get_score()
        )


def test_identical_players_different_form():
    """
    Ensures identical players with different form values have different ratings.
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
    player2 = Player(name="Player 2", attributes=player1.attributes, form=9)

    assert (
        player2.get_overall_rating() > player1.get_overall_rating()
    )  # Higher form = higher rating


def test_edge_case_attributes():
    """
    Ensures players with extreme attributes get the correct TrueSkill rating.
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
    expected_trueskill = trueskill.Rating(
        mu=base_rating * (1 + 0.05 * player.form), sigma=player.min_sigma
    )

    assert player.get_overall_rating() == pytest.approx(
        expected_trueskill.mu, rel=1e-2
    )


def test_invalid_input():
    """
    Ensures non-numeric attribute values raise a ValueError.
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
