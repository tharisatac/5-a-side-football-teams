import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Run main.py with the same Python that runs pytest, from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_COMMAND = [sys.executable, str(PROJECT_ROOT / "main.py")]


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def run_cli_command(args, check=True):
    """
    Runs a CLI command using subprocess.run against the test database.
    Returns the CompletedProcess. With check=True, a non-zero exit code fails
    the test.
    """
    return subprocess.run(
        CLI_COMMAND + args,
        capture_output=True,
        text=True,
        check=check,
        env={**os.environ, "FOOTBALL_DB": os.environ["TEST_FOOTBALL_DB"]},
    )


def add_player_cli(
    name, shooting, dribbling, passing, tackling, fitness, goalkeeping
):
    """
    Adds a player via the CLI using the 'player add' command.
    """
    args = [
        "player",
        "add",
        name,
        "--shooting",
        str(shooting),
        "--dribbling",
        str(dribbling),
        "--passing",
        str(passing),
        "--tackling",
        str(tackling),
        "--fitness",
        str(fitness),
        "--goalkeeping",
        str(goalkeeping),
    ]
    return run_cli_command(args)


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------
@pytest.fixture(scope="function")
def reset_database(tmp_path, monkeypatch):
    """
    Points each CLI test at a new, empty database in a temporary directory.
    """
    monkeypatch.setenv("TEST_FOOTBALL_DB", str(tmp_path / "test.db"))


# -------------------------------------------------------------------
# Tests using subprocess for CLI
# -------------------------------------------------------------------
def test_add_player(reset_database):
    """
    Tests adding a player via the CLI.
    """
    result = add_player_cli("TestPlayer", 8, 7, 9, 6, 9, 5)
    assert "✅ Player 'TestPlayer' added!" in result.stdout


def test_list_players_shows_all_attributes(reset_database):
    """
    Tests that `player list` displays all player attributes correctly.
    """
    add_player_cli("TestPlayer", 8, 9, 7, 6, 8, 5)
    result = run_cli_command(["player", "list"])
    assert "📋 **Players in Database:**" in result.stdout
    assert "TestPlayer" in result.stdout
    for header in [
        "Form",
        "Shooting",
        "Dribbling",
        "Passing",
        "Tackling",
        "Fitness",
        "Goalkeeping",
    ]:
        assert header in result.stdout


def test_list_player_attributes(reset_database):
    """
    Tests that `player attributes` displays the player's attributes.
    """
    add_player_cli("TestPlayer", 8, 9, 7, 6, 8, 5)
    result = run_cli_command(["player", "attributes", "TestPlayer"])
    assert "📊 Attributes for" in result.stdout
    # Check expected attribute outputs (format may need to match exact spacing).
    assert "Shooting:" in result.stdout and "8" in result.stdout
    assert "Dribbling:" in result.stdout and "9" in result.stdout
    assert "Passing:" in result.stdout and "7" in result.stdout
    assert "Tackling:" in result.stdout and "6" in result.stdout
    assert "Fitness:" in result.stdout and "8" in result.stdout
    assert "Goalkeeping:" in result.stdout and "5" in result.stdout
    assert (
        "⭐ Overall Rating:" in result.stdout
    )  # Overall rating is also printed.


def test_remove_player(reset_database):
    """
    Tests removing a player via the CLI.
    """
    add_player_cli("TestPlayer", 8, 7, 8, 6, 9, 5)
    result = run_cli_command(["player", "remove", "TestPlayer"])
    assert "🗑️ Player 'TestPlayer' removed." in result.stdout
    list_result = run_cli_command(["player", "list"])
    assert "TestPlayer" not in list_result.stdout


def test_remove_player_who_has_played(reset_database):
    """
    Tests that a player who is in a match can't be removed.
    """
    for player in ["Alice", "Bob"]:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create", "Alice", "Bob"])

    result = run_cli_command(["player", "remove", "Alice"], check=False)
    assert result.returncode == 1
    assert "has played in a match" in result.stdout


def test_cancel_match(reset_database):
    """
    Tests cancelling the latest match, which frees its players for removal.
    """
    for player in ["Alice", "Bob"]:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create", "Alice", "Bob"])

    result = run_cli_command(["teams", "cancel"])
    assert "🗑️ Cancelled match #1, " in result.stdout

    run_cli_command(["player", "remove", "Alice"])


def test_cancel_recorded_match(reset_database):
    """
    Tests that a played match can't be cancelled.
    """
    for player in ["Alice", "Bob"]:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create", "Alice", "Bob"])
    run_cli_command(["teams", "result", "team1"])

    result = run_cli_command(["teams", "cancel"], check=False)
    assert result.returncode == 1
    assert "already has a result" in result.stdout


def test_update_player(reset_database):
    """
    Tests updating a player's attribute via the CLI.
    """
    add_player_cli("TestPlayer", 8, 7, 9, 6, 9, 5)
    result = run_cli_command(
        ["player", "update", "TestPlayer", "shooting", "9"]
    )
    assert "🔄 Updated shooting of 'TestPlayer' to 9." in result.stdout


def test_update_player_out_of_range(reset_database):
    """
    Tests that an out-of-range value is rejected with a non-zero exit code.
    """
    add_player_cli("TestPlayer", 8, 7, 9, 6, 9, 5)
    result = run_cli_command(
        ["player", "update", "TestPlayer", "shooting", "95"], check=False
    )
    assert result.returncode == 1
    assert "Must be between 1 and 10" in result.stdout


def test_rank_players_all(reset_database):
    """
    Tests that 'player rank' with no argument displays rankings for overall and
    each attribute.
    """
    add_player_cli("Player1", 8, 7, 8, 6, 8, 5)
    add_player_cli("Player2", 7, 8, 7, 7, 7, 6)
    result = run_cli_command(["player", "rank"])
    assert "Ranking by Overall Rating:" in result.stdout
    for attribute in [
        "Shooting",
        "Dribbling",
        "Passing",
        "Tackling",
        "Fitness",
        "Goalkeeping",
    ]:
        assert f"Ranking by {attribute}:" in result.stdout


def test_rank_specific(reset_database):
    """
    Tests that 'player rank shooting' ranks players by the shooting attribute
    only.
    """
    add_player_cli("Player1", 8, 7, 8, 6, 8, 5)
    add_player_cli("Player2", 7, 8, 7, 7, 7, 6)
    result = run_cli_command(["player", "rank", "shooting"])
    assert "Ranking by Shooting:" in result.stdout
    # Check that overall ranking is not printed.
    assert "Ranking by Overall Rating:" not in result.stdout


def test_rank_invalid_attribute(reset_database):
    """
    Tests that 'player rank invalid_attr' outputs an error message.
    """
    add_player_cli("Player1", 8, 7, 8, 6, 8, 5)
    result = run_cli_command(["player", "rank", "invalid_attr"], check=False)
    assert result.returncode == 1
    assert "Invalid attribute" in result.stdout


def test_create_teams(reset_database):
    """
    Tests creating balanced teams from players.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    result = run_cli_command(["teams", "create"] + players)
    assert "✅ Teams created successfully!" in result.stdout
    for player in players:
        assert player in result.stdout


def test_get_team_attributes(reset_database):
    """
    Tests retrieving team attribute ratings via the CLI.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create"] + players)
    result = run_cli_command(["teams", "attributes", "team1"])
    assert "📊 **Team1 Attributes:**" in result.stdout
    assert "Shooting:" in result.stdout


def test_record_match_result(reset_database):
    """
    Tests recording a match result via the CLI.
    """
    players = ["Alice", "Bob", "Charlie", "David"]
    for player in players:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create"] + players)
    result = run_cli_command(["teams", "result", "team1"])
    assert "✅ Match recorded: team1 won!" in result.stdout


def test_record_match_result_twice(reset_database):
    """
    Tests that recording the same result twice succeeds, and a different
    result is rejected.
    """
    players = ["Alice", "Bob"]
    for player in players:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    run_cli_command(["teams", "create"] + players)
    run_cli_command(["teams", "result", "team1"])

    same = run_cli_command(["teams", "result", "team1"])
    assert "✅ Match recorded: team1 won!" in same.stdout

    different = run_cli_command(["teams", "result", "team2"], check=False)
    assert different.returncode == 1
    assert "already has a result" in different.stdout


def test_record_result_for_match_id(reset_database):
    """
    Tests recording the result of an older match with --match.
    """
    players = ["Alice", "Bob"]
    for player in players:
        add_player_cli(player, 7, 7, 7, 7, 7, 7)
    first = run_cli_command(["teams", "create"] + players)
    assert "(match #1, " in first.stdout
    run_cli_command(["teams", "create"] + players)

    result = run_cli_command(["teams", "result", "team2", "--match", "1"])
    assert "✅ Match recorded: team2 won! (match #1, " in result.stdout


def test_create_teams_unknown_player(reset_database):
    """
    Tests that an unknown player name gives an error and exit code 1.
    """
    add_player_cli("Alice", 7, 7, 7, 7, 7, 7)
    result = run_cli_command(
        ["teams", "create", "Alice", "Nobody"], check=False
    )
    assert result.returncode == 1
    assert "Unknown player 'Nobody'" in result.stdout


def test_result_without_match(reset_database):
    """
    Tests that recording a result before creating teams gives an error.
    """
    result = run_cli_command(["teams", "result", "team1"], check=False)
    assert result.returncode == 1
    assert "No matches found" in result.stdout


def test_export_csv(tmp_path, reset_database):
    """
    Tests the CSV export functionality.
    """
    # Insert sample players.
    for p in [("Player A", 8, 7, 6, 5, 7, 4), ("Player B", 7, 8, 6, 7, 7, 5)]:
        add_player_cli(p[0], p[1], p[2], p[3], p[4], p[5], p[6])
    export_file = tmp_path / "export.csv"
    run_cli_command(["database", "export", str(export_file)])
    assert export_file.exists(), "Export file was not created."
    with open(export_file, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    expected_headers = [
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
    assert len(rows) == 3  # 1 header + 2 players


def test_import_csv(tmp_path, reset_database):
    """
    Tests the CSV import functionality.
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
    run_cli_command(["database", "import", str(import_file)])
    # Verify players imported.
    result = run_cli_command(["player", "list"])
    assert "Imported Player 1" in result.stdout
    assert "Imported Player 2" in result.stdout
