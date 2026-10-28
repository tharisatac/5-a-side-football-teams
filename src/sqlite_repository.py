"""
This module provides the SQLite implementation of `Repository`.

It only saves and loads data: no team balancing, no form calculations and no
printing. Every public method opens its own connection and runs as a single
transaction, so a method either makes all of its changes or none of them.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set

from .player import ATTRIBUTE_NAMES, Attributes, Player
from .repository import (
    Match,
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
    TeamKey,
)
from .teams import Team

DEFAULT_DB_PATH = "football.db"

# Bump this and add a migration step in `_migrate` whenever schema.sql
# changes. SQLite stores it in the database file header (`PRAGMA user_version`).
SCHEMA_VERSION = 1
SCHEMA_SQL = (Path(__file__).parent.parent / "schema.sql").read_text()

# Column names are fixed constants, so it is safe to build SQL from them.
# Values are always passed separately as `?` parameters.
_PLAYER_COLUMNS = ("name",) + ATTRIBUTE_NAMES + ("form",)
_TEAM_NUMBERS: Dict[TeamKey, int] = {"team1": 1, "team2": 2}
_WINNERS: Dict[int, TeamKey] = {1: "team1", 2: "team2"}


class SqliteRepository:
    """
    Stores players and matches in a SQLite database file.
    """

    def __init__(self, path: str = DEFAULT_DB_PATH):
        """
        Opens (or creates) the database at `path` and brings its schema up
        to date.
        """
        self.path = path
        self._migrate()

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

        :raises PlayerAlreadyExistsError: If the name is taken.
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
        Overwrites the stored attributes and form of `player`, by name.

        :raises PlayerNotFoundError: If the player does not exist.
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
        Removes the player. Their match appearances are removed too, by the
        ON DELETE CASCADE on `match_players.player_id`.

        :raises PlayerNotFoundError: If the player does not exist.
        """
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM players WHERE name = ?", (name,))
            if cur.rowcount == 0:
                raise PlayerNotFoundError(name)

    def reset_forms(self, form: int) -> None:
        """
        Sets every player's form to `form`.
        """
        with self._connect() as conn:
            conn.execute("UPDATE players SET form = ?", (form,))

    # --------------------------
    # Matches
    # --------------------------

    def create_match(self, team1: Team, team2: Team) -> int:
        """
        Stores a new match with no result and returns its ID.

        :raises PlayerNotFoundError: If a team contains an unknown player.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO matches (team_1_bonus, team_2_bonus) "
                "VALUES (?, ?)",
                (team1.bonus, team2.bonus),
            )
            match_id = cur.lastrowid
            assert match_id is not None

            for team_number, team in ((1, team1), (2, team2)):
                for player in team.players:
                    cur = conn.execute(
                        "INSERT INTO match_players "
                        "(match_id, player_id, team_number) "
                        "SELECT ?, id, ? FROM players WHERE name = ?",
                        (match_id, team_number, player.name),
                    )
                    if cur.rowcount == 0:
                        raise PlayerNotFoundError(player.name)
        return match_id

    def get_match(self, match_id: int) -> Optional[Match]:
        """
        Returns the match, or None if there is no match with that ID.
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

    def record_result(
        self, match_id: int, winner: TeamKey, players: Sequence[Player]
    ) -> None:
        """
        Saves the winner and the players' updated forms in one transaction.

        :raises MatchNotFoundError: If the match does not exist.
        :raises MatchAlreadyRecordedError: If the match already has a result.
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
                row = conn.execute(
                    "SELECT winner FROM matches WHERE id = ?", (match_id,)
                ).fetchone()
                if row is None:
                    raise MatchNotFoundError(match_id)
                raise MatchAlreadyRecordedError(
                    match_id, _WINNERS[row["winner"]]
                )

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

    def _migrate(self) -> None:
        """
        Creates the schema in a new database, or upgrades an older one.

        The whole upgrade runs in one transaction, so a failure leaves the
        file exactly as it was.
        """
        # isolation_level=None stops Python's sqlite3 module from opening and
        # committing transactions on its own; the script below does it
        # explicitly with BEGIN, and we COMMIT once the checks pass.
        conn = sqlite3.connect(self.path, isolation_level=None)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                return
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database '{self.path}' has schema version {version}, "
                    f"newer than this code supports ({SCHEMA_VERSION})."
                )

            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            script = ["BEGIN;"]
            if "players" in tables:
                script.append(_v0_prepare_sql(conn, tables))
            script.append(SCHEMA_SQL)
            if "players" in tables:
                script.append(_v0_copy_sql(tables))
            conn.executescript("\n".join(script))

            # Foreign keys are off on this connection (the default), so
            # check that the copied data is consistent before committing.
            problems = conn.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                raise RuntimeError(f"Foreign key problems: {problems}")
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.execute("COMMIT")
        finally:
            # Closing without COMMIT (e.g. after an error) rolls back.
            conn.close()


def _player_values(player: Player) -> tuple:
    """
    Returns the player's values in `_PLAYER_COLUMNS` order.
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
    """
    attributes = Attributes.from_values(
        {name: row[name] for name in ATTRIBUTE_NAMES}
    )
    return Player(name=row["name"], attributes=attributes, form=row["form"])


def _load_match(conn: sqlite3.Connection, row: sqlite3.Row) -> Match:
    """
    Builds a Match from a `matches` row by loading its players. Players are
    loaded with their current form, not their form at the time of the match.
    """
    columns = ", ".join(f"p.{col}" for col in _PLAYER_COLUMNS)
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
    return Match(id=row["id"], team1=team1, team2=team2, winner=winner)


# --------------------------
# Migration from the pre-versioning schema (the old `DB` class)
# --------------------------


def _v0_prepare_sql(conn: sqlite3.Connection, tables: Set[str]) -> str:
    """
    Moves the old tables out of the way so schema.sql can create new ones.

    The old `match_players` table was never written to, and old `matches`
    rows had no players attached, so neither holds anything worth keeping.
    An old `matches` table that does have rows is kept as `matches_v0`.
    """
    sql = [
        # Dropped first so renaming `players` doesn't rewrite its foreign key.
        "DROP TABLE IF EXISTS match_players;",
        "ALTER TABLE players RENAME TO players_v0;",
    ]
    if "matches" in tables:
        count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        if count == 0:
            sql.append("DROP TABLE matches;")
        else:
            sql.append("ALTER TABLE matches RENAME TO matches_v0;")
    return "\n".join(sql)


def _v0_copy_sql(tables: Set[str]) -> str:
    """
    Copies players into the new table (adding the CHECK constraints) and turns
    any pending `last_teams` into an unrecorded match, so `teams result` still
    works straight after upgrading. Unused old columns (e.g. trueskill_mu)
    are not copied.
    """
    sql = [
        "INSERT INTO players (id, name, shooting, dribbling, passing, "
        "tackling, fitness, goalkeeping, form) "
        "SELECT id, name, shooting, dribbling, passing, tackling, fitness, "
        "goalkeeping, COALESCE(form, 5) FROM players_v0;",
    ]
    if "last_teams" in tables:
        sql += [
            "INSERT INTO matches (team_1_bonus, team_2_bonus) "
            "SELECT "
            "COALESCE(MAX(CASE WHEN team = 'team1' THEN bonus END), 1.0), "
            "COALESCE(MAX(CASE WHEN team = 'team2' THEN bonus END), 1.0) "
            "FROM last_teams HAVING COUNT(*) > 0;",
            "INSERT INTO match_players (match_id, player_id, team_number) "
            "SELECT (SELECT MAX(id) FROM matches), p.id, "
            "CASE lt.team WHEN 'team1' THEN 1 ELSE 2 END "
            "FROM last_teams lt JOIN players p ON p.name = lt.player_name "
            "ORDER BY lt.id;",
            "DROP TABLE last_teams;",
        ]
    sql.append("DROP TABLE players_v0;")
    return "\n".join(sql)
