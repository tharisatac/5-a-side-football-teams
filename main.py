"""
Main entry point for the Football Team Manager application.

Handles CLI commands and, in the future, other interfaces (APIs, GUI, etc.).
"""

from src.cli import main as cli_main


def main():
    """
    Routes command-line arguments to the CLI.
    """
    cli_main()


if __name__ == "__main__":
    main()
