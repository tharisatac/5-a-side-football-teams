import csv

import pytest

from src import csv_io
from src.repository import PlayerAlreadyExistsError, SqliteRepository


def test_export_then_import_round_trip(repo, stored_players, tmp_path):
    """
    Tests that exporting and importing into a new database gives back the
    same players.
    """
    path = str(tmp_path / "players.csv")

    assert csv_io.export_players(repo, path) == len(stored_players)

    new_repo = SqliteRepository(str(tmp_path / "other.db"))
    count, errors = csv_io.import_players(new_repo, path)

    assert errors == []
    assert count == len(stored_players)
    assert new_repo.list_players() == stored_players


def test_export_headers(repo, stored_players, tmp_path):
    """
    Tests the exported CSV columns.
    """
    path = tmp_path / "players.csv"
    csv_io.export_players(repo, str(path))

    with open(path, newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0] == list(csv_io.CSV_HEADERS)
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

    count, errors = csv_io.import_players(repo, str(path))

    assert count == 1
    assert [name for name, _ in errors] == ["OutOfRange", "NotANumber", "Good"]
    assert isinstance(errors[2][1], PlayerAlreadyExistsError)
    assert [p.name for p in repo.list_players()] == ["Good"]


def test_import_missing_file(repo, tmp_path):
    """
    Tests that a missing file raises.
    """
    with pytest.raises(FileNotFoundError):
        csv_io.import_players(repo, str(tmp_path / "missing.csv"))
