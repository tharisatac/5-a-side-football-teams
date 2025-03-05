import os

import pytest

from player.db import DB
from player.player import Attributes, Player
from player.teams import Team, create_balanced_teams


@pytest.fixture(scope="function")
def db():
    """
    Creates a temporary in-memory database for testing.

    :return:
        A Database instance connected to an SQLite in-memory database.
    """
    test_db = DB(db_name=":memory:")  # Use in-memory database for fast testing
    yield test_db
    test_db.close()


@pytest.fixture
def sample_players():
    """
    Creates sample players for testing.

    :return:
        A list of Player objects.
    """
    player_data = [
        {
            "shooting": 80,
            "dribbling": 70,
            "passing": 90,
            "tackling": 60,
            "fitness": 85,
            "goalkeeping": 50,
        },
        {
            "shooting": 75,
            "dribbling": 75,
            "passing": 80,
            "tackling": 70,
            "fitness": 80,
            "goalkeeping": 60,
        },
        {
            "shooting": 60,
            "dribbling": 85,
            "passing": 70,
            "tackling": 65,
            "fitness": 70,
            "goalkeeping": 55,
        },
        {
            "shooting": 85,
            "dribbling": 60,
            "passing": 90,
            "tackling": 50,
            "fitness": 90,
            "goalkeeping": 70,
        },
    ]
    return [
        Player(
            name=f"Player {i+1}",
            attributes=Attributes.from_values(data),
            form=5,
        )
        for i, data in enumerate(player_data)
    ]


def test_add_player(db, sample_players):
    """
    Tests adding a player to the database.
    """
    player_id = db.add_player(sample_players[0])
    assert player_id is not None

    # Retrieve player directly from the database
    db.cursor.execute(
        "SELECT name, shooting FROM players WHERE id = ?", (player_id,)
    )
    player_data = db.cursor.fetchone()

    assert player_data is not None
    assert player_data[0] == sample_players[0].name
    assert player_data[1] == sample_players[0].attributes.shooting.score


def test_remove_player(db, sample_players):
    """
    Tests removing a player from the database.
    """
    player_id = db.add_player(sample_players[0])
    db.remove_player(sample_players[0].name)

    # Ensure player is removed
    db.cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    assert db.cursor.fetchone() is None


def test_update_player_attribute(db, sample_players):
    """
    Tests updating a player's attribute.
    """
    db.add_player(sample_players[0])
    db.update_player_attribute(sample_players[0].name, "shooting", 99)

    db.cursor.execute(
        "SELECT shooting FROM players WHERE name = ?",
        (sample_players[0].name,),
    )
    updated_shooting = db.cursor.fetchone()[0]

    assert updated_shooting == 99


def test_create_teams(db, sample_players):
    """
    Tests creating balanced teams from player names.
    """
    for player in sample_players:
        db.add_player(player)

    team1, team2 = db.create_teams(
        ["Player 1", "Player 2", "Player 3", "Player 4"]
    )

    assert len(team1.players) == 2
    assert len(team2.players) == 2


def test_record_match_result(db, sample_players):
    """
    Tests recording a match result and updating player form.
    """
    for player in sample_players:
        db.add_player(player)

    team1, team2 = db.create_teams(
        ["Player 1", "Player 2", "Player 3", "Player 4"]
    )
    db.record_match_result("team1")

    # Ensure player forms updated
    db.cursor.execute("SELECT form FROM players WHERE name = ?", ("Player 1",))
    new_form = db.cursor.fetchone()[0]

    assert new_form == 6  # Form should increase by 1 for winners

    db.cursor.execute("SELECT form FROM players WHERE name = ?", ("Player 3",))
    losing_form = db.cursor.fetchone()[0]

    assert losing_form == 4  # Form should decrease by 1 for losers


def test_get_player_by_name(db, sample_players):
    """
    Tests retrieving a player from the database by name.
    """
    db.add_player(sample_players[0])

    player = db.get_player_by_name(sample_players[0].name)
    assert player is not None
    assert player.name == sample_players[0].name


def test_get_nonexistent_player(db):
    """
    Tests retrieving a non-existent player.
    """
    player = db.get_player_by_name("Nonexistent Player")
    assert player is None


def test_record_match_without_teams(db):
    """
    Tests trying to record a match without existing teams.
    """
    db.record_match_result("team1")
    db.cursor.execute("SELECT COUNT(*) FROM matches")
    match_count = db.cursor.fetchone()[0]

    assert match_count == 0  # No matches should be recorded
