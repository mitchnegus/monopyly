"""Module describing logical authorization actions (to be used in routes)."""


def get_username_and_password(form):
    """
    Get username and password from a form.

    Get the username and password from the given form. Username should
    be case insensitive.
    """
    username = form["username"].lower()
    password = form["password"]
    return username, password
