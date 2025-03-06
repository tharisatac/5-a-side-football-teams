"""
This module provides SQLite database functionality for managing players,
teams (as dynamic subsets), and match history.

Tables:
    - players: Stores player attributes.
    - matches: Stores match results.
    - match_players: Links players to matches.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple

import trueskill

from .player import Attributes, Player
from .teams import Team, TeamCreator


class DB:
    """
    Manages database interactions for players, teams, and matches.
    """

    def __init__(self, db_name=None):
        """
        Initializes the database connection and creates tables if needed.

        :param db_name:
            The name of the SQLite database file.
        """
        self.db_name = db_name or os.getenv("FOOTBALL_DB", "football.db")
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self) -> None:
        """
        Creates necessary database tables if they do not already exist.
        """
        self.cursor.executescript(
            """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            shooting INTEGER,
            dribbling INTEGER,
            passing INTEGER,
            tackling INTEGER,
            fitness INTEGER,
            goalkeeping INTEGER,
            form INTEGER DEFAULT 5,
            trueskill_mu REAL DEFAULT 25,      
            trueskill_sigma REAL DEFAULT 8.333 
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_1_score INTEGER,
            team_2_score INTEGER,
            winner INTEGER NULL
        );

        CREATE TABLE IF NOT EXISTS match_players (
            match_id INTEGER,
            player_id INTEGER,
            team_number INTEGER,  -- 1 for team1, 2 for team2
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            PRIMARY KEY (match_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS last_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            team TEXT CHECK(team IN ('team1', 'team2')) NOT NULL,
            bonus REAL
        );
        """
        )
        self.conn.commit()

    def add_player(self, player: Player) -> Optional[int]:
        """
        Adds a new player to the database.

        :param player:
            The Player object to add.
        :return:
            The database ID of the added player.
        """
        try:
            self.cursor.execute(
                """
               INSERT INTO players (name, shooting, dribbling, passing, tackling, fitness, goalkeeping, form, trueskill_mu, trueskill_sigma)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               """,
                (
                    player.name,
                    player.attributes.shooting.score,
                    player.attributes.dribbling.score,
                    player.attributes.passing.score,
                    player.attributes.tackling.score,
                    player.attributes.fitness.score,
                    player.attributes.goalkeeping.score,
                    player.form,
                    player.trueskill_rating.mu,
                    player.trueskill_rating.sigma,
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Error: Player '{player.name}' already exists.")
            return -1

    def remove_player(self, name: str) -> None:
        """
        Removes a player from the database.

        :param name:
            The name of the player to remove.
        """
        self.cursor.execute("DELETE FROM players WHERE name = ?", (name,))
        self.conn.commit()

    def update_player_attribute(
        self, name: str, attribute: str, value: int
    ) -> None:
        """
        Updates a player's attribute.

        :param name:
            The player's name.
        :param attribute:
            The attribute to update (shooting, dribbling, etc.).
        :param value:
            The new value.
        """
        valid_attributes = [
            "shooting",
            "dribbling",
            "passing",
            "tackling",
            "fitness",
            "goalkeeping",
            "form",
        ]
        if attribute not in valid_attributes:
            print(f"Error: Invalid attribute '{attribute}'.")
            return

        self.cursor.execute(
            f"UPDATE players SET {attribute} = ? WHERE name = ?", (value, name)
        )
        self.conn.commit()

    def get_player_by_name(self, name: str) -> Optional[Player]:
        """
        Retrieves a player from the database by name.

        :param name:
            The player's name.
        :return:
            A Player object or None if not found.
        """
        self.cursor.execute(
            """
        SELECT shooting, dribbling, passing, tackling, fitness, goalkeeping, form, trueskill_mu, trueskill_sigma
        FROM players WHERE name = ?
        """,
            (name,),
        )
        row = self.cursor.fetchone()

        if row is None:
            return None

        attributes = Attributes.from_values(
            {
                "shooting": row[0],
                "dribbling": row[1],
                "passing": row[2],
                "tackling": row[3],
                "fitness": row[4],
                "goalkeeping": row[5],
            }
        )
        player = Player(name=name, attributes=attributes, form=row[6])
        player.trueskill_rating = trueskill.Rating(mu=row[7], sigma=row[8])
        return player

    def get_all_players(self) -> List[Dict]:
        """
        Retrieves all players from the database.

        :return:
            List of player dictionaries.
        """
        self.cursor.execute(
            """
        SELECT name, shooting, dribbling, passing, tackling, fitness,
               goalkeeping, form FROM players;
        """
        )

        rows = self.cursor.fetchall()
        return [
            {
                "name": row[0],
                "shooting": row[1],
                "dribbling": row[2],
                "passing": row[3],
                "tackling": row[4],
                "fitness": row[5],
                "goalkeeping": row[6],
                "form": row[7],
            }
            for row in rows
        ]

    def create_teams(
        self, player_names: List[str]
    ) -> Optional[Tuple[Team, Team]]:
        """
        Creates balanced teams using `TeamCreator` and stores them in the
        database.

        :param player_names:
            List of player names.
        :return:
            Two teams (team1, team2) or None if teams could not be created.
        """
        players = [self.get_player_by_name(name) for name in player_names]
        formatted_players = [
            p for p in players if p
        ]  # Ensure only valid players

        # Ensure we have enough players to form teams
        if len(formatted_players) < 2:
            print("❌ Not enough players to create teams.")
            return None

        team_creator = TeamCreator(
            formatted_players,
            len(formatted_players) // 2,
            len(formatted_players) - len(formatted_players) // 2,
        )
        team1, team2 = team_creator.create_balanced_teams()

        # Remove previous teams
        self.cursor.execute("DELETE FROM last_teams")

        # Store new teams
        for player in team1.players:
            self.cursor.execute(
                "INSERT INTO last_teams (player_name, team, bonus) VALUES (?, ?, ?)",
                (player.name, "team1", team1.bonus),
            )
        for player in team2.players:
            self.cursor.execute(
                "INSERT INTO last_teams (player_name, team, bonus) VALUES (?, ?, ?)",
                (player.name, "team2", team2.bonus),
            )

        self.conn.commit()

        return team1, team2

    def get_last_teams(self) -> Dict[str, Team]:
        """
        Retrieves the last stored teams from the database.

        :return:
            Dictionary with player names in "team1" and "team2".
        """
        self.cursor.execute("SELECT player_name, team, bonus FROM last_teams")
        rows = self.cursor.fetchall()

        team1_players = []
        team2_players = []
        team1_bonus = 0.0
        team2_bonus = 0.0

        for player_name, team, bonus in rows:
            if team == "team1":
                team1_players.append(self.get_player_by_name(player_name))
                team1_bonus = bonus
            else:
                team2_players.append(self.get_player_by_name(player_name))
                team2_bonus = bonus

        return {
            "team1": Team(
                list(player for player in team1_players if player is not None),
                team1_bonus,
            ),
            "team2": Team(
                list(player for player in team2_players if player is not None),
                team2_bonus,
            ),
        }

    def record_match_result(self, winning_team: str) -> None:
        """
        Records the last match result and updates player forms and TrueSkill ratings.
        """
        teams = self.get_last_teams()
        if not teams["team1"].players or not teams["team2"].players:
            print("❌ Error: No match data available.")
            return

        # Determine winners and losers
        team1_won = winning_team == "team1"
        team1 = teams["team1"]
        team2 = teams["team2"]

        # Update TrueSkill & form for all players
        for player in team1.players:
            player.update_trueskill(won=team1_won)

        for player in team2.players:
            player.update_trueskill(won=not team1_won)

        # Persist updated player ratings and form to the database
        for player in team1.players + team2.players:
            self.cursor.execute(
                """
                UPDATE players SET form = ?, trueskill_mu = ?, trueskill_sigma = ? WHERE name = ?
                """,
                (
                    player.form,
                    player.trueskill_rating.mu,
                    player.trueskill_rating.sigma,
                    player.name,
                ),
            )

        # Store match result in the database
        winner = 1 if team1_won else 2
        self.cursor.execute(
            "INSERT INTO matches (team_1_score, team_2_score, winner) VALUES (?, ?, ?)",
            (0, 0, winner),
        )

        # Clear last teams after match
        self.cursor.execute("DELETE FROM last_teams")
        self.conn.commit()

        print(f"✅ Match recorded! Winning team: {winning_team.capitalize()}")

    def clear_database(self):
        """
        Deletes all data from the database, resetting it to an empty state.
        """
        self.cursor.execute("DELETE FROM players")
        self.cursor.execute("DELETE FROM matches")
        self.cursor.execute("DELETE FROM match_players")
        self.cursor.execute("DELETE FROM last_teams")
        self.conn.commit()
        print("✅ Database cleared successfully!")

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()
