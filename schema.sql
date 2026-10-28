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

-- One row per player per match. The skill and form columns are a snapshot of
-- the player when the teams were made, so a past match keeps the ratings it
-- was balanced on even after the player's skills or form change.
CREATE TABLE IF NOT EXISTS match_players (
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    -- RESTRICT: a player who has played in a match can't be deleted.
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    team_number INTEGER NOT NULL CHECK (team_number IN (1, 2)),
    shooting INTEGER NOT NULL CHECK (shooting BETWEEN 1 AND 10),
    dribbling INTEGER NOT NULL CHECK (dribbling BETWEEN 1 AND 10),
    passing INTEGER NOT NULL CHECK (passing BETWEEN 1 AND 10),
    tackling INTEGER NOT NULL CHECK (tackling BETWEEN 1 AND 10),
    fitness INTEGER NOT NULL CHECK (fitness BETWEEN 1 AND 10),
    goalkeeping INTEGER NOT NULL CHECK (goalkeeping BETWEEN 1 AND 10),
    form INTEGER NOT NULL CHECK (form BETWEEN 0 AND 10),
    -- How much the match's result changed this player's form (e.g. +1, -1,
    -- or 0 at the limits), so the result can be undone exactly. 0 until a
    -- result is recorded.
    form_change INTEGER NOT NULL DEFAULT 0 CHECK (form_change BETWEEN -10 AND 10),
    PRIMARY KEY (match_id, player_id)
);

-- Lets SQLite check "has this player played?" quickly when deleting a player.
CREATE INDEX IF NOT EXISTS idx_match_players_player_id
    ON match_players(player_id);
