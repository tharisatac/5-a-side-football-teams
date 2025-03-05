import pytest

from player.player import Attributes, Player
from player.teams import (
    InvalidTeamSizeError,
    Team,
    apply_team_bonus,
    create_balanced_teams,
)


@pytest.fixture
def players():
    """
    Creates a list of test players with varying attributes.

    :return:
        A list of Player objects.
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
    return [
        Player(
            name=f"Player {i+1}",
            attributes=Attributes.from_values(data),
            form=5,
        )
        for i, data in enumerate(player_data)
    ]


def test_create_balanced_teams_with_bonus_5v4(players):
    """
    Tests teams for a 5v4 split with a 20% bonus applied to the smaller team.

    :param players:
        A list of Player objects.
    """
    test_players = players[:9]
    team_1, team_2 = create_balanced_teams(test_players, 5, 4)

    assert len(team_1.players) == 5
    assert len(team_2.players) == 4

    apply_team_bonus(team_1, team_2)

    total_team_1_rating = team_1.get_overall_rating()
    total_team_2_rating = team_2.get_overall_rating()

    assert total_team_2_rating == pytest.approx(total_team_1_rating, rel=0.1)


def test_create_balanced_teams_with_bonus_6v5(players):
    """
    Tests teams for a 6v5 split with a 20% bonus applied to the smaller team.

    :param players:
        A list of Player objects.
    """
    test_players = players[:11]
    team_1, team_2 = create_balanced_teams(test_players, 6, 5)

    assert len(team_1.players) == 6
    assert len(team_2.players) == 5

    apply_team_bonus(team_1, team_2)

    total_team_1_rating = team_1.get_overall_rating()
    total_team_2_rating = team_2.get_overall_rating()

    assert total_team_2_rating == pytest.approx(total_team_1_rating, rel=0.1)


def test_apply_team_bonus():
    """
    Tests that the smaller team gets a 20% bonus correctly applied.
    """
    team_1 = Team(
        players=[
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
            for i in range(5)
        ]
    )

    team_2 = Team(
        players=[
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
            for i in range(4)
        ]
    )

    apply_team_bonus(team_1, team_2)

    total_team_2_rating_before = sum(
        p.get_overall_rating() for p in team_2.players
    )
    total_team_2_rating_after = team_2.get_overall_rating()

    assert total_team_2_rating_after == pytest.approx(
        total_team_2_rating_before * 1.2, rel=1e-2
    )


def test_create_balanced_teams_with_identical_players():
    """
    Tests balancing when all players have the same attributes.
    """
    identical_players = [
        Player(
            name=f"Player {i}",
            attributes=Attributes.from_values(
                {
                    "shooting": 50,
                    "dribbling": 50,
                    "passing": 50,
                    "tackling": 50,
                    "fitness": 50,
                    "goalkeeping": 50,
                }
            ),
            form=5,
        )
        for i in range(10)
    ]

    team_1, team_2 = create_balanced_teams(identical_players, 5, 5)

    total_team_1_rating = team_1.get_overall_rating()
    total_team_2_rating = team_2.get_overall_rating()

    assert total_team_1_rating == pytest.approx(total_team_2_rating, rel=0.01)


def test_invalid_team_size_error(players):
    """
    Tests that InvalidTeamSizeError is raised for incorrect team sizes.
    """
    with pytest.raises(InvalidTeamSizeError):
        create_balanced_teams(
            [], team_1_size=5, team_2_size=5
        )  # Empty player list

    with pytest.raises(InvalidTeamSizeError):
        create_balanced_teams(
            players[:9], team_1_size=-5, team_2_size=4
        )  # Negative team size
