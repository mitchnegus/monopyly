"""Helper objects to improve modularity of tests."""
import functools
import unittest

import pytest
from bs4 import BeautifulSoup

helper = unittest.TestCase()


class TestRoutes:
    blueprint_prefix = None

    @property
    def client(self):
        return self._client

    @pytest.fixture(autouse=True)
    def _get_client(self, client):
        # Use the client fixture in route tests
        self._client = client

    def route_loader(method):
        # Load the route accounting for the blueprint
        @functools.wraps(method)
        def wrapper(self, route, *args, **kwargs):
            if self.blueprint_prefix is not None:
                route = f"/{self.blueprint_prefix}{route}"
            method(self, route, *args, **kwargs)
            # Save the response as HTML
            self.html = self.response.data.decode("utf-8")
            self.soup = BeautifulSoup(self.html, "html.parser")

        return wrapper

    @route_loader
    def get_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'GET')."""
        self.response = self.client.get(route, *args, **kwargs)

    @route_loader
    def post_route(self, route, *args, **kwargs):
        """Load the HTML returned by accessing the route (via 'POST')."""
        self.response = self.client.post(route, *args, **kwargs)
