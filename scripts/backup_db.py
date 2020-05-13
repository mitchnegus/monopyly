#!/usr/bin/env python3
"""Script to backup the SQLite database."""
import os
import datetime
import sqlite3

# Set the application specific system variables
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
INSTANCE_DIR = os.path.join(BASE_DIR, 'var/monopyly-instance')
BACKUP_DIR = os.path.join(INSTANCE_DIR, 'db_backups')


def get_timestamp():
    """Get a timestamp for backup filenames."""
    now = datetime.datetime.now()
    date = str(now.date()).replace("-","")
    timestamp = f'{date}_{now.hour:0>2}{now.minute:0>2}{now.second:0>2}'
    return timestamp


def create_directory(directory_path):
    """Create a directory if it does not already exist."""
    try:
        os.makedirs(directory_path)
    except FileExistsError:
        # The directory already exists
        pass


def backup(verbose=False):
    """Creates a backup of the database."""
    timestamp = get_timestamp()
    create_directory(BACKUP_DIR)
    # Define the database names/paths
    orig_db_path = os.path.join(INSTANCE_DIR, 'monopyly.sql')
    backup_db_path = os.path.join(BACKUP_DIR, f'backup_{timestamp}.sql')
    # Connect to the databases
    db = sqlite3.connect(orig_db_path)
    backup_db = sqlite3.connect(backup_db_path)
    # Backup the database
    with backup_db:
        db.backup(backup_db)
    # Close the connections
    backup_db.close()
    db.close()
    if verbose:
        print(f'Backup complete ({timestamp})')


if __name__ == '__main__':
    backup(verbose=True)
