"""
CLI module for managing players, teams, and match results.
"""

import argparse
import os

from .db import DB
from .player import Attributes, Player

db = DB(db_name=os.getenv("FOOTBALL_DB", "football.db"))


def add_player(args):
    """Adds a new player to the database."""
    attributes = Attributes.from_values(
        {
            "shooting": args.shooting,
            "dribbling": args.dribbling,
            "passing": args.passing,
            "tackling": args.tackling,
            "fitness": args.fitness,
            "goalkeeping": args.goalkeeping,
        }
    )
    player = Player(name=args.name, attributes=attributes, form=5)
    db.add_player(player)
    print(f"✅ Player '{args.name}' added!")


def remove_player(args):
    """Removes a player from the database."""
    db.remove_player(args.name)
    print(f"🗑️ Player '{args.name}' removed.")


def update_player(args):
    """Updates a player's attribute."""

    attributes_map = {
        "s": "shooting",
        "d": "dribbling",
        "p": "passing",
        "t": "tackling",
        "f": "fitness",
        "g": "goalkeeping",
    }

    attribute = args.attribute
    if args.attribute in attributes_map:
        attribute = attributes_map[args.attribute]

    db.update_player_attribute(args.name, attribute, args.value)
    print(f"🔄 Updated {attribute} of '{args.name}' to {args.value}.")


def get_player_rating(args):
    """Displays a player's overall rating."""
    player = db.get_player_by_name(args.name)
    if player:
        print(f"⭐ {args.name}'s Rating: {player.get_overall_rating()}")
    else:
        print(f"❌ Player '{args.name}' not found.")


def list_players(args):
    """Lists all players in the database with all attributes in a table format."""
    players = db.get_all_players()

    if not players:
        print("❌ No players found in the database.")
        return

    # Define the column headers
    headers = [
        "Name",
        "Form",
        "Shooting",
        "Dribbling",
        "Passing",
        "Tackling",
        "Fitness",
        "Goalkeeping",
    ]

    # Define a format string with fixed widths (adjust widths as needed)
    format_str = "{:<20} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}"

    print("\n📋 **Players in Database:**")
    # Print the header row
    print(format_str.format(*headers))
    print("-" * 100)  # Optional separator line

    # Print each player's data row
    for player in players:
        print(
            format_str.format(
                player["name"],
                player["form"],
                player["shooting"],
                player["dribbling"],
                player["passing"],
                player["tackling"],
                player["fitness"],
                player["goalkeeping"],
            )
        )


def create_teams(args):
    """Creates balanced teams from given player names."""
    team1, team2 = db.create_teams(args.players)
    if team1 and team2:
        print("✅ Teams created successfully!")
        print("\n🏆 **Team 1:**")
        print(
            f"  Rating: {round(team1.get_overall_rating(),2)} "
            f"Bonus: {team1.bonus}\n"
        )
        for player in team1.players:
            print(
                f"- {player.name} (Rating: {round(player.get_overall_rating(),2)})"
            )

        print("\n🔥 **Team 2:**")
        print(
            f"  Rating: {round(team2.get_overall_rating(),2)} "
            f"Bonus: {team2.bonus}\n"
        )
        for player in team2.players:
            print(
                f"- {player.name} (Rating: {round(player.get_overall_rating(),2)})"
            )
    else:
        print("❌ Error: Could not create teams. Check player names.")


def record_match_result(args):
    """Records the last match result and updates player form."""
    db.record_match_result(args.winning_team)
    print(f"✅ Match recorded: {args.winning_team} won!")


def get_team_attributes(args):
    """Displays the attribute ratings of the last generated team."""
    teams = db.get_last_teams()
    team_key = args.team

    if not teams[team_key]:
        print(f"❌ No previous team '{team_key}' found.")
        return

    print(f"\n📊 **{team_key.capitalize()} Attributes:**")
    attributes = [
        "shooting",
        "dribbling",
        "passing",
        "tackling",
        "fitness",
        "goalkeeping",
    ]
    for attr in attributes:
        avg_rating = sum(
            getattr(player.attributes, attr).score
            for player in teams[team_key].players
        ) / len(teams[team_key].players)
        print(f"- {attr.capitalize()}: {avg_rating:.2f}")


def get_team_rating(args):
    """Displays the overall team rating of the last generated team."""
    team_key = "team1" if args.team == "team1" else "team2"
    teams = db.get_last_teams()
    team = teams[team_key]

    if not team:
        print(f"❌ No previous team '{team_key}' found.")
        return

    overall_rating = team.get_overall_rating()
    print(
        f"\n⭐ **{team_key.capitalize()} Overall Rating:** "
        f"{overall_rating:.2f}"
    )


def clear_database(args):
    """Clears all players, matches, and team history from the database."""
    db.clear_database()
    print("🗑️ All data has been removed from the database.")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Football Team Manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Player Subcommands
    player_parser = subparsers.add_parser("player", help="Manage players")
    player_subparsers = player_parser.add_subparsers(
        dest="action", required=True
    )

    # Add player
    add_parser = player_subparsers.add_parser("add", help="Add a new player")
    add_parser.add_argument("name", type=str, help="Player's name")
    add_parser.add_argument(
        "-s",
        "--shooting",
        type=int,
        required=True,
        help="Shooting skill (1-10)",
    )
    add_parser.add_argument(
        "-d",
        "--dribbling",
        type=int,
        required=True,
        help="Dribbling skill (1-10)",
    )
    add_parser.add_argument(
        "-p", "--passing", type=int, required=True, help="Passing skill (1-10)"
    )
    add_parser.add_argument(
        "-t",
        "--tackling",
        type=int,
        required=True,
        help="Tackling skill (1-10)",
    )
    add_parser.add_argument(
        "-f", "--fitness", type=int, required=True, help="Fitness level (1-10)"
    )
    add_parser.add_argument(
        "-g",
        "--goalkeeping",
        type=int,
        required=True,
        help="Goalkeeping skill (1-10)",
    )
    add_parser.set_defaults(func=add_player)

    # Remove player
    remove_parser = player_subparsers.add_parser(
        "remove", help="Remove a player"
    )
    remove_parser.add_argument("name", type=str, help="Player's name")
    remove_parser.set_defaults(func=remove_player)

    # Update player
    update_parser = player_subparsers.add_parser(
        "update", help="Update a player's skill"
    )
    update_parser.add_argument("name", type=str, help="Player's name")
    update_parser.add_argument(
        "attribute", type=str, help="Attribute to update"
    )
    update_parser.add_argument("value", type=int, help="New value")
    update_parser.set_defaults(func=update_player)

    # Get player rating
    rating_parser = player_subparsers.add_parser(
        "rating", help="Get a player's rating"
    )
    rating_parser.add_argument("name", type=str, help="Player's name")
    rating_parser.set_defaults(func=get_player_rating)

    # List players
    list_parser = player_subparsers.add_parser("list", help="List all players")
    list_parser.set_defaults(func=list_players)

    # Team Subcommands
    team_parser = subparsers.add_parser("teams", help="Manage teams & matches")
    team_subparsers = team_parser.add_subparsers(dest="action", required=True)

    # Create teams
    create_parser = team_subparsers.add_parser(
        "create", help="Create balanced teams"
    )
    create_parser.add_argument(
        "players", nargs="+", type=str, help="List of player names"
    )
    create_parser.set_defaults(func=create_teams)

    # Record match result
    result_parser = team_subparsers.add_parser(
        "result", help="Record match result"
    )
    result_parser.add_argument(
        "winning_team", choices=["team1", "team2"], help="Winning team"
    )
    result_parser.set_defaults(func=record_match_result)

    # Get team attributes
    attr_parser = team_subparsers.add_parser(
        "attributes", help="Get team attribute ratings"
    )
    attr_parser.add_argument(
        "team", choices=["team1", "team2"], help="Select team"
    )
    attr_parser.set_defaults(func=get_team_attributes)

    # Get team rating
    rating_parser = team_subparsers.add_parser(
        "rating", help="Get overall team rating"
    )
    rating_parser.add_argument(
        "team", choices=["team1", "team2"], help="Select team"
    )
    rating_parser.set_defaults(func=get_team_rating)

    # Clear the database
    database_parser = subparsers.add_parser("database", help="Manage database")
    database_subparsers = database_parser.add_subparsers(
        dest="action", required=True
    )

    clear_parser = database_subparsers.add_parser(
        "clear", help="Clear all database data"
    )
    clear_parser.set_defaults(func=clear_database)

    # Parse arguments & call respective function
    args = parser.parse_args()
    args.func(args)
