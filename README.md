# 5-a-side-football-teams
A CLI for organising 5-a-side football: store players' skills, split a group
into two balanced teams, and record results so each player's form adjusts.

## Setup
Requires Python 3.14 and Docker.

```
./setup_venv.sh
source venv/bin/activate
docker compose up -d      # starts Postgres on localhost:5432
```

## Usage
Data is stored in Postgres. By default the CLI and API use the local
database from `docker compose up -d`; set `DATABASE_URL` (e.g.
`postgresql://user:password@host:5432/dbname`) to use another one. Tables are
created automatically on first use.

A player who is in a match can't be removed, so match history stays
complete; delete the match first if needed. Each match remembers exactly how
its result changed everyone's form, so changing, clearing or deleting a
result puts form back precisely. Each match stores its players' skills and form from when the teams
were made.

```
# Players: skills are 1-10
./run player add Alice -s 8 -d 7 -p 6 -t 5 -f 7 -g 3
./run player list
./run player rank shooting
./run player update Alice shooting 9

# Matches
./run teams create Alice Bob Cara Dan    # prints e.g. "match #3, 28 Oct 2026"
./run teams rating team1                 # latest match, or --match N
./run teams result team1                 # winners' form +1, losers' -1
./run teams result team2                 # change the result (form follows)
./run teams undo                         # back to not played
./run teams swap Alice Bob               # swap two players (unplayed match)
./run teams delete                       # delete a match, undoing its form

# CSV
./run database export players.csv
./run database import players.csv
```

Run `./run --help` (or `./run teams --help`, etc.) for every command.

## Web API
```
uvicorn src.api:app --reload
```
Then open http://127.0.0.1:8000/docs to browse and try every endpoint. The
API uses the same database and rules as the CLI.

| Endpoint | Does |
|---|---|
| `GET /healthz` | Health check |
| `GET/POST /players`, `GET/PATCH/DELETE /players/{name}` | Manage players |
| `POST /players/reset-forms` | Reset everyone's form to 5 |
| `GET/POST /matches`, `GET/DELETE /matches/{id}` | Pick teams, history, delete |
| `POST /matches/{id}/swap` | Swap two players between the teams |
| `PUT/DELETE /matches/{id}/result` | Set or change the winner (safe to retry), or clear it |

## Web UI
A React app in `web/` for match day, the squad and match history. It talks
to the web API, so run both:

```
uvicorn src.api:app --reload      # terminal 1: the API on port 8000
cd web && npm install && npm run dev  # terminal 2: the UI
```

Then open http://localhost:5173. Requires Node.js 20+.

## How teams are balanced
Each player's rating is a weighted average of their skills, scaled by form.
Players are dealt into two teams in rating order, then pairs are swapped while
any swap brings the team totals closer. With an odd number of players the
larger team gets a 1.2x rating boost.

## Code layout
```
src/cli.py                 argparse commands -> services
src/api.py                 FastAPI routes -> services
web/                       React + TypeScript UI (Vite), calls the API
src/services.py            use-cases: create_match, record_result, CSV, ...
src/teams.py, player.py    pure domain logic (no storage, no printing)
src/repository.py          Postgres storage, Match, storage errors
                           (tables in schema.sql)
```

## Development
```
python -m pytest            # tests (needs docker compose up -d)
pre-commit run --all-files  # black, isort, mypy
```
