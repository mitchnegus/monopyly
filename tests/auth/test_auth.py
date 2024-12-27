"""Tests for user authentication."""

import pytest
from flask import g, session
from fuisce.testing import transaction_lifetime
from sqlalchemy import select
from werkzeug.security import check_password_hash


@transaction_lifetime
def test_registration(app, client, user_table):
    # Check that the 'register' route is successfully reached
    assert client.get("/auth/register").status_code == 200
    # Perform a test registration
    response = client.post("/auth/register", data={"username": "a", "password": "a"})
    assert "/auth/login" == response.headers["Location"]
    # Check that the registration was successful
    query = select(user_table).where(user_table.c.username == "a")
    with app.db.session as db_session:
        assert db_session.execute(query).fetchone() is not None


def test_registration_deactivated(app, client):
    app.config["REGISTRATION"] = False
    # Check that the 'register' route is successfully reached
    assert client.get("/auth/register").status_code == 200
    # Perform a test registration
    response = client.post("/auth/register", data={"username": "a", "password": "a"})
    assert b"The app is not currently accepting new registrations." in response.data


@transaction_lifetime
@pytest.mark.parametrize(
    "username, password, message",
    [
        ["", "", b"Username is required."],
        ["a", "", b"Password is required."],
        ["test", "test", b"User test is already registered."],
    ],
)
def test_register_validate_input(client, username, password, message, user_table):
    response = client.post(
        "/auth/register", data={"username": username, "password": password}
    )
    assert message in response.data


def test_login(client, auth):
    # Check that the 'login' route is successfully reached
    assert client.get("/auth/login").status_code == 200
    response = auth.login()
    assert response.headers["Location"] == "/"
    # Check that the session variables are properly set
    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user.username == "test"


@pytest.mark.parametrize(
    "username, password, message",
    [
        ["a", "test", b"That user is not yet registered."],
        ["test", "a", b"Incorrect username and password combination."],
    ],
)
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data


def test_logout(client, auth):
    auth.login()
    with client:
        auth.logout()
        assert "user_id" not in session


@transaction_lifetime
@pytest.mark.parametrize("current_password", ["MONOPYLY", "invalid"])
def test_change_password(app, client, authorization, current_password):
    # Check that the 'change_password' route is successfully reached
    assert client.get("/auth/change_password").status_code == 200
    # Perform a test password update
    new_password = "password123... jk don't be a fool"
    with client:
        response = client.post(
            "/auth/change_password",
            data={"current-password": current_password, "new-password": new_password},
            follow_redirects=True,
        )
        # Check that the password was updated correctly
        # (merging the user item since it expired after the transaction)
        password = new_password if current_password == "MONOPYLY" else "MONOPYLY"
        user = app.db.session.merge(g.user)
        assert check_password_hash(user.password, password)
