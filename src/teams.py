"""
This module defines the `Team` class and functions for creating balanced teams
from a list of players. Teams are balanced based on overall player ratings,
and if one team is smaller, a boost is applied.
"""

from typing import List, Tuple

from .player import Player

SMALL_TEAM_BOOST = 1.2


class Team:
    """
    Represents a football team with players and overall team statistics.

    Attributes:
        players : List of Player objects.
        bonus : A rating multiplier applied to the team (default is 1.0).
    """

    def __init__(self, players: List[Player], bonus: float = 1.0):
        """
        Initializes a team with players and an optional bonus.

        :param players:
            List of Player objects.
        :param bonus:
            A multiplier applied to the team’s rating (default: 1.0).
        """
        self.players = players
        self.bonus = bonus  # Default bonus is 1.0 (no effect)

    def get_overall_rating(self) -> float:
        """
        Calculates the total adjusted team rating.

        :return:
            The total rating of the team, considering the bonus.
        """
        total_rating = sum(
            player.get_overall_rating() for player in self.players
        )
        return total_rating * self.bonus

    def get_attribute_rating(self, attribute: str) -> float:
        """
        Calculates the team's average rating for a specific attribute.

        :param attribute:
            The name of the attribute (e.g., "shooting", "passing").
        :return:
            The average attribute rating, adjusted by the bonus.
        """
        total = sum(
            getattr(player.attributes, attribute).score
            for player in self.players
        )
        return (total / len(self.players)) * self.bonus if self.players else 0


def distribute_players(
    players: List[Player], team_1_size: int, team_2_size: int
) -> Tuple[List[Player], List[Player]]:
    """
    Distributes players into two teams in a zigzag (draft-pick) manner.

    :param players:
        List of Player objects sorted by overall rating.
    :param team_1_size:
        Desired number of players in Team 1.
    :param team_2_size:
        Desired number of players in Team 2.
    :return:
        A tuple containing two lists: Team 1 players, Team 2 players.
    """
    team_1: List[Player] = []
    team_2: List[Player] = []

    for i, player in enumerate(players):
        if len(team_1) < team_1_size and (
            i % 2 == 0 or len(team_2) >= team_2_size
        ):
            team_1.append(player)
        elif len(team_2) < team_2_size:
            team_2.append(player)

    return team_1, team_2


def apply_team_bonus(team_1: Team, team_2: Team) -> None:
    """
    Applies a 20% rating bonus to the smaller team if team sizes are uneven.

    :param team_1:
        The first team.
    :param team_2:
        The second team.
    """
    if len(team_1.players) > len(team_2.players):  # Team 1 is larger
        team_2.bonus = (
            SMALL_TEAM_BOOST  # Apply a 20% boost to the smaller team
        )
    elif len(team_2.players) > len(team_1.players):  # Team 2 is larger
        team_1.bonus = SMALL_TEAM_BOOST


def create_balanced_teams(
    players: List[Player], team_1_size: int, team_2_size: int
) -> Tuple[Team, Team]:
    """
    Creates two balanced teams based on player ratings.

    :param players:
        List of Player objects to be divided into two teams.
    :param team_1_size:
        The number of players for Team 1.
    :param team_2_size:
        The number of players for Team 2.
    :return:
        A tuple containing two Team objects.
    :raises InvalidTeamSizeError:
        If the total number of players does not match team_1_size + team_2_size.
    """
    if len(players) != team_1_size + team_2_size:
        raise InvalidTeamSizeError(team_1_size, team_2_size, len(players))

    # Sort players by overall rating in descending order
    sorted_players = sorted(
        players, key=lambda x: x.get_overall_rating(), reverse=True
    )

    # Distribute players using the zig-zag method
    team_1_players, team_2_players = distribute_players(
        sorted_players, team_1_size, team_2_size
    )

    # Create team objects
    team_1 = Team(team_1_players)
    team_2 = Team(team_2_players)

    # Apply bonus if team sizes are uneven
    apply_team_bonus(team_1, team_2)

    return team_1, team_2


class InvalidTeamSizeError(Exception):
    """
    Raised when the sum of team sizes does not match the number of players.
    """

    def __init__(self, team_1_size: int, team_2_size: int, num_players: int):
        """
        Initializes the InvalidTeamSizeError.

        :param team_1_size:
            The desired size of Team 1.
        :param team_2_size:
            The desired size of Team 2.
        :param num_players:
            The total number of players provided.
        """
        super().__init__(
            f"The sum of team sizes ({team_1_size + team_2_size}) does not "
            f"match the number of players ({num_players})."
        )
