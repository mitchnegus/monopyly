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

    @staticmethod
    def match_substring(substring):
        """A helper method to build a substring filter for some target."""

        def _wrapper(target):
            try:
                return substring in target
            except TypeError:
                raise TypeError(
                    "The target to match a substring against must be an "
                    f"iterable, not '{type(target).__name__}'"
                )

        return _wrapper

    def assert_page_header_includes_substring(self, substring, level="h1"):
        """
        Assert that the page header includes a matching substring.

        Parameters
        ----------
        substring : str
            A substring to find in the page header.
        level : str
            The tag type to treat as the page header. The default is
            'h1'.
        """
        assert self.soup.find("h1", string=self.match_substring(substring))

    def assert_tag_count_equal(self, count, tag_type, **find_kwargs):
        """Assert that the count of some tag with some class is correct."""
        len(list(self.soup.find_all(tag_type, **find_kwargs))) == count

    def assert_div_exists(self, **find_kwargs):
        """Find a <div> with any given characteristics."""
        x = self.soup.find("div", class_="notes")
        assert self.soup.find("div", **find_kwargs)

    def assert_form_exists(self, **find_kwargs):
        """Find a <form> with any given characteristics."""
        assert self.soup.find("form", **find_kwargs)
