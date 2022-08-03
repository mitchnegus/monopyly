"""
Tools for dealing with the authorization blueprint.
"""
import functools

from flask import g, redirect, session, url_for
from sqlalchemy import select

from ..database import db
from ..database.models import User
from .blueprint import bp


def get_username_and_password(form):
    """Get username and password from a form."""
    username = form['username']
    password = form['password']
    return username, password


@bp.before_app_request
def load_logged_in_user():
    # Match the user's information with the session
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        query = select(User).where(User.id == user_id)
        with db.session as db_session:
            g.user = db_session.scalar(query)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
