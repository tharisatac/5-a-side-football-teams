"""
This module imports and exports players as CSV files.
"""

import csv
from typing import List, Tuple

from .player import ATTRIBUTE_NAMES, DEFAULT_FORM, Attributes, Player
from .repository import SqliteRepository

CSV_HEADERS = ("name",) + ATTRIBUTE_NAMES + ("form",)


def export_players(repo: SqliteRepository, filename: str) -> int:
    """
    Writes all players to a CSV file.

    :param repo:
        Where the players are read from.
    :param filename:
        The CSV file to write. It is overwritten if it exists.

    :raises:
        OSError: If the file cannot be written.

    :return:
        The number of players written.
    """
    players = repo.list_players()
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for player in players:
            values = player.attributes.to_values()
            writer.writerow(
                [player.name]
                + [values[name] for name in ATTRIBUTE_NAMES]
                + [player.form]
            )
    return len(players)


def import_players(
    repo: SqliteRepository, filename: str
) -> Tuple[int, List[Tuple[str, Exception]]]:
    """
    Adds every player in a CSV file. A bad row is skipped rather than stopping
    the import. Extra columns (such as an old `id` column) are ignored.

    :param repo:
        Where the players are added.
    :param filename:
        The CSV file to read.

    :raises:
        FileNotFoundError: If the file does not exist.

    :return:
        The number of players imported, and a (name, error) pair for each
        row that was skipped.
    """
    imported = 0
    errors: List[Tuple[str, Exception]] = []
    with open(filename, mode="r", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("name") or "<unknown>"
            try:
                attributes = Attributes.from_values(
                    {attr: float(row[attr]) for attr in ATTRIBUTE_NAMES}
                )
                form = int(row.get("form") or DEFAULT_FORM)
                repo.add_player(
                    Player(name=row["name"], attributes=attributes, form=form)
                )
                imported += 1
            except Exception as exc:
                errors.append((name, exc))
    return imported, errors
