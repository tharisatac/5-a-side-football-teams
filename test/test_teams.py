import pytest

from player.player import Attributes, Player
from player.teams import InvalidTeamSizeError, create_balanced_teams


@pytest.fixture
def players():
    """
    Fixture to create a list of players for testing. Each player is initialized
    with custom attribute values representing their skill ratings.

    :return:
        A list of Player objects (enough for testing a 5v5 or 6v5 game).
    """
    player_data = [
        {
            "shooting": 80,
            "dribbling": 70,
            "passing": 90,
            "tackling": 60,
            "fitness": 85,
            "goalkeeping": 50,
        },
        {
            "shooting": 60,
            "dribbling": 80,
            "passing": 70,
            "tackling": 65,
            "fitness": 70,
            "goalkeeping": 55,
        },
        {
            "shooting": 75,
            "dribbling": 75,
            "passing": 80,
            "tackling": 70,
            "fitness": 80,
            "goalkeeping": 60,
        },
        {
            "shooting": 65,
            "dribbling": 65,
            "passing": 60,
            "tackling": 75,
            "fitness": 80,
            "goalkeeping": 65,
        },
        {
            "shooting": 85,
            "dribbling": 60,
            "passing": 90,
            "tackling": 50,
            "fitness": 90,
            "goalkeeping": 70,
        },
        {
            "shooting": 55,
            "dribbling": 85,
            "passing": 60,
            "tackling": 80,
            "fitness": 65,
            "goalkeeping": 60,
        },
        {
            "shooting": 70,
            "dribbling": 60,
            "passing": 65,
            "tackling": 55,
            "fitness": 85,
            "goalkeeping": 50,
        },
        {
            "shooting": 85,
            "dribbling": 75,
            "passing": 75,
            "tackling": 60,
            "fitness": 90,
            "goalkeeping": 65,
        },
        {
            "shooting": 90,
            "dribbling": 85,
            "passing": 80,
            "tackling": 70,
            "fitness": 80,
            "goalkeeping": 75,
        },
        {
            "shooting": 65,
            "dribbling": 60,
            "passing": 60,
            "tackling": 50,
            "fitness": 70,
            "goalkeeping": 55,
        },
        {
            "shooting": 65,
            "dribbling": 60,
            "passing": 60,
            "tackling": 50,
            "fitness": 70,
            "goalkeeping": 55,
        },
    ]
    players = []
    for data in player_data:
        attributes = Attributes.from_values(data)
        player = Player(name="Player", attributes=attributes, form=5)
        players.append(player)
    return players


def test_create_balanced_teams_with_bonus_5v4(players):
    """
    Test teams for a 5v4 split with a 20% bonus to the smaller team.

    :param players: A list of Player objects.
    """
    test_players = players[:9]
    team_1, team_2 = create_balanced_teams(
        test_players, team_1_size=5, team_2_size=4
    )

    assert len(team_1) == 5
    assert len(team_2) == 4

    total_team_1_rating = sum(player.get_overall_rating() for player in team_1)
    total_team_2_rating = sum(player.get_overall_rating() for player in team_2)

    total_team_2_rating_with_bonus = total_team_2_rating * 1.20
    assert total_team_2_rating_with_bonus == 480
    assert total_team_1_rating == 562.5


def test_create_balanced_teams_with_bonus_6v5(players):
    """
    Test teams for a 6v5 split with a 20% bonus to the smaller team.

    :param players: A list of Player objects.
    """
    test_players = players[:]
    team_1, team_2 = create_balanced_teams(
        test_players, team_1_size=6, team_2_size=5
    )

    assert len(team_1) == 6
    assert len(team_2) == 5

    total_team_1_rating = sum(player.get_overall_rating() for player in team_1)
    total_team_2_rating = sum(player.get_overall_rating() for player in team_2)

    total_team_1_rating_with_bonus = total_team_1_rating * 1.20
    assert total_team_1_rating_with_bonus >= total_team_2_rating


def test_invalid_team_size_error():
    """
    Test the `InvalidTeamSizeError` is raised when there aren't enough players
    for the desired team sizes.

    :param players: A list of Player objects with fewer than the required total.
    """
    # Only 9 players, but trying to create a 5v5 game
    test_players = [
        Player(
            name=f"Player {i}",
            attributes=Attributes.from_values(
                {
                    "shooting": 70,
                    "dribbling": 70,
                    "passing": 70,
                    "tackling": 70,
                    "fitness": 70,
                    "goalkeeping": 70,
                }
            ),
            form=5,
        )
        for i in range(9)
    ]  # Only 9 players in total

    with pytest.raises(InvalidTeamSizeError):
        create_balanced_teams(test_players, team_1_size=5, team_2_size=5)
