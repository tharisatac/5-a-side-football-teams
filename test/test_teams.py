import random

import pytest

from src.player import Attributes, Player
from src.teams import InvalidTeamSizeError, Team, TeamCreator


@pytest.fixture
def sample_players():
    """
    Creates a list of sample players with varying attributes.

    :return:
        A list of Player objects.
    """
    player_data = [
        {
            "shooting": 8,
            "dribbling": 7,
            "passing": 9,
            "tackling": 6,
            "fitness": 8,
            "goalkeeping": 5,
        },
        {
            "shooting": 6,
            "dribbling": 8,
            "passing": 7,
            "tackling": 6,
            "fitness": 7,
            "goalkeeping": 5,
        },
        {
            "shooting": 7,
            "dribbling": 7,
            "passing": 8,
            "tackling": 7,
            "fitness": 8,
            "goalkeeping": 6,
        },
        {
            "shooting": 6,
            "dribbling": 6,
            "passing": 6,
            "tackling": 7,
            "fitness": 8,
            "goalkeeping": 6,
        },
        {
            "shooting": 9,
            "dribbling": 6,
            "passing": 9,
            "tackling": 5,
            "fitness": 9,
            "goalkeeping": 7,
        },
        {
            "shooting": 5,
            "dribbling": 9,
            "passing": 6,
            "tackling": 8,
            "fitness": 6,
            "goalkeeping": 6,
        },
        {
            "shooting": 7,
            "dribbling": 6,
            "passing": 6,
            "tackling": 5,
            "fitness": 8,
            "goalkeeping": 5,
        },
        {
            "shooting": 9,
            "dribbling": 7,
            "passing": 7,
            "tackling": 6,
            "fitness": 9,
            "goalkeeping": 6,
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


def test_create_balanced_teams(sample_players):
    """
    Tests that TeamCreator correctly creates balanced teams.
    """
    team_creator = TeamCreator(sample_players, 4, 4)
    team1, team2 = team_creator.create_balanced_teams()

    assert len(team1.players) == 4
    assert len(team2.players) == 4
    assert (
        abs(team1.get_overall_rating() - team2.get_overall_rating()) < 2
    ), "Teams should be balanced"


def test_invalid_team_size_error(sample_players):
    """
    Tests that an error is raised when team sizes don't match available players.
    """
    with pytest.raises(InvalidTeamSizeError):
        TeamCreator(sample_players, 4, 3)  # Total does not match player count


def test_apply_team_bonus():
    """
    Tests that a bonus is applied correctly to the larger team.
    """
    sample_players = [
        Player(
            name=f"Player {i+1}",
            attributes=Attributes.from_values(
                {
                    "shooting": 6,
                    "dribbling": 6,
                    "passing": 6,
                    "tackling": 6,
                    "fitness": 6,
                    "goalkeeping": 6,
                }
            ),
            form=5,
        )
        for i in range(7)
    ]

    team_creator = TeamCreator(sample_players, 4, 3)  # Unequal team sizes
    team1, team2 = team_creator.create_balanced_teams()

    if len(team1.players) > len(team2.players):
        assert team1.bonus > 1.0
    elif len(team2.players) > len(team1.players):
        assert team2.bonus > 1.0


def test_adjust_teams_for_fairness():
    """
    Tests that teams adjust correctly for fairness by swapping players.
    """

    # Create an extreme imbalance: all strong players in team1, all weak in
    # team2
    strong_players = [
        Player(
            name=f"Strong {i}",
            attributes=Attributes.from_values(
                {
                    "shooting": 10,
                    "dribbling": 10,
                    "passing": 10,
                    "tackling": 10,
                    "fitness": 10,
                    "goalkeeping": 10,
                }
            ),
            form=5,
        )
        for i in range(4)
    ]

    weak_players = [
        Player(
            name=f"Weak {i}",
            attributes=Attributes.from_values(
                {
                    "shooting": 1,
                    "dribbling": 1,
                    "passing": 1,
                    "tackling": 1,
                    "fitness": 1,
                    "goalkeeping": 1,
                }
            ),
            form=5,
        )
        for i in range(4)
    ]

    # Check initial imbalance
    team_creator = TeamCreator(strong_players + weak_players, 4, 4)
    team_creator.team_1.players = (
        strong_players  # Force team 1 to be all strong
    )
    team_creator.team_2.players = weak_players  # Force team 2 to be all weak

    assert (
        team_creator.team_1.get_overall_rating()
        > team_creator.team_2.get_overall_rating() + 30
    ), "Initial teams should be highly imbalanced"

    # Run the fairness adjustment
    team_creator._adjust_teams_for_fairness()
    balanced_team1, balanced_team2 = team_creator.team_1, team_creator.team_2

    # Ensure that the new teams are more balanced
    new_diff = abs(
        balanced_team1.get_overall_rating()
        - balanced_team2.get_overall_rating()
    )

    print(f"⚖️ Adjusted balance diff: {new_diff}")

    assert (
        new_diff < 5
    ), "Teams should be significantly more balanced after adjustment"


def test_adjust_teams_for_fairness_is_deterministic(sample_players):
    """
    Ensures that adjusting fairness always results in the same optimal balance,
    even if players are swapped before recalculating.
    """
    # Create the initial best-balanced teams
    team_creator = TeamCreator(sample_players, 4, 4)
    team1, team2 = team_creator.create_balanced_teams()

    initial_balance_diff = abs(
        team1.get_overall_rating() - team2.get_overall_rating()
    )

    # Introduce a **random swap** to unbalance the teams
    random.shuffle(sample_players)

    # Recalculate the teams after introducing imbalance
    new_team_creator = TeamCreator(sample_players, 4, 4)
    new_team1, new_team2 = new_team_creator.create_balanced_teams()

    final_balance_diff = abs(
        new_team1.get_overall_rating() - new_team2.get_overall_rating()
    )

    # Ensure the balance difference is **the same** after re-balancing
    assert (
        initial_balance_diff == final_balance_diff
    ), "Final balance should be the same regardless of starting swaps"

    # Ensure **the same players** exist across both teams, ignoring swaps
    initial_players = {p.name for p in sample_players}
    final_players = {p.name for p in new_team1.players}.union(
        {p.name for p in new_team2.players}
    )

    assert initial_players == final_players, (
        "All players should still be in the teams after adjustment, even if "
        "swapped"
    )


def test_create_minimum_teams():
    """
    Tests creating the smallest possible teams (1v1).
    """
    min_players = [
        Player(
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
            form=5,
        ),
        Player(
            name="Player 2",
            attributes=Attributes.from_values(
                {
                    "shooting": 6,
                    "dribbling": 6,
                    "passing": 6,
                    "tackling": 6,
                    "fitness": 6,
                    "goalkeeping": 6,
                }
            ),
            form=5,
        ),
    ]

    team_creator = TeamCreator(min_players, 1, 1)
    team1, team2 = team_creator.create_balanced_teams()

    assert len(team1.players) == 1
    assert len(team2.players) == 1


def test_create_unbalanced_teams():
    """
    Tests that unbalanced teams (3v2) still apply the proper bonus.
    """
    players = [
        Player(
            name=f"Player {i}",
            attributes=Attributes.from_values(
                {
                    "shooting": i + 1,
                    "dribbling": i + 1,
                    "passing": i + 1,
                    "tackling": i + 1,
                    "fitness": i + 1,
                    "goalkeeping": i + 1,
                }
            ),
            form=5,
        )
        for i in range(5)
    ]

    team_creator = TeamCreator(players, 3, 2)
    team1, team2 = team_creator.create_balanced_teams()

    if len(team1.players) > len(team2.players):
        assert team1.bonus > 1.0, "Bonus should be applied to larger team"
    elif len(team2.players) > len(team1.players):
        assert team2.bonus > 1.0, "Bonus should be applied to larger team"
