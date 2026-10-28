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

    :raises PlayerNotFoundError: If a name does not exist.
    :raises DuplicatePlayerError: If a name is given more than once.
    :raises NotEnoughPlayersError: If fewer than 2 names are given.
    """
    players: List[Player] = []
    for name in player_names:
        player = repo.get_player(name)
        if player is None:
            raise PlayerNotFoundError(name)
        players.append(player)

    team1, team2 = balance_teams(players)
    match_id = repo.create_match(team1, team2)
    return Match(id=match_id, team1=team1, team2=team2)


def record_result(repo: Repository, match_id: int, winner: TeamKey) -> Match:
    """
    Records which team won a match and updates every player's form: +1 for
    the winners and -1 for the losers.

    :raises ValueError: If `winner` is not "team1" or "team2".
    :raises MatchNotFoundError: If the match does not exist.
    :raises MatchAlreadyRecordedError: If the match already has a result.
    """
    if winner not in TEAM_KEYS:
        raise ValueError(f"Winner must be 'team1' or 'team2', got '{winner}'.")

    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    if match.winner is not None:
        raise MatchAlreadyRecordedError(match_id, match.winner)

    team1_won = winner == "team1"
    for player in match.team1.players:
        player.update_form(won=team1_won)
    for player in match.team2.players:
        player.update_form(won=not team1_won)

    repo.record_result(
        match_id, winner, match.team1.players + match.team2.players
    )
    match.winner = winner
    return match


def update_player_field(
    repo: Repository, name: str, field: str, value: int
) -> Player:
    """
    Sets one attribute (1-10) or the form (0-10) of a player.

    :raises InvalidAttrError: If `field` is not an attribute or "form".
    :raises ValueError: If `value` is out of range.
    :raises PlayerNotFoundError: If the player does not exist.
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
