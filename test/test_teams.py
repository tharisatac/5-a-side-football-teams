import copy
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.player import ATTRIBUTE_NAMES, Attributes, Player
from src.teams import (
    LARGE_TEAM_BOOST,
    DuplicatePlayerError,
    NotEnoughPlayersError,
    Team,
    balance_teams,
    improve_balance,
)


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
    Tests that balance_teams correctly creates balanced teams.
    """
    team1, team2 = balance_teams(sample_players)

    assert len(team1.players) == 4
    assert len(team2.players) == 4
    assert (
        abs(team1.get_overall_rating() - team2.get_overall_rating()) < 2
    ), "Teams should be balanced"


@pytest.mark.parametrize("num_players", [0, 1])
def test_not_enough_players_error(sample_players, num_players):
    """
    Tests that an error is raised when there are fewer than 2 players.
    """
    with pytest.raises(NotEnoughPlayersError):
        balance_teams(sample_players[:num_players])


@pytest.mark.parametrize("copies", [2, 3])
def test_duplicate_player_error(sample_players, copies):
    """
    Tests that an error is raised when a player is given more than once.
    """
    with pytest.raises(DuplicatePlayerError) as exc:
        balance_teams(sample_players[:2] + [sample_players[0]] * (copies - 1))

    assert exc.value.name == sample_players[0].name


def test_balance_teams_does_not_modify_input(sample_players):
    """
    Tests that balance_teams leaves the given list and players untouched.
    """
    original_order = list(sample_players)
    original_forms = [p.form for p in sample_players]

    balance_teams(sample_players)

    assert sample_players == original_order
    assert [p.form for p in sample_players] == original_forms


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

    team1, team2 = balance_teams(sample_players)  # 7 players: 3 v 4

    assert len(team1.players) == 3
    assert len(team2.players) == 4
    assert team1.bonus == 1.0
    assert team2.bonus == LARGE_TEAM_BOOST


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
    strong_team = Team(list(strong_players))  # Team 1 is all strong
    weak_team = Team(list(weak_players))  # Team 2 is all weak

    assert (
        strong_team.get_overall_rating() > weak_team.get_overall_rating() + 30
    ), "Initial teams should be highly imbalanced"

    # Run the fairness adjustment
    balanced_team1, balanced_team2 = improve_balance(strong_team, weak_team)

    # The input teams must not be modified
    assert strong_team.players == strong_players
    assert weak_team.players == weak_players

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
    team1, team2 = balance_teams(sample_players)

    initial_balance_diff = abs(
        team1.get_overall_rating() - team2.get_overall_rating()
    )

    # Introduce a **random swap** to unbalance the teams
    random.shuffle(sample_players)

    # Recalculate the teams after introducing imbalance
    new_team1, new_team2 = balance_teams(sample_players)

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

    team1, team2 = balance_teams(min_players)

    assert len(team1.players) == 1
    assert len(team2.players) == 1


def test_create_unbalanced_teams():
    """
    Tests that unbalanced teams (2v3) still apply the proper bonus.
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

    team1, team2 = balance_teams(players)  # 5 players: 2 v 3

    assert len(team1.players) == 2
    assert len(team2.players) == 3
    assert team1.bonus == 1.0
    assert team2.bonus == LARGE_TEAM_BOOST, "Bonus should go to larger team"


# -------------------------------------------------------------------
# Property-based tests
#
# Instead of hand-picked examples, Hypothesis generates many random squads
# and checks that each rule holds for all of them. When a rule fails, it
# shrinks the squad to the smallest one that still breaks it.
# -------------------------------------------------------------------

# Allow for rounding errors when comparing float ratings.
TOLERANCE = 1e-9


@st.composite
def squads(draw, min_size=2, max_size=12):
    """
    Generates a list of players with unique names, random skills (1-10) and
    random form (0-10).
    """
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    return [
        Player(
            name=f"Player {i}",
            attributes=Attributes.from_values(
                {
                    name: draw(st.integers(min_value=1, max_value=10))
                    for name in ATTRIBUTE_NAMES
                }
            ),
            form=draw(st.integers(min_value=0, max_value=10)),
        )
        for i in range(count)
    ]


def _rating_diff(team1: Team, team2: Team) -> float:
    return abs(team1.get_overall_rating() - team2.get_overall_rating())


@given(squads())
def test_every_player_is_placed_exactly_once(players):
    """
    No player is lost, duplicated or invented.
    """
    team1, team2 = balance_teams(players)

    placed = sorted(p.name for p in team1.players + team2.players)
    assert placed == sorted(p.name for p in players)


@given(squads())
def test_team_sizes_differ_by_at_most_one(players):
    """
    Team 1 gets half the players (rounded down), team 2 the rest.
    """
    team1, team2 = balance_teams(players)

    assert len(team1.players) == len(players) // 2
    assert len(team2.players) == len(players) - len(players) // 2


@given(squads())
def test_only_a_larger_team_gets_the_boost(players):
    """
    Equal teams have no bonus; with an odd squad only team 2 (the larger
    one) is boosted.
    """
    team1, team2 = balance_teams(players)

    assert team1.bonus == 1.0
    expected = LARGE_TEAM_BOOST if len(players) % 2 else 1.0
    assert team2.bonus == expected


@given(squads())
def test_no_single_swap_improves_the_balance(players):
    """
    The result can't be improved by swapping any one pair of players, which
    is exactly the point at which the balancer stops.
    """
    team1, team2 = balance_teams(players)
    best = _rating_diff(team1, team2)

    for i in range(len(team1.players)):
        for j in range(len(team2.players)):
            swapped1 = list(team1.players)
            swapped2 = list(team2.players)
            swapped1[i], swapped2[j] = swapped2[j], swapped1[i]
            diff = _rating_diff(
                Team(swapped1, team1.bonus), Team(swapped2, team2.bonus)
            )
            assert diff >= best - TOLERANCE


@given(squads())
def test_balance_teams_does_not_modify_its_input(players):
    """
    The list and the players in it are unchanged afterwards.
    """
    before = copy.deepcopy(players)

    balance_teams(players)

    assert players == before


@given(squads(), st.randoms(use_true_random=False))
def test_input_order_does_not_change_the_balance(players, rng):
    """
    Shuffling the squad first gives teams that are just as balanced.
    """
    team1, team2 = balance_teams(players)
    shuffled = list(players)
    rng.shuffle(shuffled)
    shuffled1, shuffled2 = balance_teams(shuffled)

    assert _rating_diff(shuffled1, shuffled2) == pytest.approx(
        _rating_diff(team1, team2), abs=TOLERANCE
    )


@given(squads(), st.data())
def test_improve_balance_never_makes_things_worse(players, data):
    """
    For any starting split, improve_balance keeps the same players and team
    sizes, never increases the rating difference, and leaves the input
    teams unchanged.
    """
    split = data.draw(st.integers(min_value=1, max_value=len(players) - 1))
    start1, start2 = Team(players[:split]), Team(players[split:])
    before = copy.deepcopy((start1, start2))

    team1, team2 = improve_balance(start1, start2)

    assert _rating_diff(team1, team2) <= _rating_diff(start1, start2) + (
        TOLERANCE
    )
    assert len(team1.players) == len(start1.players)
    assert len(team2.players) == len(start2.players)
    assert sorted(p.name for p in team1.players + team2.players) == sorted(
        p.name for p in players
    )
    assert (start1, start2) == before
