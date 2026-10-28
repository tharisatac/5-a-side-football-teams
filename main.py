"""
Main entry point for the Football Team Manager application.

Handles CLI commands and, in the future, other interfaces (APIs, GUI, etc.).
"""

from src.cli import main as cli_main


def main() -> int:
    """
    Routes command-line arguments to the CLI and returns its exit code.
    """
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
