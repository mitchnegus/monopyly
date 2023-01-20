"""Tests for the credit module managing credit card statements."""
from datetime import date
from unittest.mock import patch, Mock

import pytest
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import StatementError

from monopyly.database.models import (
    CreditStatement, CreditStatementView, CreditTransaction
)
from monopyly.credit.statements import CreditStatementHandler
from ..helpers import TestHandler


@pytest.fixture
def statement_handler(client_context):
    return CreditStatementHandler


class TestCreditStatementHandler(TestHandler):

    statement2_balance = 1.00
    statement3_balance = (43.21+30.00+35.00) + statement2_balance
    statement6_balance = (1600.00-1230.00)
    statement4_balance = (99.00+6500.00-109.21) + statement3_balance
    statement7_balance = (253.99+12.34) + statement6_balance
    statement5_balance = 26.87 + statement4_balance
    # References only include entries accessible to the authorized login
    #   - ordered by issue date (most recent first)
    db_reference = [
        CreditStatementView(id=5, card_id=3, issue_date=date(2020, 6, 10),
                            due_date=date(2020, 7, 5),
                            balance=round(statement5_balance, 2),
                            payment_date=None),
        CreditStatementView(id=7, card_id=4, issue_date=date(2020, 6, 6),
                            due_date=date(2020, 6, 27),
                            balance=round(statement7_balance, 2),
                            payment_date=None),
        CreditStatementView(id=4, card_id=3, issue_date=date(2020, 5, 10),
                            due_date=date(2020, 6, 5),
                            balance=round(statement4_balance, 2),
                            payment_date=None),
        CreditStatementView(id=6, card_id=4, issue_date=date(2020, 5, 6),
                            due_date=date(2020, 5, 27),
                            balance=round(statement6_balance, 2),
                            payment_date=None),
        CreditStatementView(id=3, card_id=3, issue_date=date(2020, 4, 15),
                            due_date=date(2020, 5, 5),
                            balance=round(statement3_balance, 2),
                            payment_date=date(2020, 5, 4)),
        CreditStatementView(id=2, card_id=2, issue_date=date(2020, 3, 15),
                            due_date=date(2020, 4, 5),
                            balance=round(statement2_balance, 2),
                            payment_date=date(2020, 5, 4)),
    ]

    def test_initialization(self, statement_handler):
        assert statement_handler.model == CreditStatement
        assert statement_handler.table == "credit_statements"
        assert statement_handler.table_view == "credit_statements_view"
        assert statement_handler.user_id == 3

    def test_model_view_access(self, statement_handler):
        assert statement_handler.model == CreditStatement
        statement_handler._view_context = True
        assert statement_handler.model == CreditStatementView
        statement_handler._view_context = False

    @pytest.mark.parametrize(
        "card_ids, bank_ids, active, sort_order, reference_entries",
        [[None, None, None, "DESC",                     # defaults
          db_reference],
         [(3,), None, None, "DESC",
          [db_reference[0], db_reference[2], db_reference[4]]],
         [None, (2,), None, "DESC",
          [db_reference[0], db_reference[2], db_reference[4], db_reference[5]]],
         [None, None, False, "DESC",                    # card 2 inactive
          db_reference[5:]],
         [None, None, True, "DESC",
          db_reference[:5]],
         [None, None, None, "ASC",
          db_reference[::-1]]]
    )
    def test_get_statements(self, statement_handler, card_ids, bank_ids, active,
                            sort_order, reference_entries):
        statements = statement_handler.get_statements(
            card_ids, bank_ids, active, sort_order
        )
        self.assertEntriesMatch(statements, reference_entries, order=True)

    @pytest.mark.parametrize(
        "statement_id, reference_entry",
        [[3, db_reference[4]],
         [4, db_reference[2]]]
    )
    def test_get_entry(self, statement_handler, statement_id, reference_entry):
        statement = statement_handler.get_entry(statement_id)
        self.assertEntryMatches(statement, reference_entry)

    @pytest.mark.parametrize(
        "statement_id, exception",
        [[1, NotFound],  # Not the logged in user
         [8, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, statement_handler, statement_id, exception):
        with pytest.raises(exception):
            statement_handler.get_entry(statement_id)

    @pytest.mark.parametrize(
        "card_id, issue_date, reference_entry",
        [[3, date(2020, 5, 10), db_reference[2]],
         [4, date(2020, 5, 6), db_reference[3]],
         [3, None, db_reference[0]]]
    )
    def test_find_statement(self, statement_handler, card_id, issue_date,
                            reference_entry):
        statement = statement_handler.find_statement(card_id, issue_date)
        self.assertEntryMatches(statement, reference_entry)

    @pytest.mark.parametrize(
        "card_id, issue_date",
        [[3, date(2020, 12, 1)],
         [None, None]]
    )
    def test_find_statement_none_exist(self, statement_handler, card_id,
                                       issue_date):
        statement = statement_handler.find_statement(card_id, issue_date)
        assert statement is None

    @pytest.mark.parametrize(
        "card_id, statement_issue_day, statement_due_day, transaction_date, "
        "creation, inferred_statement_id",
        [[1, 1, 20, date(2020, 5, 5), False, None],    # should fail, invalid user
         [3, 10, 5, date(2020, 5, 1), False, 4],
         [3, 10, 5, date(2020, 6, 5), False, 5],
         [3, 10, 5, date(2020, 6, 20), True, 8],      # create new statement
         [3, 10, 5, date(2020, 6, 20), False, None]]  # do not create new statement
    )
    def test_infer_statement(self, statement_handler, card_id,
                             statement_issue_day, statement_due_day,
                             transaction_date, creation,
                             inferred_statement_id):
        # Mock the inputs required for inference
        mock_card = Mock()
        mock_card.id = card_id
        mock_card.account.statement_issue_day = statement_issue_day
        mock_card.account.statement_due_day = statement_due_day
        # Test that the inference action produces the expected behavior
        statement = statement_handler.infer_statement(
            mock_card, transaction_date, creation=creation
        )
        if inferred_statement_id is None:
            assert statement is None
        else:
            assert statement.id == inferred_statement_id

    @pytest.mark.parametrize(
        "card_id, statement_due_day, issue_date, due_date, expected_due_date",
        [[3, 5, date(2020, 7, 15), None, date(2020, 8, 5)],
         [3, 5, date(2020, 7, 15), date(2020, 8, 6), date(2020, 8, 6)],
         [4, 3, date(2020, 7, 15), None, date(2020, 8, 3)]]
    )
    def test_add_statement(self, statement_handler, card_id, statement_due_day,
                           issue_date, due_date, expected_due_date):
        mock_card = Mock()
        mock_card.id = card_id
        mock_card.account.statement_due_day = statement_due_day
        statement = statement_handler.add_statement(
            mock_card, issue_date, due_date
        )
        # Check that the entry object was properly created
        assert statement.due_date == expected_due_date
        # Check that the entry was added to the database
        self.assertNumberOfMatches(
            1,
            CreditStatement.id,
            CreditStatement.due_date == expected_due_date
        )

    @pytest.mark.parametrize(
        "card_id, statement_due_day, issue_date, due_date, exception",
        [[None, None, date(2020, 7, 15), None, AttributeError],
         [3, 5, None, None, AttributeError],
         [3, 5, None, "test", StatementError]]
    )
    def test_add_entry_invalid(self, statement_handler, card_id,
                               statement_due_day, issue_date, due_date,
                               exception):
        if card_id is None and statement_due_day is None:
            mock_card = None
        else:
            mock_card = Mock()
            mock_card.id = card_id
            mock_card.account.statement_due_day = statement_due_day
        with pytest.raises(exception):
            statement_handler.add_statement(mock_card, issue_date, due_date)

    def test_add_entry_invalid_user(self, statement_handler):
        mapping = {
            "card_id": 1,
            "issue_date": date(2020, 8, 1),
            "due_date": date(2020, 8, 20),
        }
        # Ensure that 'mr.monopyly' cannot add an entry for the test user
        self.assert_invalid_user_entry_add_fails(
            statement_handler, mapping, invalid_user_id=1, invalid_matches=1
        )

    @pytest.mark.parametrize(
        "mapping",
        [{"card_id": 2, "issue_date": date(2020, 5, 20),
          "due_date": date(2020, 6, 5)},
         {"card_id": 2, "issue_date": date(2020, 5, 20)}]
    )
    def test_update_entry(self, statement_handler, mapping):
        statement = statement_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert statement.issue_date == date(2020, 5, 20)
        # Check that the entry was updated in the database
        self.assertNumberOfMatches(
            1,
            CreditStatement.id,
            CreditStatement.issue_date == date(2020, 5, 20)
        )

    @pytest.mark.parametrize(
        "statement_id, mapping, exception",
        [[1, {"card_id": 2, "issue_date": date(2020, 5, 20)},
          NotFound],                                        # wrong user
         [2, {"card_id": 2, "invalid_field": "Test"},
          ValueError],                                      # invalid field
         [8, {"card_id": 2, "issue_date": date(2020, 5, 20)},
          NotFound]]                                        # nonexistent ID
    )
    def test_update_entry_invalid(self, statement_handler, statement_id,
                                  mapping, exception):
        with pytest.raises(exception):
            statement_handler.update_entry(statement_id, **mapping)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, statement_handler, entry_id):
        self.assert_entry_deletion_succeeds(statement_handler, entry_id)
        # Check that the cascading entries were deleted
        self.assertNumberOfMatches(
            0, CreditTransaction.id, CreditTransaction.statement_id == entry_id
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [[1, NotFound],   # should not be able to delete other user entries
         [10, NotFound]]  # should not be able to delete nonexistent entries
    )
    def test_delete_entry_invalid(self, statement_handler, entry_id, exception):
        with pytest.raises(exception):
            statement_handler.delete_entry(entry_id)

