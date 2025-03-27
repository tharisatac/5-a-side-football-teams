"""
CLI module for managing players, teams, match results, and CSV import/export.
"""

import argparse
import colorama
import os
from . import teams

from .db import DB
from .player import Attributes, Player

DEFAULT_FILENAME = "players.csv"

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
    try:
        db.add_player(player)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return None
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
    try:
        db.update_player_attribute(args.name, attribute, args.value)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return
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


def reset_player_forms():
    """Resets all player forms to the default value of 5."""
    try:
        db.reset_player_forms()
        print("✅ Player forms reset to default value of 5.")
    except Exception as e:
        print(f"❌ Error resetting player forms: {e}")


# --------------------------
# Team Command Handlers
# --------------------------


def create_teams(args):
    """Creates balanced teams from given player names."""
    try:
        team1, team2 = db.create_teams(args.players)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return

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
    print("✅ Database cleared successfully!")


def export_csv(args):
    """Exports the players table to a CSV file."""
    try:
        db.export_to_csv(args.filename)
        print(f"✅ Exported players to '{args.filename}'.")
    except Exception as e:
        print(f"❌ Error exporting players: {e}")


def import_csv(args):
    """Imports players from a CSV file into the database."""
    try:
        count = db.import_from_csv(args.filename)
        print(f"✅ Imported {count} players from '{args.filename}'.")
    except FileNotFoundError:
        print(f"❌ File '{args.filename}' not found.")
    except Exception as e:
        print(f"❌ Error importing players: {e}")


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
    reset_parser.set_defaults(func=reset_player_forms)

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
        "winning_team", choices=[teams.TEAM1, teams.TEAM2], help="Winning team"
    )
    result_parser.set_defaults(func=record_match_result)

    attr_parser = team_subparsers.add_parser(
        "attributes", help="Get team attribute ratings"
    )
    attr_parser.add_argument(
        "team", choices=[teams.TEAM1, teams.TEAM2], help="Select team"
    )
    attr_parser.set_defaults(func=get_team_attributes)

    rating_parser = team_subparsers.add_parser(
        "rating", help="Get overall team rating"
    )
    rating_parser.add_argument(
        "team", choices=[teams.TEAM1, teams.TEAM2], help="Select team"
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
        default=DEFAULT_FILENAME,
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
        default=DEFAULT_FILENAME,
        help="Input CSV filename",
    )
    import_parser.set_defaults(func=import_csv)


# --------------------------
# Interactive Functions
# --------------------------

def prompt_input(message, options=None):
    """Helper function to prompt user input with options."""
    options_text = f" ({'/'.join(options)})" if options else ""
    return (
        input(
            f"{colorama.Fore.GREEN}{message}{colorama.Fore.YELLOW}{options_text}: "
            f"{colorama.Fore.RESET}"
        )
        .strip()
        .lower()
    )


def validate_input(prompt, validation_func, error_message):
    """Validates input using a validation function."""
    while True:
        try:
            value = validation_func(input(prompt).strip())
            return value
        except ValueError:
            print(f"{colorama.Fore.RED}{error_message}")


def execute_command(command, command_map, error_message):
    """Executes a command from a command map."""
    if command in command_map:
        command_map[command]()
    else:
        print(f"{colorama.Fore.RED}{error_message}")


# --------------------------
#  Interactive Player Functions
# --------------------------


def add_player_interactive():
    """ Interactive function to add a player to the database. """
    player_name = prompt_input("Enter player name")
    skills = {
        skill: get_skill_input(skill)
        for skill in [
            "shooting",
            "dribbling",
            "passing",
            "tackling",
            "fitness",
            "goalkeeping",
        ]
    }
    add_player(argparse.Namespace(name=player_name, **skills))


def update_player_interactive():
    """ Interactive function to update a player's attribute. """
    player_name = prompt_input("Enter player name to update")
    attribute = prompt_input(
        "Enter attribute to update",
        [
            "shooting",
            "dribbling",
            "passing",
            "tackling",
            "fitness",
            "goalkeeping",
        ],
    )
    value = validate_input(
        f"{colorama.Fore.YELLOW}Enter new value for {attribute} (1-10): "
        f"{colorama.Fore.RESET}",
        lambda x: int(x) if 1 <= int(x) <= 10 else ValueError,
        "Invalid input. Please enter a number between 1 and 10.",
    )
    update_player(
        argparse.Namespace(name=player_name, attribute=attribute, value=value)
    )


def handle_player_interactive():
    """ Interactive function to handle player commands. """
    command_map = {
        "add": add_player_interactive,
        "a": add_player_interactive,
        "remove": lambda: remove_player(
            argparse.Namespace(
                name=prompt_input("Enter player name to remove")
            )
        ),
        "r": lambda: remove_player(
            argparse.Namespace(
                name=prompt_input("Enter player name to remove")
            )
        ),
        "reset_forms": lambda: reset_player_forms(argparse.Namespace()),
        "reset": lambda: reset_player_forms(argparse.Namespace()),
        "update": update_player_interactive,
        "u": update_player_interactive,
        "attributes": lambda: list_player_attributes(
            argparse.Namespace(
                name=prompt_input("Enter player name to view attributes")
            )
        ),
        "attr": lambda: list_player_attributes(
            argparse.Namespace(
                name=prompt_input("Enter player name to view attributes")
            )
        ),
        "list": lambda: list_players(argparse.Namespace()),
        "l": lambda: list_players(argparse.Namespace()),
        "rank": lambda: rank_players(
            argparse.Namespace(
                attribute=prompt_input(
                    "Enter attribute to rank by",
                    [
                        "overall",
                        "shooting",
                        "dribbling",
                        "passing",
                        "tackling",
                        "fitness",
                        "goalkeeping",
                    ],
                )
            )
        ),
    }
    while True:
        try:
            player_command = prompt_input(
                "Enter player command",
                [
                    "add(a)",
                    "remove(r)",
                    "reset_forms(reset)",
                    "update(u)",
                    "attributes(attr)",
                    "list(l)",
                    "rank",
                    "back(b)",
                ],
            )
            if player_command in ["back", "b"]:
                break
            execute_command(
                player_command,
                command_map,
                "Invalid player command. Please try again.",
            )
        except Exception as e:
            print(f"{colorama.Fore.RED}An error occurred: {e}")


# --------------------------
# Interactive Team Functions
# --------------------------


def handle_team_interactive():
    """ Interactive function to handle team commands. """
    command_map = {
        "create": lambda: create_teams(
            argparse.Namespace(
                players=prompt_input(
                    "Enter player names separated by spaces"
                ).split()
            )
        ),
        "c": lambda: create_teams(
            argparse.Namespace(
                players=prompt_input(
                    "Enter player names separated by spaces"
                ).split()
            )
        ),
        "result": lambda: record_match_result(
            argparse.Namespace(
                winning_team=prompt_input(
                    "Enter winning team", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
        "res": lambda: record_match_result(
            argparse.Namespace(
                winning_team=prompt_input(
                    "Enter winning team", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
        "attributes": lambda: get_team_attributes(
            argparse.Namespace(
                team=prompt_input(
                    "Select team for attributes", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
        "attr": lambda: get_team_attributes(
            argparse.Namespace(
                team=prompt_input(
                    "Select team for attributes", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
        "rating": lambda: get_team_rating(
            argparse.Namespace(
                team=prompt_input(
                    "Select team for rating", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
        "r": lambda: get_team_rating(
            argparse.Namespace(
                team=prompt_input(
                    "Select team for rating", [teams.TEAM1, teams.TEAM2]
                )
            )
        ),
    }
    while True:
        try:
            team_command = prompt_input(
                "Enter team command",
                [
                    "create(c)",
                    "result(res)",
                    "attributes(attr)",
                    "rating(r)",
                    "back(b)",
                ],
            )
            if team_command in ["back", "b"]:
                break
            execute_command(
                team_command,
                command_map,
                "Invalid team command. Please try again.",
            )
        except Exception as e:
            print(f"{colorama.Fore.RED}An error occurred: {e}")


# --------------------------
# Interactive Database Functions
# --------------------------


def handle_database_interactive():
    """ Handle interactive database commands. """
    command_map = {
        "clear": lambda: clear_database(argparse.Namespace()),
        "c": lambda: clear_database(argparse.Namespace()),
        "export": lambda: export_csv(
            argparse.Namespace(
                filename=prompt_input("Enter filename for export")
                or DEFAULT_FILENAME
            )
        ),
        "e": lambda: export_csv(
            argparse.Namespace(
                filename=prompt_input("Enter filename for export")
                or DEFAULT_FILENAME
            )
        ),
        "import": lambda: import_csv(
            argparse.Namespace(
                filename=prompt_input("Enter filename for import")
                or DEFAULT_FILENAME
            )
        ),
        "i": lambda: import_csv(
            argparse.Namespace(
                filename=prompt_input("Enter filename for import")
                or DEFAULT_FILENAME
            )
        ),
    }
    while True:
        try:
            database_command = prompt_input(
                "Enter database command",
                ["clear(c)", "export(e)", "import(i)", "back(b)"],
            )
            if database_command in ["back", "b"]:
                break
            execute_command(
                database_command,
                command_map,
                "Invalid database command. Please try again.",
            )
        except Exception as e:
            print(f"{colorama.Fore.RED}An error occurred: {e}")


# --------------------------
# Interactive Skill Input Function
# --------------------------


def get_skill_input(skill_name):
    """ Get a skill input from the user. """
    return validate_input(
        f"{colorama.Fore.YELLOW}Enter {skill_name} skill (1-10): "
        f"{colorama.Fore.RESET}",
        lambda x: int(x) if 1 <= int(x) <= 10 else ValueError,
        "Invalid input. Please enter a number between 1 and 10.",
    )


# --------------------------
# Main CLI Entry Point
# --------------------------


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Football Team Manager CLI"
        )
        subparsers = parser.add_subparsers(dest="command", required=False)

        # Setup subparsers for different commands
        setup_player_subparser(subparsers)
        setup_team_subparser(subparsers)
        setup_database_subparser(subparsers)

        args = parser.parse_args()

        if args.command:
            args.func(args)
        else:
            while True:
                print(
                    f"\n{colorama.Fore.CYAN}Welcome to the Football Team Creator!"
                )
                command = prompt_input(
                    "Enter command",
                    ["player(p)", "team(t)", "database(d)", "exit"],
                )

                if command in ["player", "p"]:
                    handle_player_interactive()
                elif command in ["team", "t"]:
                    handle_team_interactive()
                elif command in ["database", "d"]:
                    handle_database_interactive()
                elif command == "exit":
                    print(f"{colorama.Fore.RED}Exiting the program.")
                    break
                else:
                    print(
                        f"{colorama.Fore.RED}Invalid command. Please try again."
                    )
    except Exception as e:
        print(f"{colorama.Fore.RED}An error occurred: {e}")


if __name__ == "__main__":
    main()
