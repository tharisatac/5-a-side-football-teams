"""
This module defines the `create_balanced_teams` function, which creates two 
balanced teams based on player ratings. If there is a difference in team sizes 
(e.g., 5v4), a 20% bonus is applied to the smaller team to offset the numerical 
advantage of the larger team.

The teams are balanced based on overall player ratings, and players are sorted 
and distributed alternately to achieve the most skill-balanced teams possible.

Function:
    - create_balanced_teams: Creates two balanced teams based on player ratings 
      and varying team sizes. If one team has an extra player, a 20% bonus is 
      applied to the smaller team.
"""

from typing import List

from .player import Player


class InvalidTeamSizeError(Exception):
    """
    An error raised when the sum of team sizes doesn't match the number of
    players.
    """

    def __init__(self, team_1_size: int, team_2_size: int, num_players: int):
        super().__init__(
            f"The sum of team sizes ({team_1_size + team_2_size}) does not "
            f"match the number of players ({num_players})."
        )


def create_balanced_teams(
    players: List[Player], team_1_size: int = 5, team_2_size: int = 5
):
    """
    Create balanced teams based on player ratings and varying team sizes.
    If one team has an extra player, a 20% bonus is applied to the smaller team.

    :param players:
        List of Player objects to be divided into two teams.
    :param team_1_size:
        The number of players for team 1 (default is 5).
    :param team_2_size:
        The number of players for team 2 (default is 5).

    :return:
        A tuple containing two lists:
        - team_1: List of Player objects for team 1.
        - team_2: List of Player objects for team 2.
    """
    if len(players) != team_1_size + team_2_size:
        raise InvalidTeamSizeError(team_1_size, team_2_size, len(players))

    # Sort players by overall rating in descending order
    sorted_players = sorted(
        players, key=lambda x: x.get_overall_rating(), reverse=True
    )

    # Distribute players into teams alternately
    team_1 = sorted_players[:team_1_size]
    team_2 = sorted_players[team_1_size : team_1_size + team_2_size]

    # Apply bonus to the smaller team if necessary
    team_1_rating = sum(player.get_overall_rating() for player in team_1)
    team_2_rating = sum(player.get_overall_rating() for player in team_2)

    if len(team_1) > len(team_2):  # Team 1 is larger
        team_2_bonus = team_2_rating * 0.20
        team_2_rating += team_2_bonus
    elif len(team_2) > len(team_1):  # Team 2 is larger
        team_1_bonus = team_1_rating * 0.20
        team_1_rating += team_1_bonus

    return team_1, team_2
