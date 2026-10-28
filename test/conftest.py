"""
Shared pytest fixtures. pytest loads this file automatically.
"""

from typing import List

import pytest

from src.player import Attributes, Player
from src.repository import SqliteRepository


def make_player(name: str, score: float = 7, form: int = 5) -> Player:
    """
    Creates a player with every attribute set to `score`.
    """
    attributes = Attributes.from_values(
        {
            "shooting": score,
            "dribbling": score,
            "passing": score,
            "tackling": score,
            "fitness": score,
            "goalkeeping": score,
        }
    )
    return Player(name=name, attributes=attributes, form=form)


@pytest.fixture
def repo(tmp_path) -> SqliteRepository:
    """
    A SqliteRepository backed by a fresh database file in a temporary
    directory that pytest deletes afterwards.
    """
    return SqliteRepository(str(tmp_path / "test.db"))


@pytest.fixture
def players() -> List[Player]:
    """
    Four players with different ratings.
    """
    return [
        make_player("Player 1", score=8),
        make_player("Player 2", score=7),
        make_player("Player 3", score=6),
        make_player("Player 4", score=5),
    ]


@pytest.fixture
def stored_players(repo, players) -> List[Player]:
    """
    The `players`, already added to `repo`.
    """
    for player in players:
        repo.add_player(player)
    return players
