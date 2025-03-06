import csv
import os
import subprocess

import pytest

from src.db import DB
from src.player import Attributes, Player

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
            "8",
            "--dribbling",
            "7",
            "--passing",
            "9",
            "--tackling",
            "6",
            "--fitness",
            "9",
            "--goalkeeping",
            "5",
        ],
        capture_output=True,
        text=True,
    )

    assert "✅ Player 'TestPlayer' added!" in result.stdout


def test_list_players_shows_all_attributes(reset_database):
    """
    Tests that `player list` displays all player attributes correctly.
    """
    subprocess.run(
        [
            CLI_COMMAND,
            "player",
            "add",
            "TestPlayer",
            "--shooting",
            "8",
            "--dribbling",
            "9",
            "--passing",
            "7",
            "--tackling",
            "6",
            "--fitness",
            "8",
            "--goalkeeping",
            "5",
        ]
    )

    result = subprocess.run(
        [CLI_COMMAND, "player", "list"], capture_output=True, text=True
    )

    assert "📋 **Players in Database:**" in result.stdout
    assert "TestPlayer" in result.stdout
    assert "Form" in result.stdout
    assert "Shooting" in result.stdout
    assert "Dribbling" in result.stdout
    assert "Passing" in result.stdout
    assert "Tackling" in result.stdout
    assert "Fitness" in result.stdout
    assert "Goalkeeping" in result.stdout


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
            "8",
            "--dribbling",
            "7",
            "--passing",
            "8",
            "--tackling",
            "6",
            "--fitness",
            "9",
            "--goalkeeping",
            "5",
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
            "8",
            "--dribbling",
            "7",
            "--passing",
            "9",
            "--tackling",
            "6",
            "--fitness",
            "9",
            "--goalkeeping",
            "5",
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
            "8",
            "--dribbling",
            "7",
            "--passing",
            "9",
            "--tackling",
            "6",
            "--fitness",
            "9",
            "--goalkeeping",
            "5",
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
                "7",
                "--dribbling",
                "7",
                "--passing",
                "7",
                "--tackling",
                "7",
                "--fitness",
                "7",
                "--goalkeeping",
                "7",
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
                "7",
                "--dribbling",
                "7",
                "--passing",
                "7",
                "--tackling",
                "7",
                "--fitness",
                "7",
                "--goalkeeping",
                "7",
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
    assert "Shooting: 7.00" in result.stdout


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
                "7",
                "--dribbling",
                "7",
                "--passing",
                "7",
                "--tackling",
                "7",
                "--fitness",
                "7",
                "--goalkeeping",
                "7",
            ]
        )

    subprocess.run([CLI_COMMAND, "teams", "create"] + players)

    result = subprocess.run(
        [CLI_COMMAND, "teams", "result", "team1"],
        capture_output=True,
        text=True,
    )

    assert "✅ Match recorded: team1 won!" in result.stdout


# A simple Args class to simulate CLI arguments.
class Args:
    def __init__(self, filename):
        self.filename = filename


@pytest.fixture
def tmp_db(tmp_path):
    """
    Creates a temporary test database for CLI CSV tests.
    """
    test_db_path = tmp_path / "test_football.db"
    db_instance = DB(db_name=str(test_db_path))
    yield db_instance
    db_instance.clear_database()
    db_instance.close()
    if os.path.exists(str(test_db_path)):
        os.remove(str(test_db_path))


@pytest.fixture
def cli_db(tmp_db, monkeypatch):
    """
    Overrides the CLI module's global db with our temporary test database.
    """
    import src.cli as cli_mod

    cli_mod.db = tmp_db
    return tmp_db


@pytest.fixture
def sample_players():
    """
    Creates sample players for testing CSV functionality.
    """
    players = [
        Player(
            name="Player A",
            attributes=Attributes.from_values(
                {
                    "shooting": 8,
                    "dribbling": 7,
                    "passing": 6,
                    "tackling": 5,
                    "fitness": 7,
                    "goalkeeping": 4,
                }
            ),
            form=5,
        ),
        Player(
            name="Player B",
            attributes=Attributes.from_values(
                {
                    "shooting": 7,
                    "dribbling": 8,
                    "passing": 6,
                    "tackling": 7,
                    "fitness": 6,
                    "goalkeeping": 5,
                }
            ),
            form=5,
        ),
    ]
    return players


def test_export_csv(tmp_path, cli_db, sample_players):
    """
    Tests the CSV export functionality.
    Inserts sample players, calls the export_csv command,
    then verifies that the CSV file exists and has the expected headers and rows.
    """
    # Insert sample players into the test database.
    for player in sample_players:
        cli_db.add_player(player)

    export_file = tmp_path / "export.csv"
    args = Args(filename=str(export_file))

    from src.cli import export_csv

    export_csv(args)

    # Verify that the CSV file was created.
    assert export_file.exists(), "Export file was not created."

    # Read the CSV and verify headers and number of rows.
    with open(export_file, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Expected headers based on the players table.
    expected_headers = [
        "id",
        "name",
        "shooting",
        "dribbling",
        "passing",
        "tackling",
        "fitness",
        "goalkeeping",
        "form",
    ]
    assert (
        rows[0] == expected_headers
    ), "CSV headers do not match expected headers."
    # Expect one header row plus one row per inserted player.
    assert (
        len(rows) == len(sample_players) + 1
    ), "Number of CSV rows does not match number of players."


def test_import_csv(tmp_path, cli_db):
    """
    Tests the CSV import functionality.
    Creates a CSV file with sample player data, calls the import_csv command,
    and verifies that the players are imported into the database.
    """
    import_file = tmp_path / "import.csv"
    headers = [
        "id",
        "name",
        "shooting",
        "dribbling",
        "passing",
        "tackling",
        "fitness",
        "goalkeeping",
        "form",
    ]
    data = [
        ["", "Imported Player 1", "7", "6", "8", "5", "7", "4", "5"],
        ["", "Imported Player 2", "8", "7", "7", "6", "8", "5", "5"],
    ]
    with open(import_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)

    args = Args(filename=str(import_file))
    from src.cli import import_csv

    import_csv(args)

    # Verify that the players were imported into the database.
    cli_db.cursor.execute("SELECT name FROM players")
    rows = cli_db.cursor.fetchall()
    imported_names = [row[0] for row in rows]

    assert (
        "Imported Player 1" in imported_names
    ), "Imported Player 1 not found in database."
    assert (
        "Imported Player 2" in imported_names
    ), "Imported Player 2 not found in database."
