"""
This module stores players and matches in SQLite, and defines the `Match`
type and the errors storage can raise.

`SqliteRepository` only saves and loads data: no team balancing, no form
calculations and no printing. Every public method opens its own connection and
runs as a single transaction, so a method either makes all of its changes or
none of them.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Literal, Optional, Sequence

from .player import ATTRIBUTE_NAMES, Attributes, Player
from .teams import Team

TeamKey = Literal["team1", "team2"]
TEAM_KEYS: tuple[TeamKey, ...] = ("team1", "team2")

# Absolute paths in the project folder, so the CLI finds the same database
# whichever folder it is run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = str(PROJECT_ROOT / "football.db")
SCHEMA_SQL = (PROJECT_ROOT / "schema.sql").read_text()

# Column names are fixed constants, so it is safe to build SQL from them.
# Values are always passed separately as `?` parameters.
_PLAYER_COLUMNS = ("name",) + ATTRIBUTE_NAMES + ("form",)
_TEAM_NUMBERS: Dict[TeamKey, int] = {"team1": 1, "team2": 2}
_WINNERS: Dict[int, TeamKey] = {1: "team1", 2: "team2"}


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


class SqliteRepository:
    """
    Stores players and matches in a SQLite database file.
    """

    def __init__(self, path: str = DEFAULT_DB_PATH):
        """
        Opens (or creates) the database and creates any missing tables.

        :param path:
            The database file. Defaults to football.db in the project folder.
        """
        self.path = path
        self._create_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """
        Yields a connection with foreign keys enforced. Commits if the block
        succeeds, rolls back if it raises, and always closes the connection.
        """
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            # SQLite ignores FOREIGN KEY constraints unless this is set, and
            # it has to be set again on every new connection.
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn
        finally:
            conn.close()

    # --------------------------
    # Players
    # --------------------------

    def add_player(self, player: Player) -> None:
        """
        Adds a new player.

        :param player:
            The player to add.

        :raises:
            PlayerAlreadyExistsError: If the name is taken.
        """
        columns = ", ".join(_PLAYER_COLUMNS)
        placeholders = ", ".join("?" for _ in _PLAYER_COLUMNS)
        try:
            with self._connect() as conn:
                conn.execute(
                    f"INSERT INTO players ({columns}) VALUES ({placeholders})",
                    _player_values(player),
                )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: players.name" in str(exc):
                raise PlayerAlreadyExistsError(player.name) from exc
            raise

    def get_player(self, name: str) -> Optional[Player]:
        """
        Returns the player, or None if there is no player with that name.

        :param name:
            The player's name.
        """
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {', '.join(_PLAYER_COLUMNS)} FROM players "
                "WHERE name = ?",
                (name,),
            ).fetchone()
        return None if row is None else _row_to_player(row)

    def list_players(self) -> List[Player]:
        """
        Returns all players in the order they were added.
        """
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_PLAYER_COLUMNS)} FROM players "
                "ORDER BY id"
            ).fetchall()
        return [_row_to_player(row) for row in rows]

    def update_player(self, player: Player) -> None:
        """
        Overwrites the stored attributes and form of a player, by name.

        :param player:
            The player with their new values.

        :raises:
            PlayerNotFoundError: If the player does not exist.
        """
        assignments = ", ".join(f"{col} = ?" for col in _PLAYER_COLUMNS[1:])
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE players SET {assignments} WHERE name = ?",
                _player_values(player)[1:] + (player.name,),
            )
            if cur.rowcount == 0:
                raise PlayerNotFoundError(player.name)

    def remove_player(self, name: str) -> None:
        """
        Removes a player who has never played in a match.

        :param name:
            The player's name.

        :raises:
            PlayerNotFoundError: If the player does not exist.
            PlayerHasMatchesError: If the player is in any match.
        """
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM players WHERE name = ?", (name,)
                )
                if cur.rowcount == 0:
                    raise PlayerNotFoundError(name)
        except sqlite3.IntegrityError as exc:
            # The ON DELETE RESTRICT on match_players.player_id refused it.
            if "FOREIGN KEY constraint failed" in str(exc):
                raise PlayerHasMatchesError(name) from exc
            raise

    def reset_forms(self, form: int) -> None:
        """
        Sets every player's form to the same value.

        :param form:
            The new form (0-10).
        """
        with self._connect() as conn:
            conn.execute("UPDATE players SET form = ?", (form,))

    # --------------------------
    # Matches
    # --------------------------

    def create_match(self, team1: Team, team2: Team) -> int:
        """
        Stores a new match with no result. Each player's skills and form are
        saved with the match as a snapshot.

        :param team1:
            The first team.
        :param team2:
            The second team.

        :raises:
            PlayerNotFoundError: If a team contains an unknown player.

        :return:
            The new match's ID.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO matches (team_1_bonus, team_2_bonus) "
                "VALUES (?, ?)",
                (team1.bonus, team2.bonus),
            )
            match_id = cur.lastrowid
            assert match_id is not None

            snapshot = ", ".join(_PLAYER_COLUMNS[1:])
            placeholders = ", ".join("?" for _ in _PLAYER_COLUMNS[1:])

            for team_number, team in ((1, team1), (2, team2)):
                for player in team.players:
                    cur = conn.execute(
                        "INSERT INTO match_players "
                        f"(match_id, player_id, team_number, {snapshot}) "
                        f"SELECT ?, id, ?, {placeholders} "
                        "FROM players WHERE name = ?",
                        (match_id, team_number)
                        + _player_values(player)[1:]
                        + (player.name,),
                    )
                    if cur.rowcount == 0:
                        raise PlayerNotFoundError(player.name)
        return match_id

    def get_match(self, match_id: int) -> Optional[Match]:
        """
        Returns the match, or None if there is no match with that ID.

        :param match_id:
            The match ID.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM matches WHERE id = ?", (match_id,)
            ).fetchone()
            return None if row is None else _load_match(conn, row)

    def get_latest_match(self) -> Optional[Match]:
        """
        Returns the most recently created match, or None if there are none.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM matches ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return None if row is None else _load_match(conn, row)

    def cancel_match(self, match_id: int) -> None:
        """
        Deletes a match that has no result yet. Its `match_players` rows are
        deleted too, by the ON DELETE CASCADE on `match_players.match_id`.

        :param match_id:
            The match ID.

        :raises:
            MatchNotFoundError: If the match does not exist.
            MatchAlreadyRecordedError: If the match already has a result.
        """
        with self._connect() as conn:
            # `winner IS NULL` means a recorded match is never deleted.
            cur = conn.execute(
                "DELETE FROM matches WHERE id = ? AND winner IS NULL",
                (match_id,),
            )
            if cur.rowcount == 0:
                _raise_for_unchangeable_match(conn, match_id)

    def record_result(
        self, match_id: int, winner: TeamKey, players: Sequence[Player]
    ) -> None:
        """
        Saves the winner and the players' updated forms in one transaction.

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
        with self._connect() as conn:
            # `winner IS NULL` makes this a no-op for an already-recorded
            # match, so a result can never be applied twice even if two
            # requests race each other.
            cur = conn.execute(
                "UPDATE matches SET winner = ? "
                "WHERE id = ? AND winner IS NULL",
                (_TEAM_NUMBERS[winner], match_id),
            )
            if cur.rowcount == 0:
                _raise_for_unchangeable_match(conn, match_id)

            conn.executemany(
                "UPDATE players SET form = ? WHERE name = ?",
                [(player.form, player.name) for player in players],
            )

    # --------------------------
    # Database
    # --------------------------

    def clear(self) -> None:
        """
        Deletes all players and matches.
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM match_players")
            conn.execute("DELETE FROM matches")
            conn.execute("DELETE FROM players")

    def _create_schema(self) -> None:
        """
        Creates any missing tables. Safe to run on every start, because
        every statement in schema.sql uses IF NOT EXISTS.
        """
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)


def _raise_for_unchangeable_match(
    conn: sqlite3.Connection, match_id: int
) -> None:
    """
    Called when an update or delete limited to `winner IS NULL` matched no
    rows: raises the error explaining why.

    :param conn:
        The open connection.
    :param match_id:
        The match ID.

    :raises:
        MatchNotFoundError: If the match does not exist.
        MatchAlreadyRecordedError: If the match already has a result.
    """
    row = conn.execute(
        "SELECT winner FROM matches WHERE id = ?", (match_id,)
    ).fetchone()
    if row is None:
        raise MatchNotFoundError(match_id)
    raise MatchAlreadyRecordedError(match_id, _WINNERS[row["winner"]])


def _player_values(player: Player) -> tuple:
    """
    Returns the player's values in `_PLAYER_COLUMNS` order.

    :param player:
        The player.
    """
    values = player.attributes.to_values()
    return (
        (player.name,)
        + tuple(values[name] for name in ATTRIBUTE_NAMES)
        + (player.form,)
    )


def _row_to_player(row: sqlite3.Row) -> Player:
    """
    Builds a Player from a row containing `_PLAYER_COLUMNS`.

    :param row:
        A row from `players` or `match_players` (joined with the name).
    """
    attributes = Attributes.from_values(
        {name: row[name] for name in ATTRIBUTE_NAMES}
    )
    return Player(name=row["name"], attributes=attributes, form=row["form"])


def _load_match(conn: sqlite3.Connection, row: sqlite3.Row) -> Match:
    """
    Builds a Match from a `matches` row by loading its players. Skills and
    form come from the snapshot taken when the match was created.

    :param conn:
        The open connection.
    :param row:
        A row from `matches`.
    """
    columns = ", ".join(
        ["p.name"] + [f"mp.{col}" for col in _PLAYER_COLUMNS[1:]]
    )
    player_rows = conn.execute(
        f"SELECT mp.team_number, {columns} FROM match_players mp "
        "JOIN players p ON p.id = mp.player_id "
        "WHERE mp.match_id = ? ORDER BY mp.rowid",
        (row["id"],),
    ).fetchall()

    team1 = Team([], row["team_1_bonus"])
    team2 = Team([], row["team_2_bonus"])
    for player_row in player_rows:
        team = team1 if player_row["team_number"] == 1 else team2
        team.players.append(_row_to_player(player_row))

    winner = None if row["winner"] is None else _WINNERS[row["winner"]]
    # SQLite's CURRENT_TIMESTAMP is UTC text, e.g. "2026-10-28 14:05:00".
    created_at = datetime.fromisoformat(row["created_at"]).replace(
        tzinfo=timezone.utc
    )
    return Match(
        id=row["id"],
        team1=team1,
        team2=team2,
        created_at=created_at,
        winner=winner,
    )


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
