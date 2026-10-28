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
from typing import Dict, Iterator, List, Literal, Mapping, Optional

from .player import ATTRIBUTE_NAMES, MAX_FORM, MIN_FORM, Attributes, Player
from .teams import Team

# --------------------------
# Errors
# --------------------------


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
                    self._player_values(player),
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
        return None if row is None else self._row_to_player(row)

    def list_players(self) -> List[Player]:
        """
        Returns all players in the order they were added.
        """
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_PLAYER_COLUMNS)} FROM players "
                "ORDER BY id"
            ).fetchall()
        return [self._row_to_player(row) for row in rows]

    def update_player(self, name: str, changes: Mapping[str, int]) -> None:
        """
        Sets some of a player's attributes and/or form. Only the given columns
        are written, so a change made at the same time to another column
        (e.g. form, by a match result) isn't overwritten.

        :param name:
            The player's name.
        :param changes:
            Column name to new value, e.g. {"shooting": 9}. Must already be
            validated.

        :raises:
            PlayerNotFoundError: If the player does not exist.
        """
        # Only known column names are put into the SQL itself; values are
        # passed separately as `?` parameters.
        columns = [col for col in _PLAYER_COLUMNS[1:] if col in changes]
        if len(columns) != len(changes):
            raise ValueError(f"Unknown columns in {sorted(changes)}")
        with self._connect() as conn:
            if not columns:
                found = conn.execute(
                    "SELECT 1 FROM players WHERE name = ?", (name,)
                ).fetchone()
            else:
                assignments = ", ".join(f"{col} = ?" for col in columns)
                found = conn.execute(
                    f"UPDATE players SET {assignments} WHERE name = ?",
                    [changes[col] for col in columns] + [name],
                ).rowcount
            if not found:
                raise PlayerNotFoundError(name)

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
                for position, player in enumerate(team.players):
                    cur = conn.execute(
                        "INSERT INTO match_players (match_id, player_id, "
                        f"team_number, position, {snapshot}) "
                        f"SELECT ?, id, ?, ?, {placeholders} "
                        "FROM players WHERE name = ?",
                        (match_id, team_number, position)
                        + self._player_values(player)[1:]
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
            return None if row is None else self._load_match(conn, row)

    def list_matches(self) -> List[Match]:
        """
        Returns all matches, newest first.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM matches ORDER BY id DESC"
            ).fetchall()
            return [self._load_match(conn, row) for row in rows]

    def get_latest_match(self) -> Optional[Match]:
        """
        Returns the most recently created match, or None if there are none.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM matches ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return None if row is None else self._load_match(conn, row)

    def set_result(
        self, match_id: int, winner: Optional[TeamKey], form_change: int
    ) -> None:
        """
        Records, changes or (with None) clears a match's winner, in one
        transaction. Any form changes from the previous result are undone
        first; then the new winners' form goes up and the losers' down by
        `form_change`, kept within MIN_FORM-MAX_FORM. Setting the winner the
        match already has changes nothing.

        :param match_id:
            The match ID.
        :param winner:
            "team1", "team2", or None for "not played".
        :param form_change:
            How much each player's form moves.

        :raises:
            MatchNotFoundError: If the match does not exist.
        """
        with self._connect() as conn:
            current = self._lock_match(conn, match_id)
            if current == winner:
                return  # Already this result: leave forms alone.
            if current is not None:
                self._undo_form_changes(conn, match_id)
            conn.execute(
                "UPDATE matches SET winner = ? WHERE id = ?",
                (None if winner is None else _TEAM_NUMBERS[winner], match_id),
            )
            if winner is not None:
                self._apply_form_changes(conn, match_id, winner, form_change)

    def delete_match(self, match_id: int) -> None:
        """
        Deletes a match, first undoing any form changes from its result. Its
        `match_players` rows are deleted too, by the ON DELETE CASCADE on
        `match_players.match_id`.

        :param match_id:
            The match ID.

        :raises:
            MatchNotFoundError: If the match does not exist.
        """
        with self._connect() as conn:
            if self._lock_match(conn, match_id) is not None:
                self._undo_form_changes(conn, match_id)
            conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))

    def swap_players(self, match_id: int, name1: str, name2: str) -> None:
        """
        Puts two players in each other's place in a match that hasn't been
        played: each takes the other's team and position in the list. The
        caller checks they are in the match on different teams.

        :param match_id:
            The match ID.
        :param name1:
            A player in one team.
        :param name2:
            A player in the other team.

        :raises:
            MatchNotFoundError: If the match does not exist.
            MatchAlreadyRecordedError: If the match has a result.
        """
        with self._connect() as conn:
            winner = self._lock_match(conn, match_id)
            if winner is not None:
                raise MatchAlreadyRecordedError(match_id, winner)
            spots = conn.execute(
                "SELECT p.name, mp.player_id, mp.team_number, mp.position "
                "FROM match_players mp JOIN players p ON p.id = mp.player_id "
                "WHERE mp.match_id = ? AND p.name IN (?, ?)",
                (match_id, name1, name2),
            ).fetchall()
            first, second = sorted(spots, key=lambda r: r["name"] != name1)
            # Each player takes the other's team and position.
            for player, spot in ((first, second), (second, first)):
                conn.execute(
                    "UPDATE match_players SET team_number = ?, position = ? "
                    "WHERE match_id = ? AND player_id = ?",
                    (
                        spot["team_number"],
                        spot["position"],
                        match_id,
                        player["player_id"],
                    ),
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

    # --------------------------
    # Helpers
    # --------------------------

    def _lock_match(
        self, conn: sqlite3.Connection, match_id: int
    ) -> Optional[TeamKey]:
        """
        Starts the transaction with the write lock taken, so the match can't
        change between this read and the writes that follow, then returns
        its current winner.

        :param conn:
            The open connection, not yet in a transaction.
        :param match_id:
            The match ID.

        :raises:
            MatchNotFoundError: If the match does not exist.

        :return:
            "team1", "team2", or None if the match hasn't been played.
        """
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT winner FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
        if row is None:
            raise MatchNotFoundError(match_id)
        return None if row["winner"] is None else _WINNERS[row["winner"]]

    def _apply_form_changes(
        self,
        conn: sqlite3.Connection,
        match_id: int,
        winner: TeamKey,
        form_change: int,
    ) -> None:
        """
        Moves the winners' form up and the losers' down, and remembers in
        `match_players.form_change` exactly how much each player moved, so
        the result can be undone precisely later. A player already at the
        limit moves by 0.

        :param conn:
            The open connection, in a transaction.
        :param match_id:
            The match ID.
        :param winner:
            "team1" or "team2".
        :param form_change:
            How much each player's form moves.
        """
        for team_number in (1, 2):
            won = team_number == _TEAM_NUMBERS[winner]
            # The actual change: the new form, kept within the limits,
            # minus the current form.
            conn.execute(
                "UPDATE match_players SET form_change = ("
                "SELECT MAX(?, MIN(?, p.form + ?)) - p.form FROM players p "
                "WHERE p.id = match_players.player_id) "
                "WHERE match_id = ? AND team_number = ?",
                (
                    MIN_FORM,
                    MAX_FORM,
                    form_change if won else -form_change,
                    match_id,
                    team_number,
                ),
            )
        # The database does the arithmetic (`form + change`) instead of us
        # reading form, changing it in Python and writing it back, so changes
        # made at the same time can't overwrite each other.
        conn.execute(
            "UPDATE players SET form = form + (SELECT mp.form_change "
            "FROM match_players mp WHERE mp.match_id = ? "
            "AND mp.player_id = players.id) "
            "WHERE id IN (SELECT player_id FROM match_players "
            "WHERE match_id = ?)",
            (match_id, match_id),
        )

    def _undo_form_changes(
        self, conn: sqlite3.Connection, match_id: int
    ) -> None:
        """
        Reverses the form changes a match's result made.

        :param conn:
            The open connection, in a transaction.
        :param match_id:
            The match ID.
        """
        conn.execute(
            "UPDATE players SET form = MAX(?, MIN(?, form - (SELECT "
            "mp.form_change FROM match_players mp WHERE mp.match_id = ? "
            "AND mp.player_id = players.id))) "
            "WHERE id IN (SELECT player_id FROM match_players "
            "WHERE match_id = ?)",
            (MIN_FORM, MAX_FORM, match_id, match_id),
        )
        conn.execute(
            "UPDATE match_players SET form_change = 0 WHERE match_id = ?",
            (match_id,),
        )

    @staticmethod
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

    @staticmethod
    def _row_to_player(row: sqlite3.Row) -> Player:
        """
        Builds a Player from a row containing `_PLAYER_COLUMNS`.

        :param row:
            A row from `players` or `match_players` (joined with the name).
        """
        attributes = Attributes.from_values(
            {name: row[name] for name in ATTRIBUTE_NAMES}
        )
        return Player(
            name=row["name"], attributes=attributes, form=row["form"]
        )

    def _load_match(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Match:
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
            "WHERE mp.match_id = ? ORDER BY mp.team_number, mp.position",
            (row["id"],),
        ).fetchall()

        team1 = Team([], row["team_1_bonus"])
        team2 = Team([], row["team_2_bonus"])
        for player_row in player_rows:
            team = team1 if player_row["team_number"] == 1 else team2
            team.players.append(self._row_to_player(player_row))

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
