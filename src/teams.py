"""
This module defines the `Team` class and `TeamCreator` for creating balanced 
teams efficiently. Teams are balanced based on overall player ratings, and if 
one team is smaller, a boost is applied to the larger team.
"""

import heapq
from typing import List, Optional, Tuple

from .player import Player

LARGE_TEAM_BOOST = 1.2


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
        self.bonus = bonus

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


class TeamCreator:
    """
    Handles the creation and balancing of teams, maintaining a heap to store
    the best swaps dynamically.
    """

    def __init__(
        self, players: List[Player], team_1_size: int, team_2_size: int
    ):
        """
        Initializes the TeamCreator with player data and team sizes.
        """
        if len(players) != team_1_size + team_2_size:
            raise InvalidTeamSizeError(team_1_size, team_2_size, len(players))

        self.players = players
        self.team_1_size = team_1_size
        self.team_2_size = team_2_size
        self.swap_heap: List[
            Tuple[float, int, int]
        ] = []  # Min-heap for storing optimal swaps

        # Create initial teams
        self.team_1, self.team_2 = self._distribute_players()
        self._apply_team_bonus()
        self._precompute_valid_swaps()

    def _distribute_players(self) -> Tuple[Team, Team]:
        """
        Distributes players into two teams using a zigzag method.
        """
        sorted_players = sorted(
            self.players, key=lambda x: x.get_overall_rating(), reverse=True
        )
        team_1_players: List[Player] = []
        team_2_players: List[Player] = []

        for i, player in enumerate(sorted_players):
            if len(team_1_players) < self.team_1_size and (
                i % 2 == 0 or len(team_2_players) >= self.team_2_size
            ):
                team_1_players.append(player)
            else:
                team_2_players.append(player)

        return Team(team_1_players), Team(team_2_players)

    def _apply_team_bonus(self) -> None:
        """
        Applies a rating bonus to the larger team if team sizes are uneven.
        """
        if len(self.team_1.players) > len(self.team_2.players):
            self.team_1.bonus = LARGE_TEAM_BOOST
        elif len(self.team_2.players) > len(self.team_1.players):
            self.team_2.bonus = LARGE_TEAM_BOOST

    def _precompute_valid_swaps(self) -> None:
        """
        Precomputes and stores only valid swaps between players on opposite teams.
        """
        self.swap_heap = []
        for i, player1 in enumerate(self.team_1.players):
            for j, player2 in enumerate(self.team_2.players):
                diff = abs(
                    player1.get_overall_rating() - player2.get_overall_rating()
                )
                heapq.heappush(self.swap_heap, (diff, i, j))

    def _swap_players(self, idx1: int, idx2: int) -> None:
        """
        Swaps two players between teams based on their indices.
        """
        self.team_1.players[idx1], self.team_2.players[idx2] = (
            self.team_2.players[idx2],
            self.team_1.players[idx1],
        )

    def _team_rating_diff(self) -> float:
        """
        Determines the absolute difference between the two teams' ratings.
        """
        return abs(
            self.team_1.get_overall_rating() - self.team_2.get_overall_rating()
        )

    def _can_improve_balance(self) -> bool:
        """
        Determines if further swaps will improve balance.
        """
        best_diff_seen = self._team_rating_diff()
        can_improve = False

        for idx1 in range(len(self.team_1.players)):
            for idx2 in range(len(self.team_2.players)):
                self._swap_players(idx1, idx2)
                new_diff = self._team_rating_diff()

                if new_diff < best_diff_seen:
                    best_diff_seen = new_diff
                    can_improve = True

                self._swap_players(idx1, idx2)  # Undo swap

        return can_improve

    def _adjust_teams_for_fairness(self) -> None:
        """
        Adjusts teams iteratively using heap-based swaps to minimize imbalance.
        """
        while self._can_improve_balance():
            idx1, idx2 = self._find_best_swap()
            if idx1 is None or idx2 is None:
                break

            self._swap_players(idx1, idx2)

    def _find_best_swap(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Finds the best swap by checking the heap for valid swaps.
        """
        while self.swap_heap:
            _, idx1, idx2 = heapq.heappop(self.swap_heap)
            if idx1 < len(self.team_1.players) and idx2 < len(
                self.team_2.players
            ):
                return idx1, idx2
        return None, None

    def create_balanced_teams(self) -> Tuple[Team, Team]:
        """
        Returns the balanced teams after applying fairness adjustments.
        """
        self._adjust_teams_for_fairness()
        return self.team_1, self.team_2


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
