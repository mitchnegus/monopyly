"""Module describing logical authorization actions (to be used in routes)."""

def get_username_and_password(form):
    """Get username and password from a form."""
    username = form['username']
    password = form['password']
    return username, password
