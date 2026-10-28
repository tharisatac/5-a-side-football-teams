import asyncio
import json
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from src import services
from src.api import _error_response, app, get_repo
from src.player import InvalidValueError
from src.repository import SqliteRepository

SKILLS = {
    "shooting": 7,
    "dribbling": 7,
    "passing": 7,
    "tackling": 7,
    "fitness": 7,
    "goalkeeping": 7,
}
NAMES = ["Alice", "Bob", "Cara", "Dan"]


@pytest.fixture
def client(repo: SqliteRepository) -> Iterator[TestClient]:
    """
    A client for the API, backed by the temporary `repo` database.
    """
    app.dependency_overrides[get_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def squad(client: TestClient) -> None:
    """
    Adds the four NAMES players through the API.
    """
    for name in NAMES:
        response = client.post(
            "/players", json={"name": name, "skills": SKILLS}
        )
        assert response.status_code == 201


def _create_match(client: TestClient) -> dict:
    response = client.post("/matches", json={"players": NAMES})
    assert response.status_code == 201
    return response.json()


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------


def test_root_redirects_to_docs(client):
    """
    Tests that the root URL isn't a dead end.
    """
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_healthz(client):
    """
    Tests the health check.
    """
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# -------------------------------------------------------------------
# Players
# -------------------------------------------------------------------


def test_add_and_get_player(client):
    """
    Tests adding a player and reading it back.
    """
    created = client.post(
        "/players", json={"name": "Alice", "skills": SKILLS, "form": 6}
    )
    fetched = client.get("/players/Alice")

    assert created.status_code == 201
    assert fetched.json() == created.json()
    assert fetched.json()["skills"]["shooting"] == 7
    assert fetched.json()["form"] == 6
    assert fetched.json()["rating"] > 0


def test_add_duplicate_player(client, squad):
    """
    Tests that a taken name is a 409 conflict.
    """
    response = client.post(
        "/players", json={"name": "Alice", "skills": SKILLS}
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"name": "X", "skills": {**SKILLS, "shooting": 11}},
        {"name": "X", "skills": {**SKILLS, "shooting": 0}},
        {"name": "X", "skills": SKILLS, "form": 11},
        {"name": "", "skills": SKILLS},
        {"name": "X", "skills": {"shooting": 5}},
        {"name": "X", "skills": SKILLS, "unknown": 1},
    ],
)
def test_add_invalid_player(client, body):
    """
    Tests that invalid input is rejected with 422 before reaching storage.
    """
    response = client.post("/players", json=body)

    assert response.status_code == 422
    assert client.get("/players").json() == []


def test_list_players(client, squad):
    """
    Tests listing players in the order they were added.
    """
    response = client.get("/players")

    assert [p["name"] for p in response.json()] == NAMES


def test_get_unknown_player(client):
    """
    Tests that an unknown player is a 404.
    """
    response = client.get("/players/Nobody")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown player 'Nobody'."}


def test_update_player(client, squad):
    """
    Tests changing some fields and leaving the rest.
    """
    response = client.patch("/players/Alice", json={"shooting": 9, "form": 8})

    assert response.status_code == 200
    assert response.json()["skills"]["shooting"] == 9
    assert response.json()["skills"]["passing"] == 7
    assert response.json()["form"] == 8


def test_update_player_invalid(client, squad):
    """
    Tests that an out-of-range value is a 422 and nothing changes.
    """
    response = client.patch("/players/Alice", json={"shooting": 9, "form": 11})

    assert response.status_code == 422
    assert client.get("/players/Alice").json()["skills"]["shooting"] == 7


def test_remove_player(client, squad):
    """
    Tests removing a player who hasn't played.
    """
    response = client.delete("/players/Alice")

    assert response.status_code == 204
    assert client.get("/players/Alice").status_code == 404


def test_remove_player_who_has_played(client, squad):
    """
    Tests that removing a player who is in a match is a 409 conflict.
    """
    _create_match(client)

    response = client.delete("/players/Alice")

    assert response.status_code == 409


# -------------------------------------------------------------------
# Matches
# -------------------------------------------------------------------


def test_create_and_get_match(client, squad):
    """
    Tests creating a match and reading it back.
    """
    match = _create_match(client)

    assert len(match["team1"]["players"]) == 2
    assert len(match["team2"]["players"]) == 2
    assert match["winner"] is None
    assert client.get(f"/matches/{match['id']}").json() == match


@pytest.mark.parametrize(
    "players, status_code",
    [
        (["Alice", "Nobody"], 404),
        (["Alice", "Alice"], 422),
        (["Alice"], 422),
    ],
)
def test_create_invalid_match(client, squad, players, status_code):
    """
    Tests unknown, duplicate and too few players.
    """
    response = client.post("/matches", json={"players": players})

    assert response.status_code == status_code
    assert client.get("/matches").json() == []


def test_list_matches_newest_first(client, squad):
    """
    Tests listing matches, newest first.
    """
    first = _create_match(client)
    second = _create_match(client)

    response = client.get("/matches")

    assert [m["id"] for m in response.json()] == [second["id"], first["id"]]


def test_get_unknown_match(client):
    """
    Tests that an unknown match is a 404.
    """
    assert client.get("/matches/999").status_code == 404


def test_cancel_match(client, squad):
    """
    Tests cancelling an unplayed match.
    """
    match = _create_match(client)

    response = client.delete(f"/matches/{match['id']}")

    assert response.status_code == 204
    assert client.get(f"/matches/{match['id']}").status_code == 404


# -------------------------------------------------------------------
# Results
# -------------------------------------------------------------------


def test_record_result(client, squad):
    """
    Tests recording a result: the winner is set and players' current form
    moves, while the match keeps its snapshot.
    """
    match = _create_match(client)
    winner = match["team1"]["players"][0]["name"]

    response = client.put(
        f"/matches/{match['id']}/result", json={"winner": "team1"}
    )

    assert response.status_code == 200
    assert response.json()["winner"] == "team1"
    assert client.get(f"/players/{winner}").json()["form"] == 6
    assert response.json()["team1"]["players"][0]["form"] == 5


def test_record_result_is_idempotent(client, squad):
    """
    Tests that sending the same result twice gives the same response and
    only moves form once, so a retried request is safe.
    """
    match = _create_match(client)
    winner = match["team1"]["players"][0]["name"]
    url = f"/matches/{match['id']}/result"

    first = client.put(url, json={"winner": "team1"})
    second = client.put(url, json={"winner": "team1"})

    assert second.status_code == 200
    assert second.json() == first.json()
    assert client.get(f"/players/{winner}").json()["form"] == 6


def test_record_result_invalid_winner(client, squad):
    """
    Tests that a winner other than team1/team2 is a 422.
    """
    match = _create_match(client)

    response = client.put(
        f"/matches/{match['id']}/result", json={"winner": "team3"}
    )

    assert response.status_code == 422


def test_record_result_unknown_match(client):
    """
    Tests that recording a result for an unknown match is a 404.
    """
    response = client.put("/matches/999/result", json={"winner": "team1"})

    assert response.status_code == 404


# -------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------


def test_subclass_of_a_mapped_error_uses_its_parent_status():
    """
    FastAPI sends subclasses of a mapped error to the same handler, so the
    handler must find the parent's status instead of failing.
    """

    class TooHigh(InvalidValueError):
        pass

    response = asyncio.run(_error_response(None, TooHigh("too high")))

    assert response.status_code == 422
    assert json.loads(response.body) == {"detail": "too high"}


def test_unexpected_value_error_is_a_server_error(client, squad, monkeypatch):
    """
    A plain ValueError is a bug, not bad input: it must be a 500, not a 422
    that blames the caller.
    """

    def broken(*args):
        raise ValueError("internal bug")

    monkeypatch.setattr(services, "create_match", broken)
    unsafe_client = TestClient(app, raise_server_exceptions=False)

    response = unsafe_client.post("/matches", json={"players": NAMES})

    assert response.status_code == 500


@pytest.mark.parametrize(
    "name, status_code, stored",
    [(" Bob ", 201, "Bob"), ("A/B", 422, None), ("   ", 422, None)],
)
def test_player_names_are_trimmed_and_checked(
    client, name, status_code, stored
):
    """
    Surrounding spaces are removed, and names that can't be used in a URL
    are rejected.
    """
    response = client.post("/players", json={"name": name, "skills": SKILLS})

    assert response.status_code == status_code
    if stored:
        assert client.get(f"/players/{stored}").status_code == 200


# -------------------------------------------------------------------
# Changing results, deleting, swapping and resetting form
# -------------------------------------------------------------------


def test_change_result(client, squad):
    """
    PUTting a different winner replaces the result.
    """
    match = _create_match(client)
    winner = match["team1"]["players"][0]["name"]
    url = f"/matches/{match['id']}/result"
    client.put(url, json={"winner": "team1"})

    response = client.put(url, json={"winner": "team2"})

    assert response.status_code == 200
    assert response.json()["winner"] == "team2"
    assert client.get(f"/players/{winner}").json()["form"] == 4


def test_clear_result(client, squad):
    """
    DELETE on the result marks the match unplayed and puts form back.
    """
    match = _create_match(client)
    winner = match["team1"]["players"][0]["name"]
    url = f"/matches/{match['id']}/result"
    client.put(url, json={"winner": "team1"})

    response = client.delete(url)

    assert response.status_code == 200
    assert response.json()["winner"] is None
    assert client.get(f"/players/{winner}").json()["form"] == 5


def test_delete_recorded_match(client, squad):
    """
    A played match can be deleted, and its form changes are undone.
    """
    match = _create_match(client)
    winner = match["team1"]["players"][0]["name"]
    client.put(f"/matches/{match['id']}/result", json={"winner": "team1"})

    response = client.delete(f"/matches/{match['id']}")

    assert response.status_code == 204
    assert client.get(f"/players/{winner}").json()["form"] == 5


def test_swap_players(client, squad):
    """
    Swapping moves one player from each team to the other.
    """
    match = _create_match(client)
    a = match["team1"]["players"][0]["name"]
    b = match["team2"]["players"][0]["name"]

    response = client.post(
        f"/matches/{match['id']}/swap", json={"players": [a, b]}
    )

    assert response.status_code == 200
    assert b in [p["name"] for p in response.json()["team1"]["players"]]


@pytest.mark.parametrize("same_team, count", [(True, 2), (False, 1)])
def test_swap_players_invalid(client, squad, same_team, count):
    """
    Two players from the same team, or the wrong number of players, is a 422.
    """
    match = _create_match(client)
    team1 = [p["name"] for p in match["team1"]["players"]]
    team2 = [p["name"] for p in match["team2"]["players"]]
    players = team1 if same_team else [team1[0], team2[0]][:count]

    response = client.post(
        f"/matches/{match['id']}/swap", json={"players": players}
    )

    assert response.status_code == 422


def test_swap_players_in_recorded_match(client, squad):
    """
    The teams of a played match can't change: 409.
    """
    match = _create_match(client)
    client.put(f"/matches/{match['id']}/result", json={"winner": "team1"})
    a = match["team1"]["players"][0]["name"]
    b = match["team2"]["players"][0]["name"]

    response = client.post(
        f"/matches/{match['id']}/swap", json={"players": [a, b]}
    )

    assert response.status_code == 409


def test_reset_forms(client, squad):
    """
    Resetting puts every player's form back to 5.
    """
    client.patch("/players/Alice", json={"form": 9})

    response = client.post("/players/reset-forms")

    assert response.status_code == 200
    assert {p["form"] for p in response.json()} == {5}
