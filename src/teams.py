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

        :param players:
            List of Player objects.
        :param team_1_size:
            The number of players for Team 1.
        :param team_2_size:
            The number of players for Team 2.
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
        self._precompute_player_differences()

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
            elif len(team_2_players) < self.team_2_size:
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

    def _precompute_player_differences(self) -> None:
        """
        Precomputes and stores the rating differences between every pair of
        players.
        """
        self.swap_heap = []
        for i in range(len(self.players)):
            for j in range(i + 1, len(self.players)):
                diff = abs(
                    self.players[i].get_overall_rating()
                    - self.players[j].get_overall_rating()
                )
                heapq.heappush(self.swap_heap, (diff, i, j))

    def _find_best_swap(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Finds the best swap using the precomputed heap.
        """
        while self.swap_heap:
            _, idx1, idx2 = heapq.heappop(self.swap_heap)
            return idx1, idx2
        return None, None

    def _swap_players(
        self, team1: Team, team2: Team, player1: Player, player2: Player
    ) -> None:
        """
        Swaps two players between teams.
        """
        team1.players.remove(player1)
        team2.players.append(player1)
        team2.players.remove(player2)
        team1.players.append(player2)

    def _can_improve_balance(self) -> bool:
        """
        Determines if further swaps will improve balance.

        :return:
            True if balance can be improved further, False otherwise.
        """
        if not self.swap_heap:
            return False

        # Get the best possible next swap
        next_diff, _, _ = self.swap_heap[0]
        return next_diff < abs(
            self.team_1.get_overall_rating() - self.team_2.get_overall_rating()
        )

    def _adjust_teams_for_fairness(self) -> None:
        """
        Adjusts teams iteratively using **heap-based swaps** to minimize
        imbalance.

        Uses a heap to find and apply the best swap dynamically.
        """
        while self.swap_heap:
            idx1, idx2 = self._find_best_swap()
            if idx1 is None or idx2 is None:
                break  # No valid swaps left

            swap1, swap2 = self.players[idx1], self.players[idx2]

            # Swap players between teams
            if swap1 in self.team_1.players and swap2 in self.team_2.players:
                self._swap_players(self.team_1, self.team_2, swap1, swap2)
            elif swap1 in self.team_2.players and swap2 in self.team_1.players:
                self._swap_players(self.team_2, self.team_1, swap1, swap2)

            # Stop if no swap can further improve balance
            if not self._can_improve_balance():
                break

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
