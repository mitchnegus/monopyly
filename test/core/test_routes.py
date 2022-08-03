import pytest


def test_index(client, auth):
    pass
    # Test that index shows minimal information without login
    #response = client.get('/')
    #assert False
    # Test index page after login
    #assert False

def test_about(client):
    response = client.get('/about')
    assert b'Pass go and collect $200' in response.data

