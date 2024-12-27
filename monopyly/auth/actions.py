"""Module describing logical authorization actions (to be used in routes)."""

from flask import current_app
from sqlalchemy import select

from ..database.models import User


def get_username_and_password(form):
    """
    Get username and password from a form.

    Get the username and password from the given form. Username should
    be case insensitive.
    """
    username = form["username"].lower()
    password = form["password"]
    return username, password


def identify_user(username):
    """Identify the user in the database based on the username."""
    user_query = select(User).where(User.username == username)
    user = current_app.db.session.scalar(user_query)
    return user
