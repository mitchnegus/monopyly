"""Tests for user authentication."""
import pytest
from flask import g, session

from monopyly.db import get_db


def test_registration(client, app):
    # Check that the 'register' route is successfully reached
    assert client.get('/auth/register').status_code == 200
    # Perform a test registration
    response = client.post(
        '/auth/register',
        data={'username': 'a', 'password': 'a'}
    )
    assert 'http://localhost/auth/login' == response.headers['Location']
    # Check that the registration was successful
    with app.app_context():
        query = "SELECT * FROM users WHERE username = 'a'"
        assert get_db().execute(query).fetchone() is not None


@pytest.mark.parametrize(
    ('username', 'password', 'message'),
    [('', '', b'Username is required.'),
     ('a', '', b'Password is required.'),
     ('test', 'test', b'User test is already registered.')]
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        '/auth/register',
        data={'username': username, 'password': password}
    )
    assert message in response.data


def test_login(client, auth):
    # Check that the 'login' route is successfully reached
    assert client.get('/auth/login').status_code == 200
    response = auth.login()
    assert response.headers['Location'] == 'http://localhost/'
    # Check that the session variables are properly set
    with client:
        client.get('/')
        assert session['user_id'] == 1
        assert g.user['username'] == 'test'


@pytest.mark.parametrize(
    ('username', 'password', 'message'),
    [('a', 'test', b'That user is not yet registered.'),
     ('test', 'a', b'Incorrect username and password combination.')]
)
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data
