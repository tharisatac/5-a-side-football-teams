-- SQLite schema for the football team decider.
-- Every statement is safe to re-run ("IF NOT EXISTS").
-- Foreign keys are only enforced when a connection runs
-- `PRAGMA foreign_keys = ON`, which SqliteRepository does on every connection.

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    shooting INTEGER NOT NULL CHECK (shooting BETWEEN 1 AND 10),
    dribbling INTEGER NOT NULL CHECK (dribbling BETWEEN 1 AND 10),
    passing INTEGER NOT NULL CHECK (passing BETWEEN 1 AND 10),
    tackling INTEGER NOT NULL CHECK (tackling BETWEEN 1 AND 10),
    fitness INTEGER NOT NULL CHECK (fitness BETWEEN 1 AND 10),
    goalkeeping INTEGER NOT NULL CHECK (goalkeeping BETWEEN 1 AND 10),
    form INTEGER NOT NULL DEFAULT 5 CHECK (form BETWEEN 0 AND 10)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    team_1_bonus REAL NOT NULL DEFAULT 1.0,
    team_2_bonus REAL NOT NULL DEFAULT 1.0,
    winner INTEGER CHECK (winner IN (1, 2))  -- NULL until a result is recorded
);

CREATE TABLE IF NOT EXISTS match_players (
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    team_number INTEGER NOT NULL CHECK (team_number IN (1, 2)),
    PRIMARY KEY (match_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_match_players_player_id
    ON match_players(player_id);
