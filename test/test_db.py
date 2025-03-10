import os
import sqlite3
from typing import Iterator, List

import pytest

from src.db import DB, UnknownPlayerError
from src.player import ATTRIBUTE_WEIGHTS, Attributes, Player

TEST_DB_PATH = "test_football.db"


@pytest.fixture(scope="function")
def db() -> Iterator[DB]:
    """
    Creates a temporary test database for testing.
    """
    test_db = DB(db_name=TEST_DB_PATH)  # Use test DB
    yield test_db  # Run the test

    test_db.clear_database()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def sample_players() -> List[Player]:
    """
    Creates sample players for testing.
    """
    player_data = [
        {
            "shooting": 8.0,
            "dribbling": 7.0,
            "passing": 9.0,
            "tackling": 6.0,
            "fitness": 9.0,
            "goalkeeping": 5.0,
        },
        {
            "shooting": 7.0,
            "dribbling": 7.0,
            "passing": 8.0,
            "tackling": 7.0,
            "fitness": 8.0,
            "goalkeeping": 6.0,
        },
        {
            "shooting": 6.0,
            "dribbling": 8.0,
            "passing": 7.0,
            "tackling": 6.0,
            "fitness": 7.0,
            "goalkeeping": 5.0,
        },
        {
            "shooting": 8.0,
            "dribbling": 6.0,
            "passing": 9.0,
            "tackling": 5.0,
            "fitness": 9.0,
            "goalkeeping": 7.0,
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


def test_add_player(db: DB, sample_players: List[Player]) -> None:
    """
    Tests adding a player to the database.
    """
    player_id = db.add_player(sample_players[0])
    assert (
        player_id is not None
    ), "Player ID should not be None after insertion."

    # Retrieve the player via the DB API.
    player = db.get_player_by_name(sample_players[0].name)
    assert player is not None, "Player should exist in the database."
    assert player.name == sample_players[0].name, "Player name mismatch."
    assert (
        player.attributes.shooting.score
        == sample_players[0].attributes.shooting.score
    ), "Shooting attribute mismatch."


def test_remove_player(db: DB, sample_players: List[Player]) -> None:
    """
    Tests removing a player from the database.
    """
    db.add_player(sample_players[0])
    db.remove_player(sample_players[0].name)

    # Verify removal via the DB API.
    player = db.get_player_by_name(sample_players[0].name)
    assert player is None, "Player should be removed from the database."


def test_update_player_attribute(db: DB, sample_players: List[Player]) -> None:
    """
    Tests updating a player's attribute.
    """
    db.add_player(sample_players[0])
    db.update_player_attribute(sample_players[0].name, "shooting", 9)

    player = db.get_player_by_name(sample_players[0].name)
    assert (
        player is not None
    ), "Player should be retrievable from the database."
    assert (
        player.attributes.shooting.score == 9
    ), "Shooting attribute should be updated to 9."


def test_create_teams(db: DB, sample_players: List[Player]) -> None:
    """
    Tests creating balanced teams from player names.
    """
    for player in sample_players:
        db.add_player(player)

    teams = db.create_teams(["Player 1", "Player 2", "Player 3", "Player 4"])
    assert teams is not None, "Teams should be created."

    team1, team2 = teams
    assert len(team1.players) == 2, "Team 1 should have 2 players."
    assert len(team2.players) == 2, "Team 2 should have 2 players."


def test_record_match_result(db: DB, sample_players: List[Player]) -> None:
    """
    Tests recording a match result and updating player form.
    Winners should have their form increased and losers decreased.
    """
    for player in sample_players:
        db.add_player(player)

    # Create teams and retrieve their allocations.
    db.create_teams(["Player 1", "Player 2", "Player 3", "Player 4"])
    teams = db.get_last_teams()

    # Validate team structure.
    assert (
        "team1" in teams and "team2" in teams
    ), "Both team1 and team2 should exist."
    assert (
        teams["team1"].players and teams["team2"].players
    ), "Both teams should have players."

    winning_team = "team1"
    losing_team = "team2"

    db.record_match_result(winning_team)

    for player in teams[winning_team].players:
        updated_player = db.get_player_by_name(player.name)
        assert (
            updated_player is not None
        ), f"Player {player.name} should exist."
        assert (
            updated_player.form == 6
        ), f"Expected form 6 for {player.name}, got {updated_player.form}"

    for player in teams[losing_team].players:
        updated_player = db.get_player_by_name(player.name)
        assert (
            updated_player is not None
        ), f"Player {player.name} should exist."
        assert (
            updated_player.form == 4
        ), f"Expected form 4 for {player.name}, got {updated_player.form}"


def test_get_player_by_name(db: DB, sample_players: List[Player]) -> None:
    """
    Tests retrieving a player from the database by name.
    """
    db.add_player(sample_players[0])
    player = db.get_player_by_name(sample_players[0].name)
    assert player is not None, "Player should be retrieved by name."
    assert (
        player.name == sample_players[0].name
    ), "Retrieved player's name should match."


def test_get_all_players(db: DB, sample_players: List[Player]) -> None:
    """
    Tests retrieving all players from the database.
    """
    for player in sample_players:
        db.add_player(player)

    players = db.get_all_players()
    assert len(players) == len(
        sample_players
    ), "The number of players should match the number of sample players "
    "inserted."

    player_names = {p["name"] for p in players}
    expected_names = {p.name for p in sample_players}
    assert (
        player_names == expected_names
    ), "Player names in DB should match the sample players."


def test_get_nonexistent_player(db: DB) -> None:
    """
    Tests retrieving a non-existent player.
    """
    player = db.get_player_by_name("Nonexistent Player")
    assert (
        player is None
    ), "Retrieving a non-existent player should return None."


def test_create_team_with_non_existent_player(db: DB) -> None:
    """
    Tests creating a team with an unknown player.
    """
    with pytest.raises(UnknownPlayerError) as exc:
        db.create_teams(["Nonexistent Player"])

    assert ("Unknown player 'Nonexistent Player' passed in.") in str(exc.value)


def test_record_match_without_teams(db: DB) -> None:
    """
    Tests trying to record a match without existing teams.
    """
    db.record_match_result("team1")
    # Verify that no match is recorded by opening a connection locally.
    with sqlite3.connect(TEST_DB_PATH) as connection:
        cur = connection.execute("SELECT COUNT(*) FROM matches")
        match_count = cur.fetchone()[0]
    assert (
        match_count == 0
    ), "No match should be recorded if teams do not exist."


def test_overall_rating_calculation(sample_players: List[Player]) -> None:
    """
    Tests that the overall rating is calculated correctly.
    Overall rating =
        (weighted average attribute score) * (1 + 0.05 * (form - 5))
    """
    player = sample_players[0]
    base_rating = (
        player.attributes.shooting.score * ATTRIBUTE_WEIGHTS["shooting"]
        + player.attributes.dribbling.score * ATTRIBUTE_WEIGHTS["dribbling"]
        + player.attributes.passing.score * ATTRIBUTE_WEIGHTS["passing"]
        + player.attributes.tackling.score * ATTRIBUTE_WEIGHTS["tackling"]
        + player.attributes.fitness.score * ATTRIBUTE_WEIGHTS["fitness"]
        + player.attributes.goalkeeping.score
        * ATTRIBUTE_WEIGHTS["goalkeeping"]
    )
    multiplier = 1 + 0.05 * (player.form - 5)
    expected_overall = base_rating * multiplier

    overall_rating = player.get_overall_rating()
    assert overall_rating == pytest.approx(
        expected_overall, rel=1e-2
    ), "Overall rating should match the expected calculation."
