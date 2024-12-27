"""
Tools for dealing with the authorization blueprint.
"""

import functools

from flask import current_app, g, redirect, session, url_for
from sqlalchemy import select

from ..database.models import User
from .blueprint import bp


@bp.before_app_request
def load_logged_in_user():
    # Match the user's information with the session
    if (user_id := session.get("user_id")) is None:
        g.user = None
    else:
        query = select(User).where(User.id == user_id)
        with current_app.db.session as db_session:
            g.user = db_session.scalar(query)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
