import pytest

from src import services
from src.repository import (
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerNotFoundError,
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


def test_record_result_twice_does_not_double_count(repo, stored_players):
    """
    Tests that recording a second result is rejected and forms only move
    once.
    """
    match = services.create_match(repo, NAMES)
    services.record_result(repo, match.id, "team1")

    with pytest.raises(MatchAlreadyRecordedError):
        services.record_result(repo, match.id, "team1")

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
# update_player_field
# -------------------------------------------------------------------


def test_update_attribute(repo, stored_players):
    """
    Tests updating one attribute leaves the others alone.
    """
    services.update_player_field(repo, "Player 1", "shooting", 9)

    player = repo.get_player("Player 1")
    assert player is not None
    assert player.attributes.shooting.score == 9
    assert player.attributes.passing.score == 8


def test_update_form(repo, stored_players):
    """
    Tests updating form.
    """
    services.update_player_field(repo, "Player 1", "form", 10)

    player = repo.get_player("Player 1")
    assert player is not None and player.form == 10


def test_update_invalid_attribute(repo, stored_players):
    """
    Tests that an unknown attribute name raises.
    """
    with pytest.raises(services.InvalidAttrError) as exc:
        services.update_player_field(repo, "Player 1", "invalid-attr", 9)

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
        services.update_player_field(repo, "Player 1", field, value)

    assert repo.get_player("Player 1") == stored_players[0]


def test_update_unknown_player(repo):
    """
    Tests that updating an unknown player raises.
    """
    with pytest.raises(PlayerNotFoundError):
        services.update_player_field(repo, "Nobody", "shooting", 5)
