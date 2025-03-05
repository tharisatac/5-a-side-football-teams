import pytest

from player.player import Attributes, Player


@pytest.fixture
def default_player():
    """Create a default player with default values for all attributes."""
    player_data = {
        "shooting": 65,
        "dribbling": 65,
        "passing": 65,
        "tackling": 65,
        "fitness": 65,
        "goalkeeping": 65,
    }
    attributes = Attributes.from_values(player_data)
    player = Player(
        name="John Doe", attributes=attributes, form=5
    )  # form is set to 5
    return player


def test_default_player_attributes(default_player):
    """Test that the player has the correct default attribute values."""
    player = default_player
    assert player.name == "John Doe"
    assert player.attributes.shooting.score == 65
    assert player.attributes.dribbling.score == 65
    assert player.attributes.passing.score == 65
    assert player.attributes.tackling.score == 65
    assert player.attributes.fitness.score == 65
    assert player.attributes.goalkeeping.score == 65


def test_player_overall_rating(default_player):
    """Test the overall rating calculation."""
    player = default_player
    overall_rating = player.get_overall_rating()

    # Manually calculate the expected rating:
    total_score = (
        player.attributes.shooting.score
        + player.attributes.dribbling.score
        + player.attributes.passing.score
        + player.attributes.tackling.score
        + player.attributes.fitness.score
        + player.attributes.goalkeeping.score
    )

    expected_rating = (total_score / 6) * (1 + 0.05 * player.form)

    # Assert that the calculated rating is as expected (allowing for slight float precision errors)
    assert overall_rating == pytest.approx(expected_rating, rel=1e-2)


def test_player_with_custom_attributes():
    """Test the player initialization with custom attribute values."""
    player_data = {
        "shooting": 80,
        "dribbling": 70,
        "passing": 90,
        "tackling": 60,
        "fitness": 85,
        "goalkeeping": 50,
    }
    attributes = Attributes.from_values(player_data)
    player = Player(name="Jane Doe", attributes=attributes, form=3)

    assert player.attributes.shooting.score == 80
    assert player.attributes.dribbling.score == 70
    assert player.attributes.passing.score == 90
    assert player.attributes.tackling.score == 60
    assert player.attributes.fitness.score == 85
    assert player.attributes.goalkeeping.score == 50
    assert player.name == "Jane Doe"

    # Calculate the overall rating with these custom attributes and form
    total_score = (
        player.attributes.shooting.score
        + player.attributes.dribbling.score
        + player.attributes.passing.score
        + player.attributes.tackling.score
        + player.attributes.fitness.score
        + player.attributes.goalkeeping.score
    )
    expected_rating = (total_score / 6) * (1 + 0.05 * player.form)
    overall_rating = player.get_overall_rating()

    assert overall_rating == pytest.approx(expected_rating, rel=1e-2)


def test_player_with_no_form():
    """Test the overall rating with form set to 0."""
    player_data = {
        "shooting": 70,
        "dribbling": 75,
        "passing": 80,
        "tackling": 65,
        "fitness": 70,
        "goalkeeping": 60,
    }
    attributes = Attributes.from_values(player_data)
    player = Player(name="Alex Smith", attributes=attributes, form=0)

    # Calculate the expected rating when form is 0
    total_score = sum(
        attr.score for attr in player.attributes.__dict__.values()
    )
    expected_rating = total_score / 6  # No form adjustment (form = 0)

    overall_rating = player.get_overall_rating()

    assert overall_rating == pytest.approx(expected_rating, rel=1e-2)


def test_player_with_negative_form():
    """Test the overall rating with a negative form."""
    player_data = {
        "shooting": 70,
        "dribbling": 75,
        "passing": 80,
        "tackling": 65,
        "fitness": 70,
        "goalkeeping": 60,
    }
    attributes = Attributes.from_values(player_data)
    player = Player(name="Michael Jordan", attributes=attributes, form=-3)

    # Calculate the expected rating when form is negative
    total_score = sum(
        attr.score for attr in player.attributes.__dict__.values()
    )
    expected_rating = (total_score / 6) * (
        1 + 0.05 * player.form
    )  # Form should reduce rating

    overall_rating = player.get_overall_rating()

    assert overall_rating == pytest.approx(expected_rating, rel=1e-2)


def test_player_with_edge_values():
    """Test with edge values for attributes."""
    player_data = {
        "shooting": 0,
        "dribbling": 100,
        "passing": 100,
        "tackling": 0,
        "fitness": 50,
        "goalkeeping": 100,
    }
    attributes = Attributes.from_values(player_data)
    player = Player(name="Cristiano Ronaldo", attributes=attributes, form=10)

    # Manually calculate the expected overall rating
    total_score = sum(
        attr.score for attr in player.attributes.__dict__.values()
    )
    expected_rating = (total_score / 6) * (1 + 0.05 * player.form)

    overall_rating = player.get_overall_rating()

    assert overall_rating == pytest.approx(expected_rating, rel=1e-2)


def test_invalid_input():
    """Test the player initialization with invalid input (non-numeric)."""
    player_data = {
        "shooting": "invalid",
        "dribbling": "invalid",
        "passing": "invalid",
        "tackling": "invalid",
        "fitness": "invalid",
        "goalkeeping": "invalid",
    }

    with pytest.raises(ValueError):
        Attributes.from_values(player_data)
