"""
Tools for connecting to and working with the SQLite database.
"""
import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


# Define database fields ('id' field is ommitted in all cases where it exists)
DATABASE_FIELDS = {
    'users': (
        'username',
        'password',
    ),
    'credit_accounts': (
        'user_id',
        'bank',
        'statement_issue_day',
        'statement_due_day',
    ),
    'credit_cards': (
        'account_id',
        'last_four_digits',
        'active',
    ),
    'credit_statements': (
        'card_id',
        'issue_date',
        'due_date',
    ),
    'credit_statments_view': (
        'card_id',
        'issue_date',
        'due_date',
        'balance',
        'payment_date',
    ),
    'credit_transactions': (
        'statement_id',
        'transaction_date',
        'vendor',
    ),
    'credit_transactions_view': (
        'statement_id',
        'transaction_date',
        'vendor',
        'total',
        'notes',
    ),
    'credit_subtransactions': (
        'transaction_id',
        'subtotal',
        'note',
    ),
    'credit_tags': (
        'parent_id',
        'user_id',
        'tag_name',
    ),
    'credit_tag_links': (
        'subtransaction_id',
        'tag_id',
    ),
}


def get_db():
    """Connect to the database (and don't reconnect if already connected)."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
        )
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close the database if it is open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Execute the SQL schema to clear existing data and create new tables."""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo(f"Initialized the database ({current_app.config['DATABASE']})")


def init_app(app):
    """Registers the database initialization command with an app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
