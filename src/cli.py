"""
CLI module for managing players, teams, match results, and CSV import/export.

Every command handler takes the repository as its first argument. `main`
creates it once and passes it in, so nothing here opens a database at import
time.
"""

import argparse
import os
from typing import List, Optional

from . import csv_io, services
from .player import ATTRIBUTE_NAMES, DEFAULT_FORM, Attributes, Player
from .repository import (
    TEAM_KEYS,
    Match,
    MatchAlreadyRecordedError,
    MatchNotFoundError,
    PlayerAlreadyExistsError,
    PlayerHasMatchesError,
    PlayerNotFoundError,
    Repository,
)
from .sqlite_repository import DEFAULT_DB_PATH, SqliteRepository
from .teams import DuplicatePlayerError, NotEnoughPlayersError, Team

# Errors caused by user input. They are printed as a message; anything else
# is a bug and is left to crash with a full traceback.
USER_ERRORS = (
    PlayerNotFoundError,
    PlayerAlreadyExistsError,
    PlayerHasMatchesError,
    MatchNotFoundError,
    MatchAlreadyRecordedError,
    DuplicatePlayerError,
    NotEnoughPlayersError,
    services.InvalidAttrError,
    ValueError,
    OSError,
)


# --------------------------
# Player Command Handlers
# --------------------------


def add_player(repo: Repository, args: argparse.Namespace) -> None:
    """
    Adds a new player to the database.
    Usage: player add <player_name> -s <1-10> -d <1-10> ...

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `name` and one value per attribute.
    """
    attributes = Attributes.from_values(
        {name: getattr(args, name) for name in ATTRIBUTE_NAMES}
    )
    player = Player(name=args.name, attributes=attributes, form=DEFAULT_FORM)
    repo.add_player(player)
    print(f"✅ Player '{args.name}' added!")


def remove_player(repo: Repository, args: argparse.Namespace) -> None:
    """
    Removes a player who has never played in a match.
    Usage: player remove <player_name>

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `name`.
    """
    repo.remove_player(args.name)
    print(f"🗑️ Player '{args.name}' removed.")


def update_player(repo: Repository, args: argparse.Namespace) -> None:
    """
    Updates a player's attribute or form.
    Usage: player update <player_name> <attribute> <value>

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `name`, `attribute` (full name or
        first letter, or "form") and `value`.
    """
    attributes_map = {
        "s": "shooting",
        "d": "dribbling",
        "p": "passing",
        "t": "tackling",
        "f": "fitness",
        "g": "goalkeeping",
    }
    attribute = attributes_map.get(args.attribute, args.attribute)
    services.update_player_field(repo, args.name, attribute, args.value)
    print(f"🔄 Updated {attribute} of '{args.name}' to {args.value}.")


def list_players(repo: Repository, args: argparse.Namespace) -> None:
    """
    Lists all players in the database.
    Usage: player list

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments (none are used).
    """
    players = repo.list_players()
    if not players:
        print("❌ No players found in the database.")
        return

    headers = ["Name", "Form"] + [
        name.capitalize() for name in ATTRIBUTE_NAMES
    ]
    format_str = "{:<20} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}"
    print("\n📋 **Players in Database:**")
    print(format_str.format(*headers))
    print("-" * 100)
    for player in players:
        values = player.attributes.to_values()
        print(
            format_str.format(
                player.name,
                player.form,
                *(values[name] for name in ATTRIBUTE_NAMES),
            )
        )


def list_player_attributes(repo: Repository, args: argparse.Namespace) -> None:
    """
    Lists all the attribute values for a given player.
    Usage: player attributes <player_name>

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `name`.
    """
    player = repo.get_player(args.name)
    if not player:
        raise PlayerNotFoundError(args.name)

    print(f"\n📊 Attributes for {player.name}:")
    for name, score in player.attributes.to_values().items():
        print(f"  {name.capitalize() + ':':<17}{score}")
    print(f"⭐ Overall Rating: {player.get_overall_rating(round_num=True)}")


def rank_players(repo: Repository, args: argparse.Namespace) -> None:
    """
    Ranks players based on overall rating or a specific attribute.

    Usage:
      - If an attribute (e.g. "shooting", "dribbling", etc.) is provided,
        players are ranked based on that attribute.
      - If no attribute is provided, rankings for overall rating and all
        individual attributes are displayed.

    Valid attribute values are: overall, shooting, dribbling, passing, tackling,
    fitness, goalkeeping.

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `attribute` (optional).
    """
    attr = args.attribute.lower() if args.attribute else None
    if attr is not None and attr != "overall" and attr not in ATTRIBUTE_NAMES:
        raise services.InvalidAttrError(args.attribute)

    players = repo.list_players()
    if not players:
        print("❌ No players found in the database.")
        return

    # If no attribute is provided, default to showing all rankings.
    for attr_name in [attr] if attr else ("overall",) + ATTRIBUTE_NAMES:
        title = (
            "Overall Rating"
            if attr_name == "overall"
            else attr_name.capitalize()
        )
        ranked = sorted(
            players, key=lambda p: _score(p, attr_name), reverse=True
        )
        print(f"\n🏅 Ranking by {title}:")
        for i, player in enumerate(ranked, 1):
            print(f"{i}. {player.name}: {_score(player, attr_name):.2f}")


def _score(player: Player, attr_name: str) -> float:
    """
    Returns the player's overall rating, or their score for one attribute.

    :param player:
        The player to score.
    :param attr_name:
        "overall", or an attribute name such as "shooting".
    """
    if attr_name == "overall":
        return player.get_overall_rating()
    return getattr(player.attributes, attr_name).get_score()


def reset_forms(repo: Repository, args: argparse.Namespace) -> None:
    """
    Resets all players' forms to the default value.
    Usage: player reset_forms

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments (none are used).
    """
    repo.reset_forms(DEFAULT_FORM)
    print(f"✅ All player forms have been reset to {DEFAULT_FORM}.")


# --------------------------
# Team Command Handlers
# --------------------------


def _get_match(repo: Repository, match_id: Optional[int]) -> Match:
    """
    Returns the given match, or the latest one if `match_id` is None.

    :param repo:
        Where players and matches are stored.
    :param match_id:
        The match ID from `--match`, or None for the latest match.

    :raises:
        MatchNotFoundError: If the match does not exist, or there are none.
    """
    if match_id is None:
        match = repo.get_latest_match()
    else:
        match = repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    return match


def _match_label(match: Match) -> str:
    """
    Returns e.g. "match #3, 28 Oct 2026", using the local date.

    :param match:
        The match to describe.
    """
    created = match.created_at.astimezone()
    return f"match #{match.id}, {created.day} {created:%b %Y}"


def _print_team(title: str, team: Team) -> None:
    """
    Prints a team's rating, bonus and players.

    :param title:
        The heading to print above the team.
    :param team:
        The team to print.
    """
    print(f"\n{title}")
    print(
        f"  Rating: {team.get_overall_rating(round_num=True)} "
        f"Bonus: {team.bonus}\n"
    )
    for player in team.players:
        print(
            f"- {player.name} "
            f"(Rating: {player.get_overall_rating(round_num=True)})"
        )


def create_teams(repo: Repository, args: argparse.Namespace) -> None:
    """
    Creates balanced teams from the given player names, as a new match.
    Usage: teams create <player_name> ...

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `players`.
    """
    match = services.create_match(repo, args.players)
    print(f"✅ Teams created successfully! ({_match_label(match)})")
    _print_team("🏆 **Team 1:**", match.team1)
    _print_team("🔥 **Team 2:**", match.team2)
    print("")


def record_match_result(repo: Repository, args: argparse.Namespace) -> None:
    """
    Records a match result and updates players' form.
    Usage: teams result <team1|team2> [--match N]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `winning_team` and `match` (None for
        the latest match).
    """
    match = _get_match(repo, args.match)
    services.record_result(repo, match.id, args.winning_team)
    print(
        f"✅ Match recorded: {args.winning_team} won! "
        f"({_match_label(match)})"
    )


def cancel_match(repo: Repository, args: argparse.Namespace) -> None:
    """
    Deletes a match that hasn't been played.
    Usage: teams cancel [--match N]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `match` (None for the latest match).
    """
    match = _get_match(repo, args.match)
    services.cancel_match(repo, match.id)
    print(f"🗑️ Cancelled {_match_label(match)}.")


def get_team_attributes(repo: Repository, args: argparse.Namespace) -> None:
    """
    Displays the average attributes of a team.
    Usage: teams attributes <team1|team2> [--match N]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `team` and `match` (None for the
        latest match).
    """
    match = _get_match(repo, args.match)
    team = match.team(args.team)
    if not team.players:
        print(
            f"❌ Team '{args.team}' has no players "
            f"({_match_label(match)})."
        )
        return

    print(
        f"\n📊 **{args.team.capitalize()} Attributes:** "
        f"({_match_label(match)})"
    )
    for attr in ATTRIBUTE_NAMES:
        avg_rating = sum(
            getattr(player.attributes, attr).score for player in team.players
        ) / len(team.players)
        print(f"- {attr.capitalize()}: {avg_rating:.2f}")


def get_team_rating(repo: Repository, args: argparse.Namespace) -> None:
    """
    Displays the overall rating of a team.
    Usage: teams rating <team1|team2> [--match N]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `team` and `match` (None for the
        latest match).
    """
    match = _get_match(repo, args.match)
    overall_rating = match.team(args.team).get_overall_rating()
    print(
        f"\n⭐ **{args.team.capitalize()} Overall Rating:** "
        f"{overall_rating:.2f} ({_match_label(match)})"
    )


# --------------------------
# Database Command Handlers
# --------------------------


def clear_database(repo: Repository, args: argparse.Namespace) -> None:
    """
    Clears all players and matches from the database.
    Usage: database clear

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments (none are used).
    """
    repo.clear()
    print("🗑️ All data has been removed from the database.")


def export_csv(repo: Repository, args: argparse.Namespace) -> None:
    """
    Exports the players to a CSV file.
    Usage: database export [filename]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `filename`.
    """
    count = csv_io.export_players(repo, args.filename)
    print(f"✅ Exported {count} players to '{args.filename}'.")


def import_csv(repo: Repository, args: argparse.Namespace) -> None:
    """
    Imports players from a CSV file into the database.
    Usage: database import [filename]

    :param repo:
        Where players and matches are stored.
    :param args:
        The parsed command-line arguments: `filename`.
    """
    count, errors = csv_io.import_players(repo, args.filename)
    for name, exc in errors:
        print(f"⚠️ Could not import player {name}: {exc}")
    print(f"✅ Imported {count} players from '{args.filename}'.")


# --------------------------
# Subparser Setup Functions
# --------------------------
def setup_player_subparser(subparsers):
    """
    Adds the `player ...` commands.

    :param subparsers:
        The top-level subparsers to add the `player` command to.
    """
    player_parser = subparsers.add_parser("player", help="Manage players")
    player_subparsers = player_parser.add_subparsers(
        dest="action", required=True
    )

    # "add" command
    add_parser = player_subparsers.add_parser("add", help="Add a new player")
    add_parser.add_argument("name", type=str, help="Player's name")
    for name in ATTRIBUTE_NAMES:
        add_parser.add_argument(
            f"-{name[0]}",
            f"--{name}",
            type=int,
            required=True,
            help=f"{name.capitalize()} skill (1-10)",
        )
    add_parser.set_defaults(func=add_player)

    # "attributes" command
    attr_parser = player_subparsers.add_parser(
        "attributes", help="Show a player's attributes"
    )
    attr_parser.add_argument("name", type=str, help="Player's name")
    attr_parser.set_defaults(func=list_player_attributes)

    # "list" command
    list_parser = player_subparsers.add_parser("list", help="List all players")
    list_parser.set_defaults(func=list_players)

    # "rank" command
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

    # "remove" command
    remove_parser = player_subparsers.add_parser(
        "remove", help="Remove a player"
    )
    remove_parser.add_argument("name", type=str, help="Player's name")
    remove_parser.set_defaults(func=remove_player)

    # "reset_forms" command
    reset_parser = player_subparsers.add_parser(
        "reset_forms",
        help=f"Reset all player forms to default ({DEFAULT_FORM})",
    )
    reset_parser.set_defaults(func=reset_forms)

    # "update" command
    update_parser = player_subparsers.add_parser(
        "update", help="Update a player's skill or form"
    )
    update_parser.add_argument("name", type=str, help="Player's name")
    update_parser.add_argument(
        "attribute", type=str, help="Attribute to update, or 'form'"
    )
    update_parser.add_argument("value", type=int, help="New value")
    update_parser.set_defaults(func=update_player)


def _add_match_option(parser: argparse.ArgumentParser) -> None:
    """
    Adds the optional `--match N` argument.

    :param parser:
        The command's parser.
    """
    parser.add_argument(
        "--match",
        type=int,
        default=None,
        help="Match ID (default: the latest match)",
    )


def setup_team_subparser(subparsers):
    """
    Adds the `teams ...` commands.

    :param subparsers:
        The top-level subparsers to add the `teams` command to.
    """
    team_parser = subparsers.add_parser("teams", help="Manage teams & matches")
    team_subparsers = team_parser.add_subparsers(dest="action", required=True)

    # "attributes" command
    attr_parser = team_subparsers.add_parser(
        "attributes", help="Get team attribute ratings"
    )
    attr_parser.add_argument("team", choices=TEAM_KEYS, help="Select team")
    _add_match_option(attr_parser)
    attr_parser.set_defaults(func=get_team_attributes)

    # "cancel" command
    cancel_parser = team_subparsers.add_parser(
        "cancel", help="Cancel a match that hasn't been played"
    )
    _add_match_option(cancel_parser)
    cancel_parser.set_defaults(func=cancel_match)

    # "create" command
    create_parser = team_subparsers.add_parser(
        "create", help="Create balanced teams"
    )
    create_parser.add_argument(
        "players", nargs="+", type=str, help="List of player names"
    )
    create_parser.set_defaults(func=create_teams)

    # "rating" command
    rating_parser = team_subparsers.add_parser(
        "rating", help="Get overall team rating"
    )
    rating_parser.add_argument("team", choices=TEAM_KEYS, help="Select team")
    _add_match_option(rating_parser)
    rating_parser.set_defaults(func=get_team_rating)

    # "result" command
    result_parser = team_subparsers.add_parser(
        "result", help="Record match result"
    )
    result_parser.add_argument(
        "winning_team", choices=TEAM_KEYS, help="Winning team"
    )
    _add_match_option(result_parser)
    result_parser.set_defaults(func=record_match_result)


def setup_database_subparser(subparsers):
    """
    Adds the `database ...` commands.

    :param subparsers:
        The top-level subparsers to add the `database` command to.
    """
    database_parser = subparsers.add_parser("database", help="Manage database")
    database_subparsers = database_parser.add_subparsers(
        dest="action", required=True
    )

    # "clear" command
    clear_parser = database_subparsers.add_parser(
        "clear", help="Clear all database data"
    )
    clear_parser.set_defaults(func=clear_database)

    # "export" command
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

    # "import" command
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
def main(argv: Optional[List[str]] = None) -> int:
    """
    Parses the arguments, runs the command and returns the exit code.

    :param argv:
        The arguments to parse, or None to use the command line.

    :return:
        0 on success, 1 if the command failed because of user input.
    """
    parser = argparse.ArgumentParser(description="Football Team Manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_player_subparser(subparsers)
    setup_team_subparser(subparsers)
    setup_database_subparser(subparsers)

    args = parser.parse_args(argv)
    repo = SqliteRepository(os.getenv("FOOTBALL_DB", DEFAULT_DB_PATH))
    try:
        args.func(repo, args)
    except USER_ERRORS as exc:
        print(f"❌ {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
