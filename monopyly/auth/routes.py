"""
Routes for site authentication.
"""
from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from monopyly.db import get_db
from monopyly.auth.tools import get_username_and_password
from monopyly.auth import auth


@auth.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        # Get username and passwords from the form
        username, password = get_username_and_password(request.form)
        # Get user information from the database
        db = get_db()
        cursor = db.cursor()
        id_query = 'SELECT id FROM users WHERE username = ?'
        # Check for errors in the accessed information
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif cursor.execute(id_query, (username,)).fetchone() is not None:
            error = f'User {username} is already registered.'
        else:
            error = None
        # Add the username and hashed password to the database
        if not error:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            return redirect(url_for('auth.login'))
        else:
            flash(error)
    # Display the registration page
    return render_template('auth/register.html')


@auth.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        # Get username and passwords from the form
        username, password = get_username_and_password(request.form)
        # Get user information from the database
        db = get_db()
        cursor = db.cursor()
        user_query = 'SELECT * FROM users WHERE username = ?'
        user = cursor.execute(user_query, (username,)).fetchone()
        # Check for errors in the accessed information
        if user is None:
            error = 'That user is not yet registered.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect username and password combination.'
        else:
            error = None
        # Set the user ID securely for a new session
        if not error:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('core.index'))
        else:
            flash(error)
    # Display the login page
    return render_template('auth/login.html')

@auth.route('/logout')
def logout():
    # End the session and clear the user ID;k
    session.clear()
    return redirect(url_for('core.index'))
