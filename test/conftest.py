"""
Shared pytest fixtures. pytest loads this file automatically.
"""

import os
from typing import Iterator, List

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from src.player import Attributes, Player
from src.repository import PostgresRepository

# A separate database on the local Postgres (docker compose up -d), so tests
# never touch real data. It is recreated at the start of every test run.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://football:football@localhost:5432/football_test",
)


def make_player(name: str, score: int = 7, form: int = 5) -> Player:
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


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Creates an empty test database once per test run and returns its URL.
    """
    test_db = psycopg.conninfo.conninfo_to_dict(TEST_DATABASE_URL)["dbname"]
    # CREATE DATABASE has to be run from another database, outside a
    # transaction (autocommit).
    admin_url = make_conninfo(TEST_DATABASE_URL, dbname="postgres")
    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{test_db}" WITH (FORCE)')
            conn.execute(f'CREATE DATABASE "{test_db}"')
    except psycopg.OperationalError as exc:
        pytest.exit(
            f"Can't reach Postgres for the tests ({exc}). Start it with "
            "`docker compose up -d`.",
            returncode=1,
        )
    return TEST_DATABASE_URL


@pytest.fixture
def repo(test_database_url) -> Iterator[PostgresRepository]:
    """
    A PostgresRepository on the test database, emptied before each test.
    RESTART IDENTITY makes IDs start from 1 again.
    """
    repository = PostgresRepository(test_database_url)
    with psycopg.connect(test_database_url) as conn:
        conn.execute(
            "TRUNCATE match_players, matches, players RESTART IDENTITY"
        )
    yield repository


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
