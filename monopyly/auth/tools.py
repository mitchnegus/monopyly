"""
Tools for dealing with the authorization blueprint.
"""
import functools

from flask import g, redirect, session, url_for

from monopyly.auth import auth
from monopyly.db import get_db


def get_username_and_password(form):
    """Get username and password from a form."""
    username = form['username']
    password = form['password']
    return username, password


@auth.before_app_request
def load_logged_in_user():
    # Match the user's information with the session
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        user_query = 'SELECT * FROM users WHERE id = ?'
        db = get_db()
        cursor = db.cursor()
        g.user = cursor.execute(user_query, (user_id,)).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
