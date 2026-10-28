# 5-a-side-football-teams
A CLI for organising 5-a-side football: store players' skills, split a group
into two balanced teams, and record results so each player's form adjusts.

## Setup
Requires Python 3.14.

```
./setup_venv.sh
source venv/bin/activate
```

## Usage
Data is stored in `football.db` in the project folder, whichever folder you
run the CLI from. Set the `FOOTBALL_DB` environment variable to use a
different file.

A player who is in a match can't be removed, so match history stays
complete; cancel an unplayed match first if needed. Matches with a result
can't be cancelled. Each match stores its players' skills and form from when the teams
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
./run teams cancel                       # delete an unplayed match

# CSV
./run database export players.csv
./run database import players.csv
```

Run `./run --help` (or `./run teams --help`, etc.) for every command.

## How teams are balanced
Each player's rating is a weighted average of their skills, scaled by form.
Players are dealt into two teams in rating order, then pairs are swapped while
any swap brings the team totals closer. With an odd number of players the
larger team gets a 1.2x rating boost.

## Code layout
```
src/cli.py                 argparse commands -> services
src/services.py            use-cases: create_match, record_result, ...
src/teams.py, player.py    pure domain logic (no storage, no printing)
src/repository.py          Repository interface, Match, storage errors
src/sqlite_repository.py   SQLite implementation (schema in schema.sql)
src/csv_io.py              CSV import/export
```

## Development
```
python -m pytest            # tests
pre-commit run --all-files  # black, isort, mypy
```
