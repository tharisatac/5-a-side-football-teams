# Football team decider
Python CLI (argparse + SQLite) being turned into a tested, Terraform-managed,
CI/CD-deployed FastAPI service on GCP Cloud Run + Firestore.

## Goal
CV/interview project. I must understand and be able to explain every piece.
Explain what you change and why, in plain terms. Define jargon on first use.

## Plan
1. Refactor: pure balancing function, repository interface (SQLite first),
   injected not global, match IDs instead of "last teams"
2. pytest + Hypothesis tests for the balancer
3. FastAPI API with idempotent "record result", /healthz
4. Dockerfile, deploy to Cloud Run, FirestoreRepository
5. Terraform, GitHub Actions (Workload Identity Federation), thin Jinja/htmx UI

## Rules
- Keep the CLI working throughout
- Small commits, one step at a time, tests green before moving on
- Never run terraform apply or gcloud deploy without asking me

## Codebase
- `main.py` entry point; `./run <args>` wraps `python3 main.py`
- `src/cli.py` argparse commands (`player ...`, `teams ...`, `database ...`);
  builds the repository in `main()` and passes it to every handler
- `src/player.py` Player/Attributes (pure domain)
- `src/teams.py` `balance_teams` / `improve_balance` (pure functions)
- `src/repository.py` `Repository` Protocol, `Match`, storage errors
- `src/sqlite_repository.py` + `schema.sql` (repo root) SQLite implementation;
  foreign keys on per connection; schema versioned via `PRAGMA user_version`
- `src/services.py` use-cases: `create_match`, `record_result`,
  `update_player_field`
- `src/csv_io.py` CSV import/export over any Repository
- `test/` pytest suite, one file per module; `conftest.py` has a `repo`
  fixture backed by a temp-dir database
- Layering: cli -> services -> repository; teams/player never touch storage

## Commands
- Setup: `./setup_venv.sh` (creates `venv/`, installs `requirements.txt`)
- Tests: `venv/bin/python -m pytest` (Python 3.14)
- Style: black + isort (line length 79), mypy, all via pre-commit
