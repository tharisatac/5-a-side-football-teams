import csv

import pytest

from src import services
from src.player import InvalidValueError
from src.repository import (
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
    SqliteRepository,
)
from src.teams import DuplicatePlayerError, NotEnoughPlayersError

NAMES = ["Player 1", "Player 2", "Player 3", "Player 4"]

# -------------------------------------------------------------------
# create_match
# -------------------------------------------------------------------


def test_create_match(repo, stored_players):
    """
    Tests that a match is balanced, stored, and readable by its ID.
    """
    match = services.create_match(repo, NAMES)

    assert len(match.team1.players) == 2
    assert len(match.team2.players) == 2
    assert repo.get_match(match.id) == match


def test_create_match_unknown_player(repo, stored_players):
    """
    Tests that an unknown name raises and stores no match.
    """
    with pytest.raises(PlayerNotFoundError) as exc:
        services.create_match(repo, ["Player 1", "Nobody"])

    assert exc.value.name == "Nobody"
    assert repo.get_latest_match() is None


def test_create_match_duplicate_player(repo, stored_players):
    """
    Tests that a name given twice raises.
    """
    with pytest.raises(DuplicatePlayerError) as exc:
        services.create_match(repo, ["Player 1", "Player 1"])

    assert "Duplicate player added 'Player 1'" in str(exc.value)


def test_create_match_not_enough_players(repo, stored_players):
    """
    Tests that a single player raises.
    """
    with pytest.raises(NotEnoughPlayersError):
        services.create_match(repo, ["Player 1"])


# -------------------------------------------------------------------
# record_result
# -------------------------------------------------------------------


def test_record_result_updates_form(repo, stored_players):
    """
    Tests that winners gain 1 form, losers lose 1, and the winner is saved.
    """
    match = services.create_match(repo, NAMES)

    services.record_result(repo, match.id, "team1")

    for player in match.team1.players:
        stored = repo.get_player(player.name)
        assert stored is not None and stored.form == 6
    for player in match.team2.players:
        stored = repo.get_player(player.name)
        assert stored is not None and stored.form == 4
    stored_match = repo.get_match(match.id)
    assert stored_match is not None and stored_match.winner == "team1"


def test_record_result_is_idempotent(repo, stored_players):
    """
    Tests that recording the same result again succeeds and forms only move
    once.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    again = services.record_result(repo, match.id, "team1")

    assert again.winner == "team1"
    winner = repo.get_player(match.team1.players[0].name)
    assert winner is not None and winner.form == 6


def test_record_result_for_older_match(repo, stored_players):
    """
    Tests that creating a new match doesn't stop an older one being
    recorded, which the old single "last teams" slot could not do.
    """
    first = services.create_match(repo, NAMES)
    services.create_match(repo, NAMES[:2])

    services.record_result(repo, first.id, "team2")

    stored = repo.get_match(first.id)
    assert stored is not None and stored.winner == "team2"


def test_record_result_uses_current_form(repo, stored_players):
    """
    Tests that recording an older match starts from each player's current
    form, not the form saved with the match. Both matches contain the same
    two players, so recording both wins takes them from 5 to 7.
    """
    first = services.create_match(repo, NAMES[:2])
    second = services.create_match(repo, NAMES[:2])
    winner = second.team1.players[0].name

    services.record_result(repo, second.id, "team1")
    first_team = "team1" if first.team1.players[0].name == winner else "team2"
    services.record_result(repo, first.id, first_team)

    stored = repo.get_player(winner)
    assert stored is not None and stored.form == 7


def test_record_result_unknown_match(repo):
    """
    Tests that an unknown match ID raises.
    """
    with pytest.raises(MatchNotFoundError):
        services.record_result(repo, 999, "team1")


def test_record_result_invalid_winner(repo, stored_players):
    """
    Tests that a winner other than team1/team2 raises.
    """
    match = services.create_match(repo, NAMES)

    with pytest.raises(ValueError):
        services.record_result(repo, match.id, "team3")  # type: ignore


# -------------------------------------------------------------------
# update_player
# -------------------------------------------------------------------


def test_update_attribute(repo, stored_players):
    """
    Tests updating one attribute leaves the others alone.
    """
    services.update_player(repo, "Player 1", {"shooting": 9})

    player = repo.get_player("Player 1")
    assert player is not None
    assert player.attributes.shooting.score == 9
    assert player.attributes.passing.score == 8


def test_update_form(repo, stored_players):
    """
    Tests updating form.
    """
    services.update_player(repo, "Player 1", {"form": 10})

    player = repo.get_player("Player 1")
    assert player is not None and player.form == 10


def test_update_invalid_attribute(repo, stored_players):
    """
    Tests that an unknown attribute name raises.
    """
    with pytest.raises(services.InvalidAttrError) as exc:
        services.update_player(repo, "Player 1", {"invalid-attr": 9})

    assert "Invalid attribute 'invalid-attr' passed in." in str(exc.value)


@pytest.mark.parametrize(
    "field, value",
    [("shooting", 0), ("shooting", 11), ("shooting", 95), ("form", -1)],
)
def test_update_out_of_range(repo, stored_players, field, value):
    """
    Tests that out-of-range values are rejected and nothing is saved.
    """
    with pytest.raises(ValueError):
        services.update_player(repo, "Player 1", {field: value})

    assert repo.get_player("Player 1") == stored_players[0]


def test_update_several_fields_at_once(repo, stored_players):
    """
    Tests changing attributes and form in one call.
    """
    player = services.update_player(
        repo, "Player 1", {"shooting": 2, "passing": 3, "form": 9}
    )

    assert repo.get_player("Player 1") == player
    assert player.attributes.shooting.score == 2
    assert player.attributes.passing.score == 3
    assert player.form == 9


def test_update_saves_nothing_if_one_value_is_invalid(repo, stored_players):
    """
    Tests that a valid change isn't saved alongside an invalid one.
    """
    with pytest.raises(ValueError):
        services.update_player(
            repo, "Player 1", {"shooting": 2, "passing": 11}
        )

    assert repo.get_player("Player 1") == stored_players[0]


def test_update_unknown_player(repo):
    """
    Tests that updating an unknown player raises.
    """
    with pytest.raises(PlayerNotFoundError):
        services.update_player(repo, "Nobody", {"shooting": 5})


# -------------------------------------------------------------------
# Import / export
# -------------------------------------------------------------------


def test_export_then_import_round_trip(repo, stored_players, tmp_path):
    """
    Tests that exporting and importing into a new database gives back the
    same players.
    """
    path = str(tmp_path / "players.csv")

    assert services.export_players(repo, path) == len(stored_players)

    new_repo = SqliteRepository(str(tmp_path / "other.db"))
    count, errors = services.import_players(new_repo, path)

    assert errors == []
    assert count == len(stored_players)
    assert new_repo.list_players() == stored_players


def test_export_headers(repo, stored_players, tmp_path):
    """
    Tests the exported CSV columns.
    """
    path = tmp_path / "players.csv"
    services.export_players(repo, str(path))

    with open(path, newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0] == list(services.CSV_HEADERS)
    assert len(rows) == 1 + len(stored_players)


def test_import_skips_bad_rows(repo, tmp_path):
    """
    Tests that a bad row is reported and the rest are still imported. Also
    checks that an old export with an `id` column still imports.
    """
    path = tmp_path / "players.csv"
    path.write_text(
        "id,name,shooting,dribbling,passing,tackling,fitness,goalkeeping,"
        "form\n"
        "1,Good,7,7,7,7,7,7,5\n"
        "2,OutOfRange,95,7,7,7,7,7,5\n"
        "3,NotANumber,x,7,7,7,7,7,5\n"
        "4,Good,7,7,7,7,7,7,5\n"
    )

    count, errors = services.import_players(repo, str(path))

    assert count == 1
    assert [name for name, _ in errors] == ["OutOfRange", "NotANumber", "Good"]
    assert isinstance(errors[2][1], PlayerAlreadyExistsError)
    assert [p.name for p in repo.list_players()] == ["Good"]


def test_import_missing_file(repo, tmp_path):
    """
    Tests that a missing file raises.
    """
    with pytest.raises(FileNotFoundError):
        services.import_players(repo, str(tmp_path / "missing.csv"))


# -------------------------------------------------------------------
# Changing results, deleting and swapping
# -------------------------------------------------------------------


def test_change_result(repo, stored_players):
    """
    Recording a different winner replaces the result and its form changes.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    changed = services.record_result(repo, match.id, "team2")

    assert changed.winner == "team2"
    first_team1 = repo.get_player(match.team1.players[0].name)
    assert first_team1 is not None and first_team1.form == 4


def test_clear_result(repo, stored_players):
    """
    Clearing a result marks the match unplayed and puts form back.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    cleared = services.clear_result(repo, match.id)

    assert cleared.winner is None
    assert {p.form for p in repo.list_players()} == {5}


def test_delete_match(repo, stored_players):
    """
    A match can be deleted and teams picked again, even after a result.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    services.delete_match(repo, match.id)

    assert repo.get_match(match.id) is None
    assert {p.form for p in repo.list_players()} == {5}
    assert services.create_match(repo, NAMES).id != match.id


def test_swap_players(repo, stored_players):
    """
    Swapping moves one player from each team to the other.
    """
    match = services.create_match(repo, NAMES)
    a = match.team1.players[0].name
    b = match.team2.players[0].name

    swapped = services.swap_players(repo, match.id, a, b)

    assert b in [p.name for p in swapped.team1.players]
    assert a in [p.name for p in swapped.team2.players]


def test_swap_players_on_the_same_team(repo, stored_players):
    """
    Two players from the same team can't be swapped.
    """
    match = services.create_match(repo, NAMES)
    a, b = [p.name for p in match.team1.players]

    with pytest.raises(InvalidValueError):
        services.swap_players(repo, match.id, a, b)


def test_swap_player_not_in_match(repo, stored_players):
    """
    A player who isn't in the match can't be swapped.
    """
    match = services.create_match(repo, NAMES[:2])

    with pytest.raises(InvalidValueError):
        services.swap_players(repo, match.id, NAMES[0], NAMES[3])


def test_cannot_swap_in_recorded_match(repo, stored_players):
    """
    The teams of a played match can't change.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    with pytest.raises(MatchAlreadyRecordedError):
        services.swap_players(
            repo,
            match.id,
            match.team1.players[0].name,
            match.team2.players[0].name,
        )
