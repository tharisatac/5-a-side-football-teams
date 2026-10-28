import sqlite3
from test.conftest import make_player

import pytest

from src.repository import (
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from src.sqlite_repository import SCHEMA_VERSION, SqliteRepository
from src.teams import Team

# -------------------------------------------------------------------
# Players
# -------------------------------------------------------------------


def test_add_and_get_player(repo):
    """
    Tests that a stored player comes back with the same values.
    """
    player = make_player("Alice", score=8, form=7)
    repo.add_player(player)

    assert repo.get_player("Alice") == player


def test_add_duplicate_player(repo):
    """
    Tests that adding a name twice raises instead of printing.
    """
    repo.add_player(make_player("Alice"))

    with pytest.raises(PlayerAlreadyExistsError) as exc:
        repo.add_player(make_player("Alice"))

    assert exc.value.name == "Alice"


def test_get_nonexistent_player(repo):
    """
    Tests that an unknown name returns None.
    """
    assert repo.get_player("Nobody") is None


def test_list_players_in_insertion_order(repo, stored_players):
    """
    Tests that list_players returns Player objects in the order added.
    """
    assert repo.list_players() == stored_players


def test_update_player(repo, stored_players):
    """
    Tests that update_player overwrites attributes and form.
    """
    updated = make_player("Player 1", score=3, form=9)
    repo.update_player(updated)

    assert repo.get_player("Player 1") == updated


def test_update_nonexistent_player(repo):
    """
    Tests that updating an unknown player raises.
    """
    with pytest.raises(PlayerNotFoundError):
        repo.update_player(make_player("Nobody"))


def test_remove_player(repo, stored_players):
    """
    Tests removing a player.
    """
    repo.remove_player("Player 1")

    assert repo.get_player("Player 1") is None
    assert len(repo.list_players()) == len(stored_players) - 1


def test_remove_nonexistent_player(repo):
    """
    Tests that removing an unknown player raises instead of silently
    succeeding.
    """
    with pytest.raises(PlayerNotFoundError):
        repo.remove_player("Nobody")


def test_reset_forms(repo, stored_players):
    """
    Tests that every player's form is reset.
    """
    repo.update_player(make_player("Player 1", form=9))
    repo.reset_forms(5)

    assert {p.form for p in repo.list_players()} == {5}


# -------------------------------------------------------------------
# Matches
# -------------------------------------------------------------------


def test_create_and_get_match(repo, stored_players):
    """
    Tests that a stored match comes back with the same teams and bonuses.
    """
    team1 = Team(stored_players[:1], 1.2)
    team2 = Team(stored_players[1:], 1.0)

    match_id = repo.create_match(team1, team2)
    match = repo.get_match(match_id)

    assert match is not None
    assert match.id == match_id
    assert match.team1 == team1
    assert match.team2 == team2
    assert match.winner is None


def test_match_ids_are_unique(repo, stored_players):
    """
    Tests that each match gets its own ID, so older matches stay reachable.
    """
    teams = (Team(stored_players[:2]), Team(stored_players[2:]))
    first = repo.create_match(*teams)
    second = repo.create_match(*teams)

    assert first != second
    assert repo.get_match(first) is not None


def test_create_match_with_unknown_player_rolls_back(repo, stored_players):
    """
    Tests that a failed create_match stores nothing at all.
    """
    with pytest.raises(PlayerNotFoundError):
        repo.create_match(
            Team(stored_players[:2]), Team([make_player("Nobody")])
        )

    assert repo.get_latest_match() is None


def test_get_nonexistent_match(repo):
    """
    Tests that an unknown match ID returns None.
    """
    assert repo.get_match(999) is None


def test_get_latest_match(repo, stored_players):
    """
    Tests that get_latest_match returns the newest match, or None.
    """
    assert repo.get_latest_match() is None

    teams = (Team(stored_players[:2]), Team(stored_players[2:]))
    repo.create_match(*teams)
    latest_id = repo.create_match(*teams)

    latest = repo.get_latest_match()
    assert latest is not None
    assert latest.id == latest_id


def test_record_result(repo, stored_players):
    """
    Tests that the winner and the given forms are saved.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    winners = [make_player(p.name, form=6) for p in stored_players[:2]]

    repo.record_result(match_id, "team1", winners)

    match = repo.get_match(match_id)
    assert match is not None
    assert match.winner == "team1"
    assert [p.form for p in match.team1.players] == [6, 6]


def test_record_result_twice(repo, stored_players):
    """
    Tests that a second result is rejected and does not change any form.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    repo.record_result(match_id, "team1", [])

    with pytest.raises(MatchAlreadyRecordedError) as exc:
        repo.record_result(
            match_id, "team2", [make_player("Player 1", form=0)]
        )

    assert exc.value.winner == "team1"
    player = repo.get_player("Player 1")
    assert player is not None and player.form == 5


def test_record_result_unknown_match(repo):
    """
    Tests that recording a result for an unknown match raises.
    """
    with pytest.raises(MatchNotFoundError):
        repo.record_result(999, "team1", [])


def test_remove_player_removes_match_appearances(repo, stored_players):
    """
    Tests the ON DELETE CASCADE: a removed player disappears from matches.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    repo.remove_player("Player 1")

    match = repo.get_match(match_id)
    assert match is not None
    assert [p.name for p in match.team1.players] == ["Player 2"]


def test_clear(repo, stored_players):
    """
    Tests that clear removes players and matches.
    """
    repo.create_match(Team(stored_players[:2]), Team(stored_players[2:]))
    repo.clear()

    assert repo.list_players() == []
    assert repo.get_latest_match() is None


# -------------------------------------------------------------------
# Database integrity
# -------------------------------------------------------------------


def test_foreign_keys_are_enforced(repo):
    """
    Tests that the repository's connections reject rows pointing at
    players or matches that don't exist.
    """
    with repo._connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with repo._connect() as conn:
            conn.execute(
                "INSERT INTO match_players (match_id, player_id, team_number) "
                "VALUES (999, 999, 1)"
            )


def test_check_constraints_reject_bad_scores(repo):
    """
    Tests that the database itself rejects out-of-range values, even if
    something bypasses the Player validation.
    """
    repo.add_player(make_player("Alice"))

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        with repo._connect() as conn:
            conn.execute("UPDATE players SET shooting = 95")


def test_new_database_has_schema_version(tmp_path):
    """
    Tests that a new database is stamped with the schema version, and that
    opening it again is a no-op.
    """
    path = str(tmp_path / "new.db")
    SqliteRepository(path).add_player(make_player("Alice"))
    repo = SqliteRepository(path)

    with repo._connect() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    assert repo.get_player("Alice") is not None


# -------------------------------------------------------------------
# Migration from the old `DB` class schema
# -------------------------------------------------------------------

OLD_SCHEMA = """
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    shooting INTEGER, dribbling INTEGER, passing INTEGER,
    tackling INTEGER, fitness INTEGER, goalkeeping INTEGER,
    form INTEGER DEFAULT 5,
    trueskill_mu REAL DEFAULT 25,
    trueskill_sigma REAL DEFAULT 8.333
);
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_score INTEGER, team_2_score INTEGER, winner INTEGER NULL
);
CREATE TABLE match_players (
    match_id INTEGER, player_id INTEGER, team_number INTEGER,
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    PRIMARY KEY (match_id, player_id)
);
CREATE TABLE last_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team TEXT CHECK(team IN ('team1', 'team2')) NOT NULL,
    bonus REAL
);
"""


def _make_old_database(path, shooting=7):
    with sqlite3.connect(path) as conn:
        conn.executescript(OLD_SCHEMA)
        for name in ["Alice", "Bob", "Cara"]:
            conn.execute(
                "INSERT INTO players (name, shooting, dribbling, passing, "
                "tackling, fitness, goalkeeping, form) "
                "VALUES (?, ?, 7, 7, 7, 7, 7, 6)",
                (name, shooting),
            )
        conn.executemany(
            "INSERT INTO last_teams (player_name, team, bonus) "
            "VALUES (?, ?, ?)",
            [("Alice", "team1", 1.0), ("Bob", "team2", 1.2)],
        )
    conn.close()


def _tables(path):
    conn = sqlite3.connect(path)
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conn.close()


def test_migrates_old_database(tmp_path):
    """
    Tests that players are kept and pending last_teams become a match.
    """
    path = str(tmp_path / "old.db")
    _make_old_database(path)

    repo = SqliteRepository(path)

    assert [p.name for p in repo.list_players()] == ["Alice", "Bob", "Cara"]
    assert {p.form for p in repo.list_players()} == {6}

    match = repo.get_latest_match()
    assert match is not None
    assert [p.name for p in match.team1.players] == ["Alice"]
    assert [p.name for p in match.team2.players] == ["Bob"]
    assert match.team2.bonus == 1.2
    assert match.winner is None

    assert "last_teams" not in _tables(path)
    assert "players_v0" not in _tables(path)


def test_failed_migration_leaves_database_unchanged(tmp_path):
    """
    Tests that the migration is all-or-nothing: an old player with an
    invalid score makes it fail, and the old tables are left as they were.
    """
    path = str(tmp_path / "old.db")
    _make_old_database(path, shooting=95)

    with pytest.raises(sqlite3.IntegrityError):
        SqliteRepository(path)

    assert _tables(path) >= {"players", "matches", "last_teams"}
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM last_teams").fetchone()[0]
    finally:
        conn.close()
