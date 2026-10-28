"""
This module defines the storage interface ("repository") the rest of the app
talks to, plus the `Match` type and the errors a repository can raise.

Code that needs to save or load data depends on `Repository`, not on a
concrete database, so SQLite can later be swapped for Postgres without
touching the CLI or the business logic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal, Optional, Protocol, Sequence

from .player import Player
from .teams import Team

TeamKey = Literal["team1", "team2"]
TEAM_KEYS: tuple[TeamKey, ...] = ("team1", "team2")


@dataclass
class Match:
    """
    A generated pair of teams, and the result once it has been recorded.

    Attributes:
        id : Unique match ID assigned by the repository.
        team1 : The first team.
        team2 : The second team.
        created_at : When the teams were made (timezone-aware, UTC).
        winner : "team1" or "team2" once recorded, otherwise None.
    """

    id: int
    team1: Team
    team2: Team
    created_at: datetime
    winner: Optional[TeamKey] = None

    def team(self, key: TeamKey) -> Team:
        """
        Returns the team for "team1" or "team2".

        :param key:
            "team1" or "team2".
        """
        return self.team1 if key == "team1" else self.team2


class Repository(Protocol):
    """
    Everything the app needs from storage. Any class with these methods counts
    as a Repository; it does not need to inherit from this class.
    """

    def add_player(self, player: Player) -> None:
        """
        Adds a new player.

        :param player:
            The player to add.

        :raises:
            PlayerAlreadyExistsError: If the name is taken.
        """
        ...

    def get_player(self, name: str) -> Optional[Player]:
        """
        Returns the player, or None if there is no player with that name.

        :param name:
            The player's name.
        """
        ...

    def list_players(self) -> List[Player]:
        """
        Returns all players in the order they were added.
        """
        ...

    def update_player(self, player: Player) -> None:
        """
        Overwrites the stored attributes and form of a player, by name.

        :param player:
            The player with their new values.

        :raises:
            PlayerNotFoundError: If the player does not exist.
        """
        ...

    def remove_player(self, name: str) -> None:
        """
        Removes a player who has never played in a match.

        :param name:
            The player's name.

        :raises:
            PlayerNotFoundError: If the player does not exist.
            PlayerHasMatchesError: If the player is in any match.
        """
        ...

    def reset_forms(self, form: int) -> None:
        """
        Sets every player's form to the same value.

        :param form:
            The new form (0-10).
        """
        ...

    def create_match(self, team1: Team, team2: Team) -> int:
        """
        Stores a new match with no result. The players' skills and form are
        stored with it, so the match keeps them even if the players change
        later.

        :param team1:
            The first team.
        :param team2:
            The second team.

        :raises:
            PlayerNotFoundError: If a team contains an unknown player.

        :return:
            The new match's ID.
        """
        ...

    def get_match(self, match_id: int) -> Optional[Match]:
        """
        Returns the match, or None if there is no match with that ID. Its
        players have the skills and form they had when it was created.

        :param match_id:
            The match ID.
        """
        ...

    def get_latest_match(self) -> Optional[Match]:
        """
        Returns the most recently created match, or None if there are none.
        """
        ...

    def cancel_match(self, match_id: int) -> None:
        """
        Deletes a match that has no result yet, along with its players' rows.

        :param match_id:
            The match ID.

        :raises:
            MatchNotFoundError: If the match does not exist.
            MatchAlreadyRecordedError: If the match already has a result.
        """
        ...

    def record_result(
        self, match_id: int, winner: TeamKey, players: Sequence[Player]
    ) -> None:
        """
        Saves the winner and the players' updated (current) forms as a single
        change: either both are saved or neither is.

        :param match_id:
            The match ID.
        :param winner:
            "team1" or "team2".
        :param players:
            The players with their new forms.

        :raises:
            MatchNotFoundError: If the match does not exist.
            MatchAlreadyRecordedError: If the match already has a result.
        """
        ...

    def clear(self) -> None:
        """
        Deletes all players and matches.
        """
        ...


class PlayerNotFoundError(Exception):
    """
    Raised when a player name does not exist.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the PlayerNotFoundError.

        :param name:
            The name of the unknown player.
        """
        self.name = name
        super().__init__(f"Unknown player '{name}'.")


class PlayerHasMatchesError(Exception):
    """
    Raised when removing a player who has played in a match.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the PlayerHasMatchesError.

        :param name:
            The name of the player.
        """
        self.name = name
        super().__init__(
            f"Player '{name}' has played in a match and can't be removed."
        )


class PlayerAlreadyExistsError(Exception):
    """
    Raised when adding a player whose name is already taken.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the PlayerAlreadyExistsError.

        :param name:
            The name that is already taken.
        """
        self.name = name
        super().__init__(f"Player '{name}' already exists.")


class MatchNotFoundError(Exception):
    """
    Raised when a match ID does not exist.
    """

    def __init__(self, match_id: Optional[int]) -> None:
        """
        Initializes the MatchNotFoundError.

        :param match_id:
            The unknown match ID, or None if there are no matches at all.
        """
        self.match_id = match_id
        if match_id is None:
            super().__init__("No matches found. Create teams first.")
        else:
            super().__init__(f"Match #{match_id} not found.")


class MatchAlreadyRecordedError(Exception):
    """
    Raised when recording a result for a match that already has one.
    """

    def __init__(self, match_id: int, winner: Optional[str] = None) -> None:
        """
        Initializes the MatchAlreadyRecordedError.

        :param match_id:
            The match ID.
        :param winner:
            The result that was already recorded, if known.
        """
        self.match_id = match_id
        self.winner = winner
        message = f"Match #{match_id} already has a result"
        if winner is not None:
            message += f" ({winner} won)"
        super().__init__(message + ".")
