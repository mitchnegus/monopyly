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

    def page_header_includes_substring(self, substring, level="h1"):
        """
        Return true if the page header includes a matching substring.

        Parameters
        ----------
        substring : str
            A substring to find in the page header.
        level : str
            The tag type to treat as the page header. The default is
            'h1'.
        """
        return bool(self.soup.find("h1", string=self.match_substring(substring)))

    def tag_count_is_equal(self, count, tag_type, **find_kwargs):
        """Return true if the count of some tag with some class is correct."""
        return len(list(self.soup.find_all(tag_type, **find_kwargs))) == count

    def tag_exists(self, tag_type, **find_kwargs):
        """Return true if a specific tag type exists with any given characteristics."""
        return bool(self.soup.find_all(tag_type, **find_kwargs))

    def anchor_exists(self, **find_kwargs):
        """Return true if a <a> exists with any given characteristics."""
        return self.tag_exists("a", **find_kwargs)

    def div_exists(self, **find_kwargs):
        """Return true if a <div> exists with any given characteristics."""
        return self.tag_exists("div", **find_kwargs)

    def span_exists(self, **find_kwargs):
        """Return true if a <span> exists with any given characteristics."""
        return self.tag_exists("span", **find_kwargs)

    def form_exists(self, **find_kwargs):
        """Return true if a <form> exists with any given characteristics."""
        return self.tag_exists("form", **find_kwargs)

    def input_exists(self, **find_kwargs):
        """Return true if an <input> exists with any given characteristics."""
        return self.tag_exists("input", **find_kwargs)

    def input_has_value(self, value, **find_kwargs):
        """Return true if an <input> exists with the given value."""
        attrs = find_kwargs.pop("attrs", {}) | {"value": value}
        return bool(self.soup.find("input", attrs=attrs, **find_kwargs))
