#!/usr/bin/env python3
"""A script (entry point) to backup the SQLite database."""
import argparse
import datetime
import sqlite3
from pathlib import Path

# Set the application specific system variables
SCRIPT_DIR = Path(__file__)
BASE_DIR = SCRIPT_DIR.parents[1]
INSTANCE_DIR = BASE_DIR / "var" / "monopyly-instance"
BACKUP_DIR = INSTANCE_DIR / "db_backups"


def main():
    args = parse_arguments()
    timestamp = get_timestamp()
    backup(timestamp, verbose=args.verbose)
    if verbose:
        print(f"Backup complete ({timestamp})")


def get_timestamp():
    """Get a timestamp for backup filenames."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return timestamp


def backup(timestamp):
    """Creates a backup of the database."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # Define the database names/paths
    orig_db_path = INSTANCE_DIR / "monopyly.sqlite"
    backup_db_path = BACKUP_DIR / f"backup_{timestamp}.sqlite"
    # Connect to the databases
    db = sqlite3.connect(orig_db_path)
    backup_db = sqlite3.connect(backup_db_path)
    # Backup the database
    with backup_db:
        db.backup(backup_db)
    # Close the connections
    backup_db.close()
    db.close()


def parse_arguments():
    """Parse arguments from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
