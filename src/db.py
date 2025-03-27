"""
This module provides SQLite database functionality for managing players,
teams (as dynamic subsets), and match history.
"""

import csv
import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from .player import Attributes, Player
from . import teams
from .teams import Team, TeamCreator


class DB:
    """
    Manages database interactions for players, teams, and matches.
    """

    def __init__(self, db_name=None):
        """
        Initializes the database connection and creates tables if needed.
        """
        self.db_name = db_name or os.getenv("FOOTBALL_DB", "football.db")
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def _validate_player_exists_by_name(
        self, name: str, should_exist: bool
    ) -> str:
        """
        Validate whether the player should exist or not.

        :param name:
            The name of the player to check.

        :param should_exist:
            A boolean flag indicating whether the player should exist or not.

        """
        if should_exist and self.get_player_by_name(name) is None:
            raise ValueError(f"Player '{name}' not found.")
        if not should_exist and self.get_player_by_name(name) is not None:
            raise ValueError(f"Player '{name}' already exists.")

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
            team_number INTEGER,  -- 1 for {team1}, 2 for {team2}
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            PRIMARY KEY (match_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS last_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            team TEXT CHECK(team IN ('{team1}', '{team2}')) NOT NULL,
            bonus REAL
        );
        """.format(
                team1=teams.TEAM1, team2=teams.TEAM2
            )
        )
        self.conn.commit()

    def add_player(self, player: Player) -> Optional[int]:
        """
        Adds a new player to the database.

        :param player:
            The player to add to the database.

        :return:
            The ID of the newly added player.

        """
        self._validate_player_exists_by_name(player.name, should_exist=False)

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

    def remove_player(self, name: str) -> None:
        """
        Removes a player from the database.

        :param name:
            The name of the player to remove.

        """
        self._validate_player_exists_by_name(name, should_exist=True)

        self.cursor.execute("DELETE FROM players WHERE name = ?", (name,))
        self.conn.commit()

    def update_player_attribute(
        self, name: str, attribute: str, value: int
    ) -> None:
        """
        Updates a player's attribute.

        :param name:
            The name of the player to update.

        :param attribute:
            The attribute to update.

        :param value:
            The new value for the attribute.

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

        self._validate_player_exists_by_name(name, should_exist=True)

        if attribute not in valid_attributes:
            raise ValueError(f"Invalid attribute '{attribute}'.")

        self.cursor.execute(
            f"UPDATE players SET {attribute} = ? WHERE name = ?", (value, name)
        )
        self.conn.commit()

    def get_player_by_name(self, name: str) -> Optional[Player]:
        """
        Retrieves a player from the database by name.

        :param name:
            The name of the player to retrieve.

        :return:
            The player instance, or None if not found.

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

    def get_all_players(self) -> List[Dict]:
        """
        Retrieves all players from the database.
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

    def reset_player_forms(self) -> None:
        """
        Resets all players' forms to the default value (5).
        """
        self.cursor.execute("UPDATE players SET form = 5")
        self.conn.commit()

    def create_teams(
        self, player_names: List[str]
    ) -> Optional[Tuple[Team, Team]]:
        """
        Creates balanced teams using `TeamCreator` and stores them in the
        database.

        :param player_names:
            A list of player names to create teams from.

        :return:
            A tuple containing the two teams.

        """
        players = []
        for name in player_names:
            self._validate_player_exists_by_name(name, should_exist=True)
            player = self.get_player_by_name(name)
            players.append(player)

        if len(players) < 2:
            raise InvalidTeamsError("Not enough players to create teams.")

        team_creator = TeamCreator(
            players,
            len(players) // 2,
            len(players) - len(players) // 2,
        )
        team1, team2 = team_creator.create_balanced_teams()

        # Update last_teams table with the newly created teams.
        self.cursor.execute("DELETE FROM last_teams")

        for player in team1.players:
            self.cursor.execute(
                "INSERT INTO last_teams (player_name, team, bonus) VALUES (?, ?, ?)",
                (player.name, teams.TEAM1, team1.bonus),
            )
        for player in team2.players:
            self.cursor.execute(
                "INSERT INTO last_teams (player_name, team, bonus) VALUES (?, ?, ?)",
                (player.name, teams.TEAM2, team2.bonus),
            )

        self.conn.commit()

        return team1, team2

    def get_last_teams(self) -> Dict[str, Team]:
        """
        Retrieves the last stored teams from the database.

        :return:
            A dictionary mapping team names to `Team` instances.

        """
        self.cursor.execute("SELECT player_name, team, bonus FROM last_teams")
        rows = self.cursor.fetchall()

        team1_players = []
        team2_players = []
        team1_bonus = 0.0
        team2_bonus = 0.0

        for player_name, team, bonus in rows:
            if team == teams.TEAM1:
                team1_players.append(self.get_player_by_name(player_name))
                team1_bonus = bonus
            else:
                team2_players.append(self.get_player_by_name(player_name))
                team2_bonus = bonus

        return {
            teams.TEAM1: Team(
                [p for p in team1_players if p is not None],
                team1_bonus,
            ),
            teams.TEAM2: Team(
                [p for p in team2_players if p is not None],
                team2_bonus,
            ),
        }

    def record_match_result(self, winning_team: str) -> None:
        """
        Records the last match result and updates player form using the custom
        rating system.

        :param winning_team:
            The name of the winning team.

        """
        if winning_team not in (teams.TEAM1, teams.TEAM2):
            raise InvalidTeamsError(
                f"Invalid winning team: '{winning_team}'. Must be "
                f"'{teams.TEAM1}' or '{teams.TEAM2}'."
            )

        last_teams = self.get_last_teams()
        if (
            not last_teams[teams.TEAM1].players
            or not last_teams[teams.TEAM2].players
        ):
            raise NoLastTeamsError("No last teams found in the database.")

        team1_won = winning_team == teams.TEAM1
        team1 = last_teams[teams.TEAM1]
        team2 = last_teams[teams.TEAM2]

        # Update each player's form based on match outcome.
        for player in team1.players:
            player.update_form(won=team1_won)
        for player in team2.players:
            player.update_form(won=not team1_won)

        # Persist updated form to the database
        for player in team1.players + team2.players:
            self.cursor.execute(
                "UPDATE players SET form = ? WHERE name = ?",
                (player.form, player.name),
            )

        winner = 1 if team1_won else 2
        self.cursor.execute(
            "INSERT INTO matches (team_1_score, team_2_score, winner) VALUES (?, ?, ?)",
            (0, 0, winner),
        )

        self.cursor.execute("DELETE FROM last_teams")
        self.conn.commit()

    def export_to_csv(self, filename: str) -> None:
        """
        Exports the players table to a CSV file.

        :param filename:
            The name of the CSV file to export to.

        """
        self.cursor.execute(
            "SELECT id, name, shooting, dribbling, passing, tackling, fitness, goalkeeping, form FROM players"
        )
        rows = self.cursor.fetchall()
        headers = [desc[0] for desc in self.cursor.description]
        with open(filename, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    def import_from_csv(self, filename: str) -> int:
        """
        Imports players from a CSV file into the database.

        :param filename:
            The name of the CSV file to import from.

        :return:
            The number of players imported.

        """
        with open(filename, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    attributes = {
                        "shooting": float(row["shooting"]),
                        "dribbling": float(row["dribbling"]),
                        "passing": float(row["passing"]),
                        "tackling": float(row["tackling"]),
                        "fitness": float(row["fitness"]),
                        "goalkeeping": float(row["goalkeeping"]),
                    }
                    player_attributes = Attributes.from_values(attributes)
                    player = Player(
                        name=row["name"],
                        attributes=player_attributes,
                        form=int(row["form"]),
                    )
                    self.add_player(player)
                    count += 1
                except Exception as e:
                    print(
                        "⚠️ Could not import player "
                        f"{row.get('name', '<unknown>')}: {e}"
                    )
                    raise
        return count

    def clear_database(self):
        """
        Deletes all data from the database, resetting it to an empty state.
        """
        self.cursor.execute("DELETE FROM players")
        self.cursor.execute("DELETE FROM matches")
        self.cursor.execute("DELETE FROM match_players")
        self.cursor.execute("DELETE FROM last_teams")
        self.conn.commit()

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()


class InvalidTeamsError(Exception):
    """
    Raised when the teams cannot be created or are invalid.
    """

    pass


class NoLastTeamsError(Exception):
    """
    Raised when no last teams are stored in the database.
    """

    pass
