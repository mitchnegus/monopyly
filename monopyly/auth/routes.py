"""
Routes for site authentication.
"""
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from fuisce.database import db_transaction
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from ..database.models import User
from .actions import get_username_and_password
from .blueprint import bp


@bp.route("/register", methods=("GET", "POST"))
@db_transaction
def register():
    if request.method == "POST":
        # Get username and passwords from the form
        username, password = get_username_and_password(request.form)
        # Check for errors in the accessed information
        if not current_app.config["REGISTRATION"]:
            error = "The app is not currently accepting new registrations."
        elif not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        else:
            # Get user information from the database
            user_query = select(User).where(User.username == username)
            user = current_app.db.session.scalar(user_query)
            if user:
                error = f"User {username} is already registered."
            else:
                error = None
        # Add the username and hashed password to the database
        if not error:
            new_user = User(
                username=username,
                password=generate_password_hash(password),
            )
            current_app.db.session.add(new_user)
            return redirect(url_for("auth.login"))
        else:
            flash(error)
    # Display the registration page
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        # Get username and passwords from the form
        username, password = get_username_and_password(request.form)
        # Get user information from the database
        user_query = select(User).where(User.username == username)
        user = current_app.db.session.scalar(user_query)
        # Check for errors in the accessed information
        if user is None:
            error = "That user is not yet registered."
        elif not check_password_hash(user.password, password):
            error = "Incorrect username and password combination."
        else:
            error = None
        # Set the user ID securely for a new session
        if not error:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("core.index"))
        else:
            flash(error)
    # Display the login page
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    # End the session and clear the user ID
    session.clear()
    return redirect(url_for("core.index"))
