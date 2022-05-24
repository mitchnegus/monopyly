"""Tests for the credit module managing credit card statements."""
from datetime import date
from sqlite3 import IntegrityError
from unittest.mock import patch

import pytest
from werkzeug.exceptions import NotFound

from monopyly.credit.cards import CreditStatementHandler
from ..helpers import TestHandler


@pytest.fixture
def statement_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        statement_db = CreditStatementHandler()
        yield statement_db


class TestCreditStatementHandler(TestHandler):

    # References only include entries accessible to the authorized login
    #   - ordered by date (most recent first)
    reference = {
        'keys': ('id', 'card_id', 'issue_date', 'due_date'),
        'rows': [(5, 3, date(2020, 6, 15), date(2020, 7, 5)),
                 (7, 4, date(2020, 6, 15), date(2020, 7, 3)),
                 (4, 3, date(2020, 5, 15), date(2020, 6, 5)),
                 (6, 4, date(2020, 5, 15), date(2020, 6, 3)),
                 (3, 3, date(2020, 4, 15), date(2020, 5, 5)),
                 (2, 2, date(2020, 3, 15), date(2020, 4, 5))]
    }
    view_reference = {
        'keys': ('id', 'card_id', 'issue_date', 'due_date', 'balance',
                 'payment_date'),
        'rows': [(5, 3, date(2020, 6, 15), date(2020, 7, 5), 26.87+6599.00,
                  None),
                 (7, 4, date(2020, 6, 15), date(2020, 7, 3), 1477+253.99,
                  None),
                 (4, 3, date(2020, 5, 15), date(2020, 6, 5), 6599.00,
                  None),
                 (6, 4, date(2020, 5, 15), date(2020, 6, 3), 1477.00,
                  None),
                 (3, 3, date(2020, 4, 15), date(2020, 5, 5), 108.21+1.00,
                  date(2020, 5, 4)),
                 (2, 2, date(2020, 3, 15), date(2020, 4, 5), 1.00,
                  date(2020, 5, 4))]
    }

    def test_initialization(self, statement_db):
        assert statement_db.table == 'credit_statements'
        assert statement_db.user_id == 3

    @pytest.mark.parametrize(
        'card_ids, bank_ids, active, sort_order, fields, '
        'reference_entries',
        [[None, None, False, 'DESC', None,
          view_reference['rows']],
         [None, None, False, 'DESC', ('card_id', 'issue_date'),
          [row[:3] for row in view_reference['rows']]],
         [(3,), None, False, 'DESC', ('card_id', 'issue_date'),
          [view_reference['rows'][0][:3],
           view_reference['rows'][2][:3],
           view_reference['rows'][4][:3]]],
         [None, (2,), False, 'DESC', ('card_id', 'issue_date'),
          [view_reference['rows'][0][:3],
           view_reference['rows'][2][:3],
           view_reference['rows'][4][:3],
           view_reference['rows'][5][:3]]],
         [None, None, True, 'DESC', ('card_id', 'issue_date'),
          [row[:3] for row in view_reference['rows'][:5]]],
         [None, None, False, 'ASC', ('card_id', 'issue_date'),
          [view_reference['rows'][5][:3],
           view_reference['rows'][4][:3],
           view_reference['rows'][2][:3],
           view_reference['rows'][3][:3],
           view_reference['rows'][0][:3],
           view_reference['rows'][1][:3]]]]
    )
    def test_get_entries(self, statement_db, card_ids, bank_ids, active,
                         sort_order, fields, reference_entries):
        statements = statement_db.get_entries(card_ids, bank_ids, active,
                                              sort_order, fields)
        if fields:
            self.assertMatchEntries(reference_entries, statements, order=True)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, statements)

    @pytest.mark.parametrize(
        'statement_id, fields, reference_entry',
        [[3, None,
          view_reference['rows'][4]],
         [4, None,
          view_reference['rows'][2]],
         [3, ('card_id', 'issue_date'),
          view_reference['rows'][4][:3]]]
    )
    def test_get_entry(self, statement_db, statement_id, fields, reference_entry):
        statement = statement_db.get_entry(statement_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, statement)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, statement)

    @pytest.mark.parametrize(
        'statement_id, exception',
        [[1, NotFound],  # Not the logged in user
         [8, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, statement_db, statement_id, exception):
        with pytest.raises(exception):
            statement_db.get_entry(statement_id)

    @pytest.mark.parametrize(
        'card, issue_date, fields, reference_entry',
        [[{'id': 3}, date(2020, 5, 15), None,
          view_reference['rows'][2]],
         [{'id': 4}, date(2020, 5, 15), None,
          view_reference['rows'][3]],
         [{'id': 3}, None, None,
          view_reference['rows'][0]],
         [{'id': 3}, date(2020, 5, 15), ('card_id', 'issue_date'),
          view_reference['rows'][2][:3]]]
    )
    def test_find_statement(self, statement_db, card, issue_date, fields,
                            reference_entry):
        statement = statement_db.find_statement(card, issue_date, fields)
        if fields:
            self.assertMatchEntry(reference_entry, statement)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, statement)

    @pytest.mark.parametrize(
        'card, issue_date, fields, reference_entry',
        [({'id': 3}, date(2020, 12, 1), None,
          None)]
    )
    def test_find_statement_none_exist(self, statement_db, card, issue_date,
                                       fields, reference_entry):
        statement = statement_db.find_statement(card, issue_date, fields)
        assert statement is None

    @pytest.mark.parametrize(
        'card, transaction_date, creation, statement_found, statement_added',
        [[{'id': 1, 'statement_issue_day': 1}, date(2020, 5, 5), False,
          True, False],
         [{'id': 3, 'statement_issue_day': 10}, date(2020, 6, 10), False,
          True, False],
         [{'id': 3, 'statement_issue_day': 10}, date(2020, 6, 20), False,
          False, False],  # statement does not exist (do not create)
         [{'id': 3, 'statement_issue_day': 10}, date(2020, 6, 20), True,
          False, True]]   # statement does not exist (do create)
    )
    @patch('monopyly.credit.statements.CreditStatementHandler.add_statement')
    @patch('monopyly.credit.statements.CreditStatementHandler.find_statement')
    def test_infer_statement(self, find_statement_method, add_statement_method,
                             statement_db, card, transaction_date, creation,
                             statement_found, statement_added):
        find_statement_method.return_value = statement_found
        add_statement_method.return_value = statement_added
        statement = statement_db.infer_statement(card, transaction_date,
                                                 creation)
        assert statement == (statement_found or statement_added)

    @pytest.mark.parametrize(
        'card, issue_date, due_date, expected_due_date',
        [[{'id': 3, 'statement_due_day': 5},
          date(2020, 7, 15), None, date(2020, 8, 5)],
         [{'id': 3, 'statement_due_day': 5},
          date(2020, 7, 15), date(2020, 8, 6), date(2020, 8, 6)],
         [{'id': 4, 'statement_due_day': 3},
          date(2020, 7, 15), None, date(2020, 8, 3)]]
    )
    def test_add_statement(self, app, statement_db, card, issue_date,
                           due_date, expected_due_date):
        statement = statement_db.add_statement(card, issue_date, due_date)
        assert statement['due_date'] == expected_due_date
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM credit_statements"
                f" WHERE due_date = DATE('{expected_due_date}')")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'card, issue_date, due_date, exception',
        [[{}, date(2020, 7, 15), None, KeyError],
         [{'id': 3, 'statement_due_day': 5}, None, None, AttributeError],
         [{'id': 3, 'statement_due_day': 5}, None, 'test', IntegrityError]]
    )
    def test_add_entry_invalid(self, statement_db, card, issue_date, due_date,
                               exception):
        with pytest.raises(exception):
            statement_db.add_statement(card, issue_date, due_date)

    @pytest.mark.parametrize(
        'mapping',
        [{'card_id': 2, 'issue_date': '2020-05-20', 'due_date': '2020-06-05'},
         {'card_id': 2, 'issue_date': '2020-05-20'}]
    )
    def test_update_entry(self, app, statement_db, mapping):
        statement = statement_db.update_entry(2, mapping)
        assert statement['issue_date'] == date(2020, 5, 20)
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM credit_statements"
                 " WHERE issue_date = '2020-05-20'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'statement_id, mapping, exception',
        [[1, {'card_id': 2, 'issue_date': '2020-05-20'},  # another user
          NotFound],
         [2, {'card_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [8, {'card_id': 2, 'issue_date': '2020-05-20'},  # nonexistent ID
          NotFound]]
    )
    def test_update_entry_invalid(self, statement_db, statement_id, mapping,
                                  exception):
        with pytest.raises(exception):
            statement_db.update_entry(statement_id, mapping)

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, statement_db, entry_ids):
        statement_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM credit_statements"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, statement_db):
        statement_db.delete_entries((3,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM credit_transactions"
                f" WHERE statement_id = 3")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(10,), NotFound]]  # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, statement_db, entry_ids, exception):
        with pytest.raises(exception):
            statement_db.delete_entries(entry_ids)

