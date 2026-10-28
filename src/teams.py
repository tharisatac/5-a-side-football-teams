"""
This module defines the `Team` class and the pure functions that split a list
of players into two balanced teams. Teams are balanced based on overall player
ratings, and if one team is smaller, a boost is applied to the larger team.

"Pure" here means the functions only read their inputs and return new values:
they never touch the database, print, or modify the players/teams passed in.
"""

from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .player import Player

# --------------------------
# Errors
# --------------------------


class DuplicatePlayerError(Exception):
    """
    Raised when a duplicate player is added during team creation.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the DuplicatePlayerError.

        :param name:
            The name of the player that was given more than once.
        """
        self.name = name

        super().__init__(f"Duplicate player added '{self.name}'")


class NotEnoughPlayersError(Exception):
    """
    Raised when fewer than 2 players are given to create teams.
    """

    def __init__(self, num_players: int) -> None:
        """
        Initializes the NotEnoughPlayersError.

        :param num_players:
            The total number of players provided.
        """
        self.num_players = num_players
        super().__init__(
            f"At least 2 players are needed to create teams, got "
            f"{num_players}."
        )


LARGE_TEAM_BOOST = 1.2


@dataclass
class Team:
    """
    Represents a football team with players and overall team statistics.

    Attributes:
        players : List of Player objects.
        bonus : A rating multiplier applied to the team (default is 1.0).
    """

    players: List[Player]
    bonus: float = 1.0

    def get_overall_rating(self, round_num: bool = False) -> float:
        """
        Calculates the total adjusted team rating.

        :param round_num:
            Whether to round to 2 decimals. This should only be True if
            outputting to the end user.

        :return:
            The total rating of the team, considering the bonus.
        """
        total_rating = sum(
            player.get_overall_rating() for player in self.players
        )
        if not round_num:
            return total_rating * self.bonus
        return round(total_rating * self.bonus, 2)


def balance_teams(players: Sequence[Player]) -> Tuple[Team, Team]:
    """
    Splits players into two balanced teams.

    Team 1 gets `len(players) // 2` players and team 2 gets the rest, so with
    an odd number of players team 2 is the larger team and gets the boost.

    :param players:
        The players to split. Must contain at least 2 unique names.

    :raises:
        NotEnoughPlayersError: If fewer than 2 players are given.
        DuplicatePlayerError: If the same player name appears twice.

    :return:
        The two balanced teams.
    """
    if len(players) < 2:
        raise NotEnoughPlayersError(len(players))

    for name, count in Counter(player.name for player in players).items():
        if count > 1:
            raise DuplicatePlayerError(name)

    team_1_size = len(players) // 2
    team_2_size = len(players) - team_1_size
    team_1, team_2 = _distribute_players(players, team_1_size, team_2_size)
    return improve_balance(team_1, team_2)


def improve_balance(team_1: Team, team_2: Team) -> Tuple[Team, Team]:
    """
    Repeatedly applies the single player swap that most reduces the rating
    difference between the teams, until no swap improves it.

    The input teams are left untouched; new teams are returned.

    :param team_1:
        The first team.
    :param team_2:
        The second team.

    :return:
        The two rebalanced teams.
    """
    team_1 = Team(list(team_1.players), team_1.bonus)
    team_2 = Team(list(team_2.players), team_2.bonus)

    while True:
        best_swap: Optional[Tuple[int, int]] = None
        best_diff_seen = _team_rating_diff(team_1, team_2)

        # Try all swaps and find the best one
        for idx1 in range(len(team_1.players)):
            for idx2 in range(len(team_2.players)):
                _swap_players(team_1, team_2, idx1, idx2)
                new_diff = _team_rating_diff(team_1, team_2)

                if new_diff < best_diff_seen:
                    best_diff_seen = new_diff
                    best_swap = (idx1, idx2)

                _swap_players(team_1, team_2, idx1, idx2)  # Undo swap

        if best_swap is None:
            return team_1, team_2  # No improving swaps left

        # Apply the best swap found
        _swap_players(team_1, team_2, *best_swap)


def _distribute_players(
    players: Sequence[Player], team_1_size: int, team_2_size: int
) -> Tuple[Team, Team]:
    """
    Distributes players into two teams using a zigzag method, then applies a
    rating bonus to the larger team if team sizes are uneven.

    :param players:
        The players to distribute.
    :param team_1_size:
        How many players team 1 gets.
    :param team_2_size:
        How many players team 2 gets.

    :return:
        The two teams.
    """
    sorted_players = sorted(
        players, key=lambda x: x.get_overall_rating(), reverse=True
    )
    team_1_players: List[Player] = []
    team_2_players: List[Player] = []

    for i, player in enumerate(sorted_players):
        if len(team_1_players) < team_1_size and (
            i % 2 == 0 or len(team_2_players) >= team_2_size
        ):
            team_1_players.append(player)
        else:
            team_2_players.append(player)

    team_1 = Team(team_1_players)
    team_2 = Team(team_2_players)
    if team_1_size > team_2_size:
        team_1.bonus = LARGE_TEAM_BOOST
    elif team_2_size > team_1_size:
        team_2.bonus = LARGE_TEAM_BOOST
    return team_1, team_2


def _swap_players(team_1: Team, team_2: Team, idx1: int, idx2: int) -> None:
    """
    Swaps two players between teams based on their indices.

    :param team_1:
        The first team.
    :param team_2:
        The second team.
    :param idx1:
        The index of the player in team 1.
    :param idx2:
        The index of the player in team 2.
    """
    team_1.players[idx1], team_2.players[idx2] = (
        team_2.players[idx2],
        team_1.players[idx1],
    )


def _team_rating_diff(team_1: Team, team_2: Team) -> float:
    """
    Determines the absolute difference between the two teams' ratings.

    :param team_1:
        The first team.
    :param team_2:
        The second team.
    """
    return abs(team_1.get_overall_rating() - team_2.get_overall_rating())
