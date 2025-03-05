"""
This module provides SQLite database functionality for managing players,
teams (as dynamic subsets), and match history.

Tables:
    - players: Stores player attributes.
    - matches: Stores match results.
    - match_players: Links players to matches.
"""

import sqlite3
from typing import List, Optional

from .player import Attributes, Player
from .teams import Team, create_balanced_teams


class DB:
    """
    Manages database interactions for players, teams, and matches.
    """

    def __init__(self, db_name: str = "football.db"):
        """
        Initializes the database connection and creates tables if needed.

        :param db_name:
            The name of the SQLite database file.
        """
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

        # Temporary storage for last created teams
        self.last_teams: dict[str, list[Player]] = {"team1": [], "team2": []}

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
            form INTEGER DEFAULT 5
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
            INSERT INTO players (name, shooting, dribbling, passing, tackling, fitness, goalkeeping, form)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        SELECT shooting, dribbling, passing, tackling, fitness, goalkeeping, form
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
        return Player(name=name, attributes=attributes, form=row[6])

    def create_teams(self, player_names: List[str]) -> tuple[Team, Team]:
        """
        Creates and stores dynamically generated teams from player names.

        :param player_names:
            A list of player names.
        :return:
            A tuple of two Team objects or None if errors occur.
        """
        players = [self.get_player_by_name(name) for name in player_names]
        formatted_players = [p for p in players if p is not None]

        team1, team2 = create_balanced_teams(
            formatted_players,
            len(formatted_players) // 2,
            len(formatted_players) - len(formatted_players) // 2,
        )
        self.last_teams["team1"] = team1.players
        self.last_teams["team2"] = team2.players
        return team1, team2

    def record_match_result(self, winning_team: str) -> None:
        """
        Records the last match result and updates player forms.

        :param winning_team:
            "team1" or "team2" indicating the winning team.
        """
        if not self.last_teams["team1"] or not self.last_teams["team2"]:
            print("Error: No match data available.")
            return

        team1 = self.last_teams["team1"]
        team2 = self.last_teams["team2"]
        winner = 1 if winning_team == "team1" else 2

        # Update player forms using streak-based logic
        for player in team1 + team2:
            form_change = 1 if player in self.last_teams[winning_team] else -1
            new_form = max(
                1, player.form + form_change
            )  # Prevent form from dropping below 1
            self.update_player_attribute(player.name, "form", new_form)

        # Save match in database
        self.cursor.execute(
            "INSERT INTO matches (team_1_score, team_2_score, winner) VALUES (?, ?, ?)",
            (0, 0, winner),
        )  # Scores can be added later
        match_id = self.cursor.lastrowid

        # Fetch player ID before inserting into `match_players`
        for player in team1 + team2:
            self.cursor.execute(
                "SELECT id FROM players WHERE name = ?", (player.name,)
            )
            player_id = self.cursor.fetchone()

            if player_id:  # Ensure the player exists before inserting
                team_number = 1 if player in team1 else 2
                self.cursor.execute(
                    "INSERT INTO match_players (match_id, player_id, team_number) VALUES (?, ?, ?)",
                    (match_id, player_id[0], team_number),
                )

        self.conn.commit()
        print(f"Match recorded! Winning team: {winning_team.capitalize()}")

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()
