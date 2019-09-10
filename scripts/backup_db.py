"""Script to backup the SQLite database."""
import os
import datetime
import sqlite3

INSTANCE_DIR = 'instance'
BACKUP_DIR = f'{INSTANCE_DIR}/db_backups'

def get_timestamp():
    """Get a timestamp for backup filenames."""
    now = datetime.datetime.now()
    date = str(now.date()).replace("-","")
    timestamp = f'{date}_{now.hour:0>2}{now.minute:0>2}{now.second:0>2}'
    return timestamp

def create_directory_if_not_existing(directory_path):
    """Create a directory if it does not already exist."""
    try:
        os.makedirs(directory_path)
    except FileExistsError:
        # The directory already exists
        pass

if __name__ == '__main__':
    create_directory_if_not_existing(BACKUP_DIR)
    # Define the database names/paths
    timestamp = get_timestamp()
    orig_db_path = f'{INSTANCE_DIR}/monopyly.sql'
    backup_db_path = f'{BACKUP_DIR}/backup_{timestamp}.sql'
    # Connect to the databases
    db = sqlite3.connect(orig_db_path)
    backup_db = sqlite3.connect(backup_db_path)
    # Backup the database
    with backup_db:
        db.backup(backup_db)
    backup_db.close()
    db.close()
