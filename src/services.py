"""
This module holds the app's use-cases: the steps that combine the balancer,
the player rules and storage. Each function takes the repository as an
argument instead of creating one, so the CLI (and later the API) decides which
storage to use, and tests can pass in a throwaway database.
"""

from typing import List, Sequence

from .player import ATTRIBUTE_NAMES, MAX_FORM, MIN_FORM, Attributes, Player
from .repository import (
    TEAM_KEYS,
    Match,
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerNotFoundError,
    Repository,
    TeamKey,
)
from .teams import balance_teams

UPDATABLE_FIELDS = ATTRIBUTE_NAMES + ("form",)


def create_match(repo: Repository, player_names: Sequence[str]) -> Match:
    """
    Looks up the named players, balances them into two teams and stores the
    result as a new match.

    :param repo:
        Where players and matches are stored.
    :param player_names:
        The names of the players taking part.

    :raises:
        PlayerNotFoundError: If a name does not exist.
        DuplicatePlayerError: If a name is given more than once.
        NotEnoughPlayersError: If fewer than 2 names are given.

    :return:
        The new match.
    """
    players: List[Player] = []
    for name in player_names:
        player = repo.get_player(name)
        if player is None:
            raise PlayerNotFoundError(name)
        players.append(player)

    team1, team2 = balance_teams(players)
    match_id = repo.create_match(team1, team2)
    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    return match


def record_result(repo: Repository, match_id: int, winner: TeamKey) -> Match:
    """
    Records which team won a match and updates every player's current form:
    +1 for the winners and -1 for the losers. The match's own snapshot of
    each player is left as it was.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.
    :param winner:
        "team1" or "team2".

    :raises:
        ValueError: If `winner` is not "team1" or "team2".
        MatchNotFoundError: If the match does not exist.
        MatchAlreadyRecordedError: If the match already has a result.

    :return:
        The match, with its winner set.
    """
    if winner not in TEAM_KEYS:
        raise ValueError(f"Winner must be 'team1' or 'team2', got '{winner}'.")

    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    if match.winner is not None:
        raise MatchAlreadyRecordedError(match_id, match.winner)

    # Start from each player's current form, not the match snapshot: their
    # form may have changed since, e.g. if another match was recorded first.
    updated: List[Player] = []
    for key in TEAM_KEYS:
        for snapshot in match.team(key).players:
            player = repo.get_player(snapshot.name)
            if player is None:
                raise PlayerNotFoundError(snapshot.name)
            player.update_form(won=key == winner)
            updated.append(player)

    repo.record_result(match_id, winner, updated)
    match.winner = winner
    return match


def cancel_match(repo: Repository, match_id: int) -> Match:
    """
    Deletes a match that hasn't been played, e.g. to pick teams again. A
    match with a result can't be cancelled, so history stays complete.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.

    :raises:
        MatchNotFoundError: If the match does not exist.
        MatchAlreadyRecordedError: If the match already has a result.

    :return:
        The cancelled match.
    """
    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    if match.winner is not None:
        raise MatchAlreadyRecordedError(match_id, match.winner)

    repo.cancel_match(match_id)
    return match


def update_player_field(
    repo: Repository, name: str, field: str, value: int
) -> Player:
    """
    Sets one attribute (1-10) or the form (0-10) of a player.

    :param repo:
        Where players are stored.
    :param name:
        The player's name.
    :param field:
        An attribute name such as "shooting", or "form".
    :param value:
        The new value.

    :raises:
        InvalidAttrError: If `field` is not an attribute or "form".
        ValueError: If `value` is out of range.
        PlayerNotFoundError: If the player does not exist.

    :return:
        The updated player.
    """
    if field not in UPDATABLE_FIELDS:
        raise InvalidAttrError(field)

    player = repo.get_player(name)
    if player is None:
        raise PlayerNotFoundError(name)

    if field == "form":
        if not MIN_FORM <= value <= MAX_FORM:
            raise ValueError(
                f"Invalid form: {value}. Must be between {MIN_FORM} and "
                f"{MAX_FORM}."
            )
        player.form = value
    else:
        values = player.attributes.to_values()
        values[field] = value
        # Attributes validates the 1-10 range.
        player.attributes = Attributes.from_values(values)

    repo.update_player(player)
    return player


class InvalidAttrError(Exception):
    """
    Raised when an invalid attribute is passed in.
    """

    def __init__(self, attr: str):
        """
        Initializes the InvalidAttrError.

        :param attr:
            The invalid attribute.

        """
        self.attr = attr
        super().__init__(f"Invalid attribute '{attr}' passed in.")
