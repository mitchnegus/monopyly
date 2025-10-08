"""
Routes for site authentication.
"""

from dry_foundation.database import db_transaction
from flask import (
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from ..database.models import User
from .actions import get_username_and_password, identify_user
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
        elif identify_user(username):
            error = f"User {username} is already registered."
        else:
            # Create a new user
            new_user = User(
                username=username,
                password=generate_password_hash(password),
            )
            current_app.db.session.add(new_user)
            return redirect(url_for("auth.login"))
        flash(error)
    # Display the registration page
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        # Get username and passwords from the form
        username, password = get_username_and_password(request.form)
        # Check for errors in the accessed information
        if (user := identify_user(username)) is None:
            error = "That user is not yet registered."
        elif not check_password_hash(user.password, password):
            error = "Incorrect username and password combination."
        else:
            # Set the user ID securely for a new session
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("core.index"))
        flash(error)
    # Display the login page
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    # End the session and clear the user ID
    session.clear()
    return redirect(url_for("core.index"))


@bp.route("/change_password", methods=("GET", "POST"))
@db_transaction
def change_password():
    if request.method == "POST":
        current_password = request.form["current-password"]
        new_password = request.form["new-password"]
        if check_password_hash(g.user.password, current_password):
            # Merge the user item (dissociated from the current session) for updating
            g.user = current_app.db.session.merge(g.user)
            g.user.password = generate_password_hash(new_password)
            flash("Password updated successfully.", category="success")
            return redirect(url_for("core.load_profile"))
        else:
            flash(
                "The provided value for the current password does not match the "
                "value of the current password set on this account.",
                category="error",
            )
    return render_template("auth/change_password.html")
