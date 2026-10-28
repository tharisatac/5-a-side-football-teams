"""
This module holds the app's use-cases: what the app does, such as creating a
match or recording a result. Each one applies the rules (balancing, form
changes, validation) and uses the repository to save and load data.

The CLI calls these functions, and the web API will call the same ones, so
the rules live in one place. Each function takes the repository as an
argument instead of creating one, so tests can pass in a throwaway database.
"""

import csv
from typing import List, Mapping, Sequence, Tuple

from .player import (
    ATTRIBUTE_NAMES,
    DEFAULT_FORM,
    FORM_CHANGE,
    MAX_FORM,
    MIN_FORM,
    Attributes,
    InvalidValueError,
    Player,
)
from .repository import (
    TEAM_KEYS,
    Match,
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerNotFoundError,
    PostgresRepository,
    TeamKey,
)
from .teams import balance_teams

# --------------------------
# Errors
# --------------------------


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


UPDATABLE_FIELDS = ATTRIBUTE_NAMES + ("form",)
CSV_HEADERS = ("name",) + ATTRIBUTE_NAMES + ("form",)


# --------------------------
# Players
# --------------------------


def update_player(
    repo: PostgresRepository, name: str, changes: Mapping[str, int]
) -> Player:
    """
    Changes any of a player's attributes (1-10) and form (0-10) at once.
    Every value is checked before anything is saved, so an invalid value
    leaves the player unchanged.

    :param repo:
        Where players are stored.
    :param name:
        The player's name.
    :param changes:
        Field name to new value, e.g. {"shooting": 9, "form": 6}. Fields
        are attribute names or "form".

    :raises:
        InvalidAttrError: If a field is not an attribute or "form".
        InvalidValueError: If a value is out of range.
        PlayerNotFoundError: If the player does not exist.

    :return:
        The updated player.
    """
    for field in changes:
        if field not in UPDATABLE_FIELDS:
            raise InvalidAttrError(field)

    if "form" in changes:
        form = changes["form"]
        if not MIN_FORM <= form <= MAX_FORM:
            raise InvalidValueError(
                f"Invalid form: {form}. Must be between {MIN_FORM} and "
                f"{MAX_FORM}."
            )
    # Attributes validates the 1-10 range of the attributes being changed.
    Attributes.from_values({k: v for k, v in changes.items() if k != "form"})

    # Only the changed columns are written, so this can't undo a form change
    # made by a match result at the same time.
    repo.update_player(name, changes)
    player = repo.get_player(name)
    if player is None:
        raise PlayerNotFoundError(name)
    return player


# --------------------------
# Matches
# --------------------------


def create_match(
    repo: PostgresRepository, player_names: Sequence[str]
) -> Match:
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


def delete_match(repo: PostgresRepository, match_id: int) -> Match:
    """
    Deletes a match, e.g. to pick teams again or remove a mistake. If it has
    a result, the form changes from that result are undone first.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.

    :raises:
        MatchNotFoundError: If the match does not exist.

    :return:
        The deleted match.
    """
    match = _get_match(repo, match_id)
    repo.delete_match(match_id)
    return match


def swap_players(
    repo: PostgresRepository, match_id: int, name1: str, name2: str
) -> Match:
    """
    Swaps two players between the teams of a match that hasn't been played,
    e.g. to adjust the balanced teams by hand. Team sizes stay the same.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.
    :param name1:
        A player in one team.
    :param name2:
        A player in the other team.

    :raises:
        MatchNotFoundError: If the match does not exist.
        MatchAlreadyRecordedError: If the match has a result.
        InvalidValueError: If a player isn't in the match, or both are in
            the same team.

    :return:
        The match with the players swapped.
    """
    match = _get_match(repo, match_id)
    if match.winner is not None:
        raise MatchAlreadyRecordedError(match_id, match.winner)
    team_of = {
        p.name: key for key in TEAM_KEYS for p in match.team(key).players
    }
    for name in (name1, name2):
        if name not in team_of:
            raise InvalidValueError(f"'{name}' isn't in match #{match_id}.")
    if team_of[name1] == team_of[name2]:
        raise InvalidValueError(
            f"'{name1}' and '{name2}' are in the same team."
        )

    repo.swap_players(match_id, name1, name2)
    return _get_match(repo, match_id)


# --------------------------
# Results
# --------------------------


def record_result(
    repo: PostgresRepository, match_id: int, winner: TeamKey
) -> Match:
    """
    Records which team won a match, or changes it if a different winner was
    recorded before. Players' current form moves by FORM_CHANGE: up for the
    winners, down for the losers; the previous result's changes are undone
    first. The match's own snapshot of each player is left as it was.

    Idempotent: recording the same winner again does nothing and succeeds,
    so a retried request can't change anyone's form twice.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.
    :param winner:
        "team1" or "team2".

    :raises:
        InvalidValueError: If `winner` is not "team1" or "team2".
        MatchNotFoundError: If the match does not exist.

    :return:
        The match, with its winner set.
    """
    if winner not in TEAM_KEYS:
        raise InvalidValueError(
            f"Winner must be 'team1' or 'team2', got '{winner}'."
        )
    repo.set_result(match_id, winner, FORM_CHANGE)
    return _get_match(repo, match_id)


def clear_result(repo: PostgresRepository, match_id: int) -> Match:
    """
    Marks a match as not played, undoing the form changes from its result.
    Does nothing if it has no result.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID.

    :raises:
        MatchNotFoundError: If the match does not exist.

    :return:
        The match, with no winner.
    """
    repo.set_result(match_id, None, FORM_CHANGE)
    return _get_match(repo, match_id)


def _get_match(repo: PostgresRepository, match_id: int) -> Match:
    """
    Returns the match.

    :param repo:
        Where matches are stored.
    :param match_id:
        The match ID.

    :raises:
        MatchNotFoundError: If the match does not exist.
    """
    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    return match


# --------------------------
# Import / export
# --------------------------


def export_players(repo: PostgresRepository, filename: str) -> int:
    """
    Writes all players to a CSV file.

    :param repo:
        Where the players are read from.
    :param filename:
        The CSV file to write. It is overwritten if it exists.

    :raises:
        OSError: If the file cannot be written.

    :return:
        The number of players written.
    """
    players = repo.list_players()
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for player in players:
            values = player.attributes.to_values()
            writer.writerow(
                [player.name]
                + [values[name] for name in ATTRIBUTE_NAMES]
                + [player.form]
            )
    return len(players)


def import_players(
    repo: PostgresRepository, filename: str
) -> Tuple[int, List[Tuple[str, Exception]]]:
    """
    Adds every player in a CSV file. A bad row is skipped rather than stopping
    the import. Extra columns (such as an old `id` column) are ignored.

    :param repo:
        Where the players are added.
    :param filename:
        The CSV file to read.

    :raises:
        FileNotFoundError: If the file does not exist.

    :return:
        The number of players imported, and a (name, error) pair for each
        row that was skipped.
    """
    imported = 0
    errors: List[Tuple[str, Exception]] = []
    with open(filename, mode="r", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("name") or "<unknown>"
            try:
                attributes = Attributes.from_values(
                    {attr: int(row[attr]) for attr in ATTRIBUTE_NAMES}
                )
                form = int(row.get("form") or DEFAULT_FORM)
                repo.add_player(
                    Player(name=row["name"], attributes=attributes, form=form)
                )
                imported += 1
            except Exception as exc:
                errors.append((name, exc))
    return imported, errors
