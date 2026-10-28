import os
import sqlite3
from datetime import datetime, timezone
from test.conftest import make_player

import pytest

from src.repository import (
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerHasMatchesError,
    PlayerNotFoundError,
)
from src.sqlite_repository import (
    DEFAULT_DB_PATH,
    PROJECT_ROOT,
    SqliteRepository,
)
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
    Tests that the winner and the given forms are saved, and that the
    match's snapshot keeps the forms from when it was created.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    winners = [make_player(p.name, form=6) for p in stored_players[:2]]

    repo.record_result(match_id, "team1", winners)

    match = repo.get_match(match_id)
    assert match is not None
    assert match.winner == "team1"
    assert [p.form for p in match.team1.players] == [5, 5]
    assert [repo.get_player(p.name).form for p in winners] == [6, 6]


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


def test_match_keeps_snapshot_of_players(repo, stored_players):
    """
    Tests that changing a player afterwards doesn't change a past match.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    repo.update_player(make_player("Player 1", score=1, form=0))

    match = repo.get_match(match_id)
    assert match is not None
    assert match.team1.players[0] == stored_players[0]


def test_cannot_remove_player_who_has_played(repo, stored_players):
    """
    Tests the ON DELETE RESTRICT: removing a player who is in a match is
    refused, and both the player and the match are left intact.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )

    with pytest.raises(PlayerHasMatchesError) as exc:
        repo.remove_player("Player 1")

    assert exc.value.name == "Player 1"
    assert repo.get_player("Player 1") is not None
    match = repo.get_match(match_id)
    assert match is not None and len(match.team1.players) == 2


def test_cancel_match(repo, stored_players):
    """
    Tests that cancelling deletes the match and its player rows, after which
    its players can be removed.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )

    repo.cancel_match(match_id)

    assert repo.get_match(match_id) is None
    with repo._connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM match_players").fetchone()
    assert count[0] == 0
    repo.remove_player("Player 1")


def test_cannot_cancel_recorded_match(repo, stored_players):
    """
    Tests that a match with a result can't be cancelled.
    """
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    repo.record_result(match_id, "team1", [])

    with pytest.raises(MatchAlreadyRecordedError):
        repo.cancel_match(match_id)

    assert repo.get_match(match_id) is not None


def test_cancel_unknown_match(repo):
    """
    Tests that cancelling an unknown match raises.
    """
    with pytest.raises(MatchNotFoundError):
        repo.cancel_match(999)


def test_match_created_at(repo, stored_players):
    """
    Tests that a match records when it was created, as a UTC datetime.
    """
    before = datetime.now(timezone.utc).replace(microsecond=0)
    match_id = repo.create_match(
        Team(stored_players[:2]), Team(stored_players[2:])
    )
    after = datetime.now(timezone.utc)

    match = repo.get_match(match_id)
    assert match is not None
    assert before <= match.created_at <= after


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
                "INSERT INTO match_players (match_id, player_id, "
                "team_number, shooting, dribbling, passing, tackling, "
                "fitness, goalkeeping, form) "
                "VALUES (999, 999, 1, 5, 5, 5, 5, 5, 5, 5)"
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


def test_reopening_keeps_data(tmp_path):
    """
    Tests that opening an existing database (which re-runs schema.sql) keeps
    its data.
    """
    path = str(tmp_path / "test.db")
    SqliteRepository(path).add_player(make_player("Alice"))

    assert SqliteRepository(path).get_player("Alice") is not None


def test_default_path_is_absolute_in_project_folder():
    """
    Tests that the default database doesn't depend on the current folder.
    """
    assert os.path.isabs(DEFAULT_DB_PATH)
    assert os.path.dirname(DEFAULT_DB_PATH) == str(PROJECT_ROOT)
