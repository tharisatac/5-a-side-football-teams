import os
import subprocess

import pytest

CLI_COMMAND = "./run"

TEST_DB_PATH = "test_football.db"


@pytest.fixture(scope="function")
def reset_database():
    """
    Ensures a clean test database before running each CLI test.
    """
    os.environ["FOOTBALL_DB"] = TEST_DB_PATH

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    subprocess.run(
        [CLI_COMMAND, "database", "clear"], stderr=subprocess.DEVNULL
    )
    yield  # Run the test

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_add_player(reset_database):
    """
    Tests adding a player via the CLI.
    """
    result = subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "80",
            "--dribbling",
            "70",
            "--passing",
            "85",
            "--tackling",
            "60",
            "--fitness",
            "90",
            "--goalkeeping",
            "50",
        ],
        capture_output=True,
        text=True,
    )

    assert "✅ Player 'TestPlayer' added!" in result.stdout


def test_list_players(reset_database):
    """
    Tests listing all players.
    """
    subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "80",
            "--dribbling",
            "70",
            "--passing",
            "85",
            "--tackling",
            "60",
            "--fitness",
            "90",
            "--goalkeeping",
            "50",
        ]
    )

    result = subprocess.run(
        [CLI_COMMAND, "player", "list"], capture_output=True, text=True
    )

    assert "📋 **Players in Database:**" in result.stdout
    assert "TestPlayer" in result.stdout


def test_remove_player(reset_database):
    """
    Tests removing a player.
    """
    subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "80",
            "--dribbling",
            "70",
            "--passing",
            "85",
            "--tackling",
            "60",
            "--fitness",
            "90",
            "--goalkeeping",
            "50",
        ]
    )

    result = subprocess.run(
        [CLI_COMMAND, "player", "remove", "TestPlayer"],
        capture_output=True,
        text=True,
    )

    assert "🗑️ Player 'TestPlayer' removed." in result.stdout

    list_result = subprocess.run(
        [CLI_COMMAND, "player", "list"], capture_output=True, text=True
    )
    assert "TestPlayer" not in list_result.stdout


def test_update_player(reset_database):
    """
    Tests updating a player's attribute.
    """
    subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "80",
            "--dribbling",
            "70",
            "--passing",
            "85",
            "--tackling",
            "60",
            "--fitness",
            "90",
            "--goalkeeping",
            "50",
        ]
    )

    result = subprocess.run(
        [CLI_COMMAND, "player", "update", "TestPlayer", "shooting", "95"],
        capture_output=True,
        text=True,
    )

    assert "🔄 Updated shooting of 'TestPlayer' to 95." in result.stdout


def test_get_player_rating(reset_database):
    """
    Tests retrieving a player's rating.
    """
    subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "80",
            "--dribbling",
            "70",
            "--passing",
            "85",
            "--tackling",
            "60",
            "--fitness",
            "90",
            "--goalkeeping",
            "50",
        ]
    )

    result = subprocess.run(
        [CLI_COMMAND, "player", "rating", "TestPlayer"],
        capture_output=True,
        text=True,
    )

    assert "⭐ TestPlayer's Rating:" in result.stdout


def test_create_teams(reset_database):
    """
    Tests creating balanced teams from players.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        subprocess.run(
            [
                CLI_COMMAND,
                "player",
                "add",
                player,
                "--shooting",
                "70",
                "--dribbling",
                "70",
                "--passing",
                "70",
                "--tackling",
                "70",
                "--fitness",
                "70",
                "--goalkeeping",
                "70",
            ]
        )

    result = subprocess.run(
        [CLI_COMMAND, "teams", "create"] + players,
        capture_output=True,
        text=True,
    )

    assert "✅ Teams created successfully!" in result.stdout
    for player in players:
        assert player in result.stdout


def test_get_team_attributes(reset_database):
    """
    Tests retrieving team attribute ratings.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        subprocess.run(
            [
                CLI_COMMAND,
                "player",
                "add",
                player,
                "--shooting",
                "70",
                "--dribbling",
                "70",
                "--passing",
                "70",
                "--tackling",
                "70",
                "--fitness",
                "70",
                "--goalkeeping",
                "70",
            ]
        )

    # Ensure teams are created before fetching attributes
    subprocess.run([CLI_COMMAND, "teams", "create"] + players)

    result = subprocess.run(
        [CLI_COMMAND, "teams", "attributes", "team1"],
        capture_output=True,
        text=True,
    )

    assert "📊 **Team1 Attributes:**" in result.stdout
    assert "Shooting: 70.00" in result.stdout


def test_record_match_result(reset_database):
    """
    Tests recording a match result.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        subprocess.run(
            [
                CLI_COMMAND,
                "player",
                "add",
                player,
                "--shooting",
                "70",
                "--dribbling",
                "70",
                "--passing",
                "70",
                "--tackling",
                "70",
                "--fitness",
                "70",
                "--goalkeeping",
                "70",
            ]
        )

    subprocess.run([CLI_COMMAND, "teams", "create"] + players)

    result = subprocess.run(
        [CLI_COMMAND, "teams", "result", "team1"],
        capture_output=True,
        text=True,
    )

    assert "✅ Match recorded: team1 won!" in result.stdout
