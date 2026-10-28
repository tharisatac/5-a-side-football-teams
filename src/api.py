"""
This module is the web API: FastAPI routes over the same services the CLI
uses, so both follow the same rules.

Run it locally with `uvicorn src.api:app --reload`, then open
http://127.0.0.1:8000/docs for interactive documentation.
"""

import os
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import services
from .player import DEFAULT_FORM, Attributes, Player
from .repository import (
    DEFAULT_DB_PATH,
    Match,
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerHasMatchesError,
    PlayerNotFoundError,
    SqliteRepository,
    TeamKey,
)
from .teams import DuplicatePlayerError, NotEnoughPlayersError, Team

# --------------------------
# Errors
# --------------------------

# The HTTP status code returned for each domain error. Anything else is a bug
# and becomes a 500.
ERROR_STATUS: Dict[type, int] = {
    PlayerNotFoundError: status.HTTP_404_NOT_FOUND,
    MatchNotFoundError: status.HTTP_404_NOT_FOUND,
    PlayerAlreadyExistsError: status.HTTP_409_CONFLICT,
    PlayerHasMatchesError: status.HTTP_409_CONFLICT,
    MatchAlreadyRecordedError: status.HTTP_409_CONFLICT,
    DuplicatePlayerError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NotEnoughPlayersError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    services.InvalidAttrError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ValueError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def _error_response(request: Request, exc: Exception) -> JSONResponse:
    """
    Turns a domain error into a JSON response with the matching status code.

    :param request:
        The request that failed (required by FastAPI, unused).
    :param exc:
        The error that was raised.

    :return:
        `{"detail": "<message>"}` with the status code from ERROR_STATUS.
    """
    return JSONResponse(
        status_code=ERROR_STATUS[type(exc)], content={"detail": str(exc)}
    )


app = FastAPI(title="Football Team Decider")
for error_type in ERROR_STATUS:
    app.add_exception_handler(error_type, _error_response)


# --------------------------
# Dependencies
# --------------------------


@lru_cache
def _repo_for(path: str) -> SqliteRepository:
    """
    Returns one repository per database path, so the schema check runs once
    rather than on every request.

    :param path:
        The database file.
    """
    return SqliteRepository(path)


def get_repo() -> SqliteRepository:
    """
    Provides the repository to each route. Tests replace this with a
    temporary database via `app.dependency_overrides`.
    """
    return _repo_for(os.getenv("FOOTBALL_DB", DEFAULT_DB_PATH))


Repo = Annotated[SqliteRepository, Depends(get_repo)]


# --------------------------
# Request and response models
# --------------------------

Score = Annotated[int, Field(ge=1, le=10)]
Form = Annotated[int, Field(ge=0, le=10)]


class Skills(BaseModel):
    """
    A player's six skills, each 1-10.
    """

    model_config = ConfigDict(extra="forbid")

    shooting: Score
    dribbling: Score
    passing: Score
    tackling: Score
    fitness: Score
    goalkeeping: Score


class PlayerCreate(BaseModel):
    """
    Body of `POST /players`.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=50)
    skills: Skills
    form: Form = DEFAULT_FORM


class PlayerUpdate(BaseModel):
    """
    Body of `PATCH /players/{name}`: only the fields given are changed.
    """

    model_config = ConfigDict(extra="forbid")

    shooting: Optional[Score] = None
    dribbling: Optional[Score] = None
    passing: Optional[Score] = None
    tackling: Optional[Score] = None
    fitness: Optional[Score] = None
    goalkeeping: Optional[Score] = None
    form: Optional[Form] = None


class PlayerOut(BaseModel):
    """
    A player as returned by the API.
    """

    name: str
    skills: Dict[str, float]
    form: int
    rating: float


class TeamOut(BaseModel):
    """
    A team as returned by the API.
    """

    players: List[PlayerOut]
    bonus: float
    rating: float


class MatchCreate(BaseModel):
    """
    Body of `POST /matches`.
    """

    model_config = ConfigDict(extra="forbid")

    players: List[str]


class MatchOut(BaseModel):
    """
    A match as returned by the API. Its players' skills and form are as they
    were when the teams were made.
    """

    id: int
    created_at: datetime
    team1: TeamOut
    team2: TeamOut
    winner: Optional[TeamKey]


class ResultIn(BaseModel):
    """
    Body of `PUT /matches/{match_id}/result`.
    """

    model_config = ConfigDict(extra="forbid")

    winner: TeamKey


def _player_out(player: Player) -> PlayerOut:
    """
    Converts a Player for the response.

    :param player:
        The player.
    """
    return PlayerOut(
        name=player.name,
        skills=player.attributes.to_values(),
        form=player.form,
        rating=player.get_overall_rating(),
    )


def _team_out(team: Team) -> TeamOut:
    """
    Converts a Team for the response.

    :param team:
        The team.
    """
    return TeamOut(
        players=[_player_out(p) for p in team.players],
        bonus=team.bonus,
        rating=team.get_overall_rating(),
    )


def _match_out(match: Match) -> MatchOut:
    """
    Converts a Match for the response.

    :param match:
        The match.
    """
    return MatchOut(
        id=match.id,
        created_at=match.created_at,
        team1=_team_out(match.team1),
        team2=_team_out(match.team2),
        winner=match.winner,
    )


# --------------------------
# Health
# --------------------------


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    """
    Reports that the server is up. Cloud Run calls this to decide whether
    the container is healthy.
    """
    return {"status": "ok"}


# --------------------------
# Players
# --------------------------


@app.get("/players")
def list_players(repo: Repo) -> List[PlayerOut]:
    """
    Lists all players in the order they were added.

    :param repo:
        Where players are stored.
    """
    return [_player_out(p) for p in repo.list_players()]


@app.get("/players/{name}")
def get_player(name: str, repo: Repo) -> PlayerOut:
    """
    Returns one player.

    :param name:
        The player's name.
    :param repo:
        Where players are stored.

    :raises:
        PlayerNotFoundError: If the player does not exist (404).
    """
    player = repo.get_player(name)
    if player is None:
        raise PlayerNotFoundError(name)
    return _player_out(player)


@app.post("/players", status_code=status.HTTP_201_CREATED)
def add_player(body: PlayerCreate, repo: Repo) -> PlayerOut:
    """
    Adds a new player.

    :param body:
        The player's name, skills and (optional) form.
    :param repo:
        Where players are stored.

    :raises:
        PlayerAlreadyExistsError: If the name is taken (409).
    """
    player = Player(
        name=body.name,
        attributes=Attributes.from_values(body.skills.model_dump()),
        form=body.form,
    )
    repo.add_player(player)
    return _player_out(player)


@app.patch("/players/{name}")
def update_player(name: str, body: PlayerUpdate, repo: Repo) -> PlayerOut:
    """
    Changes some of a player's skills and/or form.

    :param name:
        The player's name.
    :param body:
        The fields to change; omitted fields are left as they are.
    :param repo:
        Where players are stored.

    :raises:
        PlayerNotFoundError: If the player does not exist (404).
    """
    changes = body.model_dump(exclude_none=True)
    return _player_out(services.update_player(repo, name, changes))


@app.delete("/players/{name}", status_code=status.HTTP_204_NO_CONTENT)
def remove_player(name: str, repo: Repo) -> None:
    """
    Removes a player who has never played in a match.

    :param name:
        The player's name.
    :param repo:
        Where players are stored.

    :raises:
        PlayerNotFoundError: If the player does not exist (404).
        PlayerHasMatchesError: If the player is in any match (409).
    """
    repo.remove_player(name)


# --------------------------
# Matches
# --------------------------


@app.get("/matches")
def list_matches(repo: Repo) -> List[MatchOut]:
    """
    Lists all matches, newest first.

    :param repo:
        Where matches are stored.
    """
    return [_match_out(m) for m in repo.list_matches()]


@app.post("/matches", status_code=status.HTTP_201_CREATED)
def create_match(body: MatchCreate, repo: Repo) -> MatchOut:
    """
    Balances the named players into two teams and stores them as a match.

    :param body:
        The names of the players taking part.
    :param repo:
        Where players and matches are stored.

    :raises:
        PlayerNotFoundError: If a name does not exist (404).
        DuplicatePlayerError: If a name is given more than once (422).
        NotEnoughPlayersError: If fewer than 2 names are given (422).
    """
    return _match_out(services.create_match(repo, body.players))


@app.get("/matches/{match_id}")
def get_match(match_id: int, repo: Repo) -> MatchOut:
    """
    Returns one match.

    :param match_id:
        The match ID.
    :param repo:
        Where matches are stored.

    :raises:
        MatchNotFoundError: If the match does not exist (404).
    """
    match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    return _match_out(match)


@app.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_match(match_id: int, repo: Repo) -> None:
    """
    Cancels a match that hasn't been played.

    :param match_id:
        The match ID.
    :param repo:
        Where matches are stored.

    :raises:
        MatchNotFoundError: If the match does not exist (404).
        MatchAlreadyRecordedError: If the match has a result (409).
    """
    services.cancel_match(repo, match_id)


@app.put("/matches/{match_id}/result")
def record_result(match_id: int, body: ResultIn, repo: Repo) -> MatchOut:
    """
    Records the winner and updates players' form. Idempotent: sending the
    same winner again changes nothing and returns the same match, so
    retries are safe. PUT is the HTTP method for exactly this behaviour.

    :param match_id:
        The match ID.
    :param body:
        The winning team.
    :param repo:
        Where players and matches are stored.

    :raises:
        MatchNotFoundError: If the match does not exist (404).
        MatchAlreadyRecordedError: If a different winner was recorded (409).
    """
    return _match_out(services.record_result(repo, match_id, body.winner))
