"""Tests for the actions performed by the credit blueprint."""
import datetime
from unittest.mock import MagicMock

from monopyly.credit.actions import *
from test.helpers import TestGrouper


class TestGroupingActions(TestGrouper):

    def test_get_card_statement_groupings(self, client_context):
        cards = [MagicMock(), MagicMock()]
        cards[0].__getitem__.return_value = 3
        cards[1].__getitem__.return_value = 4
        statement_id_groupings = {3: [3, 4, 5], 4: [6, 7]}
        groupings = get_card_statement_groupings(cards)
        self.compare_groupings(groupings, statement_id_groupings)
        # Ensure that date fields are returned as `datetime.date` objects
        for card, statements in groupings.items():
            for statement in statements:
                for key in statement.keys():
                    if key.endswith('_date') and statement[key] is not None:
                        assert isinstance(statement[key], datetime.date)

