"""
CLI module for managing players, teams, match results, and CSV import/export.
"""

import argparse
import os

from .db import DB
from .player import Attributes, Player

# Initialize the database connection.
db = DB(db_name=os.getenv("FOOTBALL_DB", "football.db"))


# --------------------------
# Player Command Handlers
# --------------------------


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
    attribute = attributes_map.get(args.attribute, args.attribute)
    db.update_player_attribute(args.name, attribute, args.value)
    print(f"🔄 Updated {attribute} of '{args.name}' to {args.value}.")


def list_players(args):
    """Lists all players in the database."""
    players = db.get_all_players()
    if not players:
        print("❌ No players found in the database.")
        return

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
    format_str = "{:<20} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}"
    print("\n📋 **Players in Database:**")
    print(format_str.format(*headers))
    print("-" * 100)
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


def list_player_attributes(args):
    """
    Lists all the attribute values for a given player.
    Usage: player attributes <player_name>
    """
    player = db.get_player_by_name(args.name)
    if not player:
        print(f"❌ Player '{args.name}' not found.")
        return

    print(f"\n📊 Attributes for {player.name}:")
    print(f"  Shooting:        {player.attributes.shooting.get_score()}")
    print(f"  Dribbling:       {player.attributes.dribbling.get_score()}")
    print(f"  Passing:         {player.attributes.passing.get_score()}")
    print(f"  Tackling:        {player.attributes.tackling.get_score()}")
    print(f"  Fitness:         {player.attributes.fitness.get_score()}")
    print(f"  Goalkeeping:     {player.attributes.goalkeeping.get_score()}")
    print(f"⭐ Overall Rating: {player.get_overall_rating(round_num=True)}")


def rank_players(args):
    """
    Ranks players based on overall rating or a specific attribute.

    Usage:
      - If an attribute (e.g. "shooting", "dribbling", etc.) is provided,
        players are ranked based on that attribute.
      - If no attribute is provided, rankings for overall rating and all
        individual attributes are displayed.

    Valid attribute values are: overall, shooting, dribbling, passing, tackling,
    fitness, goalkeeping.
    """
    # Retrieve full player instances from the database.
    players = [db.get_player_by_name(p["name"]) for p in db.get_all_players()]
    if not players:
        print("❌ No players found in the database.")
        return

    def print_ranking(title, key_func):
        sorted_players = sorted(players, key=key_func, reverse=True)
        print(f"\n🏅 Ranking by {title}:")
        for i, player in enumerate(sorted_players, 1):
            if title.lower() == "overall rating":
                score = player.get_overall_rating()
            else:
                # Dynamically retrieve the attribute score.
                attr_obj = getattr(player.attributes, title.lower())
                score = attr_obj.get_score()
            print(f"{i}. {player.name} - {title}: {score:.2f}")

    # If no attribute is provided, default to showing all rankings.
    if not args.attribute:
        print_ranking("Overall Rating", lambda p: p.get_overall_rating())
        for attr in [
            "shooting",
            "dribbling",
            "passing",
            "tackling",
            "fitness",
            "goalkeeping",
        ]:
            print_ranking(
                attr.capitalize(),
                lambda p, a=attr: getattr(p.attributes, a).get_score(),
            )
    else:
        attr = args.attribute.lower()
        if attr == "overall":
            print_ranking("Overall Rating", lambda p: p.get_overall_rating())
        elif attr in [
            "shooting",
            "dribbling",
            "passing",
            "tackling",
            "fitness",
            "goalkeeping",
        ]:
            print_ranking(
                attr.capitalize(),
                lambda p: getattr(p.attributes, attr).get_score(),
            )
        else:
            print(
                f"❌ Invalid attribute '{args.attribute}'. Valid options are "
                "overall, shooting, dribbling, passing, tackling, fitness, "
                "goalkeeping."
            )


# --------------------------
# Team Command Handlers
# --------------------------
def create_teams(args):
    """Creates balanced teams from given player names."""
    team1, team2 = db.create_teams(args.players)
    if team1 and team2:
        print("✅ Teams created successfully!")
        print("\n🏆 **Team 1:**")
        print(
            f"  Rating: {team1.get_overall_rating(round_num=True)} Bonus: {team1.bonus}\n"
        )
        for player in team1.players:
            print(
                f"- {player.name} (Rating: {player.get_overall_rating(round_num=True)})"
            )

        print("\n🔥 **Team 2:**")
        print(
            f"  Rating: {team2.get_overall_rating(round_num=True)} Bonus: {team2.bonus}\n"
        )
        for player in team2.players:
            print(
                f"- {player.name} (Rating: {player.get_overall_rating(round_num=True)})"
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
    for attr in [
        "shooting",
        "dribbling",
        "passing",
        "tackling",
        "fitness",
        "goalkeeping",
    ]:
        avg_rating = sum(
            getattr(player.attributes, attr).score
            for player in teams[team_key].players
        ) / len(teams[team_key].players)
        print(f"- {attr.capitalize()}: {avg_rating:.2f}")


def get_team_rating(args):
    """Displays the overall team rating of the last generated team."""
    teams = db.get_last_teams()
    team = teams[args.team]
    if not team:
        print(f"❌ No previous team '{args.team}' found.")
        return
    overall_rating = team.get_overall_rating()
    print(
        f"\n⭐ **{args.team.capitalize()} Overall Rating:** {overall_rating:.2f}"
    )


# --------------------------
# Database Command Handlers
# --------------------------
def clear_database(args):
    """Clears all players, matches, and team history from the database."""
    db.clear_database()
    print("🗑️ All data has been removed from the database.")


def export_csv(args):
    """Exports the players table to a CSV file."""
    db.export_to_csv(args.filename)


def import_csv(args):
    """Imports players from a CSV file into the database."""
    db.import_from_csv(args.filename)


# --------------------------
# Subparser Setup Functions
# --------------------------
def setup_player_subparser(subparsers):
    player_parser = subparsers.add_parser("player", help="Manage players")
    player_subparsers = player_parser.add_subparsers(
        dest="action", required=True
    )

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

    remove_parser = player_subparsers.add_parser(
        "remove", help="Remove a player"
    )
    remove_parser.add_argument("name", type=str, help="Player's name")
    remove_parser.set_defaults(func=remove_player)

    reset_parser = player_subparsers.add_parser(
        "reset_forms", help="Reset all player forms to default (5)"
    )
    reset_parser.set_defaults(func=lambda args: db.reset_player_forms())

    update_parser = player_subparsers.add_parser(
        "update", help="Update a player's skill"
    )
    update_parser.add_argument("name", type=str, help="Player's name")
    update_parser.add_argument(
        "attribute", type=str, help="Attribute to update"
    )
    update_parser.add_argument("value", type=int, help="New value")
    update_parser.set_defaults(func=update_player)

    attr_parser = player_subparsers.add_parser(
        "attributes", help="Show a player's attributes"
    )
    attr_parser.add_argument("name", type=str, help="Player's name")
    attr_parser.set_defaults(func=list_player_attributes)

    list_parser = player_subparsers.add_parser("list", help="List all players")
    list_parser.set_defaults(func=list_players)

    rank_parser = player_subparsers.add_parser(
        "rank", help="Rank players by overall rating or attribute"
    )
    rank_parser.add_argument(
        "attribute",
        nargs="?",
        help=(
            "Attribute to rank by (overall, shooting, dribbling, passing, "
            "tackling, fitness, goalkeeping). If omitted, all rankings will "
            "be shown."
        ),
    )
    rank_parser.set_defaults(func=rank_players)


def setup_team_subparser(subparsers):
    team_parser = subparsers.add_parser("teams", help="Manage teams & matches")
    team_subparsers = team_parser.add_subparsers(dest="action", required=True)

    create_parser = team_subparsers.add_parser(
        "create", help="Create balanced teams"
    )
    create_parser.add_argument(
        "players", nargs="+", type=str, help="List of player names"
    )
    create_parser.set_defaults(func=create_teams)

    result_parser = team_subparsers.add_parser(
        "result", help="Record match result"
    )
    result_parser.add_argument(
        "winning_team", choices=["team1", "team2"], help="Winning team"
    )
    result_parser.set_defaults(func=record_match_result)

    attr_parser = team_subparsers.add_parser(
        "attributes", help="Get team attribute ratings"
    )
    attr_parser.add_argument(
        "team", choices=["team1", "team2"], help="Select team"
    )
    attr_parser.set_defaults(func=get_team_attributes)

    rating_parser = team_subparsers.add_parser(
        "rating", help="Get overall team rating"
    )
    rating_parser.add_argument(
        "team", choices=["team1", "team2"], help="Select team"
    )
    rating_parser.set_defaults(func=get_team_rating)


def setup_database_subparser(subparsers):
    database_parser = subparsers.add_parser("database", help="Manage database")
    database_subparsers = database_parser.add_subparsers(
        dest="action", required=True
    )

    clear_parser = database_subparsers.add_parser(
        "clear", help="Clear all database data"
    )
    clear_parser.set_defaults(func=clear_database)

    export_parser = database_subparsers.add_parser(
        "export", help="Export players to a CSV file"
    )
    export_parser.add_argument(
        "filename",
        type=str,
        nargs="?",
        default="players_export.csv",
        help="Output CSV filename",
    )
    export_parser.set_defaults(func=export_csv)

    import_parser = database_subparsers.add_parser(
        "import", help="Import players from a CSV file"
    )
    import_parser.add_argument(
        "filename",
        type=str,
        nargs="?",
        default="players_import.csv",
        help="Input CSV filename",
    )
    import_parser.set_defaults(func=import_csv)


# --------------------------
# Main CLI Entry Point
# --------------------------
def main():
    parser = argparse.ArgumentParser(description="Football Team Manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_player_subparser(subparsers)
    setup_team_subparser(subparsers)
    setup_database_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
