"""Tests for the banking module managing bank accounts."""
from unittest.mock import patch

import pytest
from werkzeug.exceptions import Forbidden, NotFound

from monopyly.banking.accounts import *
from ..helpers import TestHandler


@pytest.fixture
def account_type_db(client_context):
    account_type_db = BankAccountTypeHandler()
    yield account_type_db


class TestBankAccountTypeHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'user_id', 'type_name', 'type_abbreviation'),
        'rows': [(1, 0, 'Savings', None),
                 (2, 0, 'Checking', None),
                 (3, 0, 'Certificate of Deposit', 'CD'),
                 (5, 3, 'Trustworthy Player', 'Trust'),
                 (6, 3, 'Cooperative Enjoyment Depository', 'Mutual FunD')]
    }
    view_reference = {
        'keys': ('id', 'user_id', 'type_name', 'type_common_name'),
        'rows': [(1, 0, 'Savings', 'Savings'),
                 (2, 0, 'Checking', 'Checking'),
                 (3, 0, 'Certificate of Deposit', 'CD'),
                 (5, 3, 'Trustworthy Player', 'Trust'),
                 (6, 3, 'Cooperative Enjoyment Depository', 'Mutual FunD')]
    }

    def test_initialization(self, account_type_db):
        assert account_type_db.table == 'bank_account_types'
        assert account_type_db.table_view == 'bank_account_types_view'
        assert account_type_db.user_id == 3

    @pytest.mark.parametrize(
        'fields, reference_entries',
        [[None,
          view_reference['rows']],
         [('type_name', 'type_common_name'),  # use the fields from the view
          [(row[0], row[2], row[3]) for row in view_reference['rows']]]]
    )
    def test_get_entries(self, account_type_db, fields, reference_entries):
        account_types = account_type_db.get_entries(fields)
        self.assertMatchEntries(reference_entries, account_types)

    @pytest.mark.parametrize(
        'bank_id, reference_entries',
        [[2, view_reference['rows'][:2]],
         [3, view_reference['rows'][2:3]]]
    )
    def test_get_types_for_bank(self, account_type_db, bank_id,
                                reference_entries):
        account_types = account_type_db.get_types_for_bank(bank_id)
        self.assertMatchEntries(reference_entries, account_types)

    @pytest.mark.parametrize(
        'account_type_id, fields, reference_entry',
        [[2, None,
          view_reference['rows'][1]],
         [3, None,
          view_reference['rows'][2]],
         [2, ('type_name',),
          (view_reference['rows'][1][0], view_reference['rows'][1][2])],
         [3, ('type_name', 'type_common_name'),  # use the fields from the view
          (view_reference['rows'][2][0],
           view_reference['rows'][2][2],
           view_reference['rows'][2][3])]]
    )
    def test_get_entry(self, account_type_db, account_type_id, fields,
                       reference_entry):
        account_type = account_type_db.get_entry(account_type_id, fields)
        self.assertMatchEntry(reference_entry, account_type)

    @pytest.mark.parametrize(
        'account_type_id, exception',
        [[4, NotFound],  # Not the logged in user
         [7, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_type_db, account_type_id,
                               exception):
        with pytest.raises(exception):
            account_type_db.get_entry(account_type_id)

    @pytest.mark.parametrize(
        'type_name, type_abbreviation, fields, reference_entry',
        [['Checking', None, None,
          reference['rows'][1]],
         ['Certificate of Deposit', None, None,
          reference['rows'][2]],
         [None, 'CD', None,
          reference['rows'][2]],
         [None, 'Trust', None,
          reference['rows'][3]],
         ['Certificate of Deposit', 'CD', None,
          reference['rows'][2]],
         [None, 'CD', ('type_name', 'type_abbreviation'),
          (reference['rows'][2][0],
           reference['rows'][2][2],
           reference['rows'][2][3])]]
    )
    def test_find_account_type(self, account_type_db, type_name,
                               type_abbreviation, fields, reference_entry):
        account_type = account_type_db.find_account_type(type_name,
                                                         type_abbreviation,
                                                         fields)
        self.assertMatchEntry(reference_entry, account_type)

    @pytest.mark.parametrize(
        'type_name, type_abbreviation, fields',
        [('Certificate of Deposit', 'CoD', None),
         (None, None, None)]
    )
    def test_find_account_type_none_exist(self, account_type_db, type_name,
                                          type_abbreviation, fields):
        account_type = account_type_db.find_account_type(type_name,
                                                         type_abbreviation,
                                                         fields)
        assert account_type is None

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'type_name': 'Well Stocked Hand',
          'type_abbreviation': None},
         {'user_id': 3, 'type_name': 'Well Stocked Hand',
          'type_abbreviation': 'Paper'}]
    )
    def test_add_entry(self, app, account_type_db, mapping):
        account_type = account_type_db.add_entry(mapping)
        assert account_type['type_name'] == 'Well Stocked Hand'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_account_types"
                 " WHERE type_name LIKE '%Hand'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'invalid_field': 'Test', 'type_abbreviation': None},
         {'user_id': 3, 'type_name': 'Test'}]
    )
    def test_add_entry_invalid(self, account_type_db, mapping):
        with pytest.raises(ValueError):
            account_type_db.add_entry(mapping)

    def test_add_entry_invalid_user(self, app, account_type_db):
        query = ("SELECT COUNT(id) FROM bank_account_types"
                 " WHERE user_id = 1")
        self.assertQueryEqualsCount(app, query, 1)
        with pytest.raises(NotFound):
            mapping = {
                'user_id': 1,
                'type_name': 'Well Stocked Hand',
                'type_abbreviation': 'Paper',
            }
            account_type_db.add_entry(mapping)
        # Check that the transaction was not added to a different account
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'user_id': 3, 'type_name': 'Trustworthy Friend',
          'type_abbreviation': 'Trust'},
         {'type_name': 'Trustworthy Friend'}]
    )
    def test_update_entry(self, app, account_type_db, mapping):
        account_type = account_type_db.update_entry(5, mapping)
        assert account_type['type_name'] == 'Trustworthy Friend'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_account_types"
                 " WHERE type_name LIKE '%Friend'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'account_type_id, mapping, exception',
        [[2, {'user_id': 3, 'type_name': 'Test'}, Forbidden], # another user
         [5, {'user_id': 3, 'invalid_field': 'Test'}, ValueError],
         [7, {'user_id': 3, 'type_name': 'Test'}, NotFound]]  # nonexistent ID
    )
    def test_update_entry_invalid(self, account_type_db, account_type_id,
                                  mapping, exception):
        with pytest.raises(exception):
            account_type_db.update_entry(account_type_id, mapping)

    def test_update_entry_value(self, account_type_db):
        account_type = account_type_db.update_entry_value(5, 'type_name',
                                                          'Trustworthy Friend')
        assert account_type['type_name'] == 'Trustworthy Friend'

    @pytest.mark.parametrize(
        'entry_ids', [(5,), (5, 6)]
    )
    def test_delete_entries(self, app, account_type_db, entry_ids):
        account_type_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_account_types"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), Forbidden],  # should not be able to delete common entries
         [(4,), NotFound],   # should not be able to delete other user entries
         [(7,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, account_type_db, entry_ids,
                                    exception):
        with pytest.raises(exception):
            account_type_db.delete_entries(entry_ids)


@pytest.fixture
def account_db(app, client, auth):
    auth.login('mr.monopyly', 'MONOPYLY')
    with client:
        # Context variables (e.g. `g`) may be accessed only after response
        client.get('/')
        account_db = BankAccountHandler()
        yield account_db


class TestBankAccountHandler(TestHandler):

    # References only include entries accessible to the authorized login
    reference = {
        'keys': ('id', 'bank_id', 'account_type_id', 'last_four_digits',
                 'active'),
        'rows': [(2, 2, 1, '5556', 1),
                 (3, 2, 2, '5556', 0),
                 (4, 3, 3, '5557', 1)]
    }
    view_reference = {
        'keys': ('id', 'bank_id', 'account_type_id', 'last_four_digits',
                 'active', 'balance'),
        'rows': [(2, 2, 1, '5556', 1, 443.90),
                 (3, 2, 2, '5556', 0, -409.21),
                 (4, 3, 3, '5557', 1, 200.00)]
    }

    def test_initialization(self, account_db):
        assert account_db.table == 'bank_accounts'
        assert account_db.table_view == 'bank_accounts_view'
        assert account_db.user_id == 3

    @pytest.mark.parametrize(
        'bank_ids, account_type_ids, fields, reference_entries',
        [[None, None, None,
          view_reference['rows']],
         [None, None, ('bank_id', 'account_type_id', 'last_four_digits'),
          [row[:4] for row in view_reference['rows']]],
         [(2,), None, ('bank_id', 'account_type_id', 'last_four_digits'),
          [row[:4] for row in view_reference['rows'][:2]]],
         [None, (2, 3), ('bank_id', 'account_type_id', 'last_four_digits'),
          [row[:4] for row in view_reference['rows'][1:]]],
         [None, None, ('last_four_digits', 'balance'), # use view fields
          [(row[0], row[3], row[5]) for row in view_reference['rows']]]]
    )
    def test_get_entries(self, account_db, bank_ids, account_type_ids, fields,
                         reference_entries):
        accounts = account_db.get_entries(bank_ids, account_type_ids, fields)
        if fields:
            self.assertMatchEntries(reference_entries, accounts)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntries(reference_entries, accounts)

    @pytest.mark.parametrize(
        'account_id, fields, reference_entry',
        [[2, None,
          view_reference['rows'][0]],
         [3, None,
          view_reference['rows'][1]],
         [2, ('last_four_digits',),
          (view_reference['rows'][0][0], view_reference['rows'][0][3])],
         [3, ('last_four_digits', 'balance'),  # use fields from the view
          (view_reference['rows'][1][0],
           view_reference['rows'][1][3],
           view_reference['rows'][1][5])]]
    )
    def test_get_entry(self, account_db, account_id, fields, reference_entry):
        account = account_db.get_entry(account_id, fields)
        if fields:
            self.assertMatchEntry(reference_entry, account)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, account)

    @pytest.mark.parametrize(
        'account_id, exception',
        [[1, NotFound],  # Not the logged in user
         [5, NotFound]]  # Not in the database
    )
    def test_get_entry_invalid(self, account_db, account_id, exception):
        with pytest.raises(exception):
            account_db.get_entry(account_id)

    @pytest.mark.parametrize(
        'bank_id, expected_balance',
        [[2, (443.90 - 409.21)],
         [3, 200.00]]
    )
    def test_get_bank_balance(self, account_db, bank_id, expected_balance):
        balance = account_db.get_bank_balance(bank_id)
        assert balance == expected_balance

    @pytest.mark.parametrize(
        'bank_id, exception',
        [[1, NotFound],  # Not the logged in user
         [4, NotFound]]  # Not in the database
    )
    def test_get_bank_balance_invalid(self, account_db, bank_id, exception):
        with pytest.raises(exception):
            balance = account_db.get_bank_balance(bank_id)

    @pytest.mark.parametrize(
        'bank_name, last_four_digits, account_type_name, fields, '
        'reference_entry',
        [['Jail', '5556', 'Savings', None,
          view_reference['rows'][0]],
         ['Jail', '5556', 'Checking', None,
          view_reference['rows'][1]],
         ['TheBank', None, 'Certificate of Deposit', None,
          view_reference['rows'][2]],
         [None, '5557', 'Certificate of Deposit', None,
          view_reference['rows'][2]],
         ['TheBank', None, 'Certificate of Deposit', ('bank_id', 'balance'),
          (view_reference['rows'][2][0],
           view_reference['rows'][2][1],
           view_reference['rows'][2][5])]]
    )
    def test_find_account(self, account_db, bank_name, last_four_digits,
                          account_type_name, fields, reference_entry):
        account = account_db.find_account(bank_name, last_four_digits,
                                          account_type_name, fields)
        if fields:
            self.assertMatchEntry(reference_entry, account)
        else:
            # Leaving fields unspecified acquires all fields from many tables
            self.assertContainEntry(reference_entry, account)

    @pytest.mark.parametrize(
        'bank_name, last_four_digits, account_type_name, fields, '
        'reference_entry',
        [('Jail', '6666', None, None,
          None),
         (None, None, None, None,
          None)]
    )
    def test_find_account_none_exist(self, account_db, bank_name,
                                     last_four_digits, account_type_name,
                                     fields, reference_entry):
        account = account_db.find_account(bank_name, last_four_digits,
                                          account_type_name, fields)
        assert account is None

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'account_type_id': 2, 'last_four_digits': '6666',
          'active': 1},
         {'bank_id': 3, 'account_type_id': 5, 'last_four_digits': '6666',
          'active': 0}]
    )
    def test_add_entry(self, app, account_db, mapping):
        account = account_db.add_entry(mapping)
        assert account['last_four_digits'] == '6666'
        # Check that the entry was added
        query = ("SELECT COUNT(id) FROM bank_accounts"
                 " WHERE last_four_digits = '6666'")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 2, 'invalid_field': 'Test', 'last_four_digits': 6000,
          'active': 1},
         {'bank_id': 3, 'account_type_id': 5, 'last_four_digits': 6666}]
    )
    def test_add_entry_invalid(self, account_db, mapping):
        with pytest.raises(ValueError):
            account_db.add_entry(mapping)

    def test_add_entry_invalid_user(self, app, account_db):
        query = ("SELECT COUNT(id) FROM bank_accounts"
                 " WHERE bank_id = 1")
        self.assertQueryEqualsCount(app, query, 1)
        with pytest.raises(NotFound):
            mapping = {
                'bank_id': 1,
                'account_type_id': 5,
                'last_four_digits': '6666',
                'active': 1,
            }
            account_db.add_entry(mapping)
        # Check that the transaction was not added to a different account
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'mapping',
        [{'bank_id': 3, 'account_type_id': 1, 'last_four_digits': '6666',
          'active': 1},
         {'bank_id': 3, 'last_four_digits': '6666'}]
    )
    def test_update_entry(self, app, account_db, mapping):
        account = account_db.update_entry(2, mapping)
        assert account['last_four_digits'] == '6666'
        # Check that the entry was updated
        query = ("SELECT COUNT(id) FROM bank_accounts"
                 " WHERE last_four_digits = 6666")
        self.assertQueryEqualsCount(app, query, 1)

    @pytest.mark.parametrize(
        'account_id, mapping, exception',
        [[1, {'bank_id': 2, 'last_four_digits': '6666'},  # another user
          NotFound],
         [2, {'bank_id': 2, 'invalid_field': 'Test'},
          ValueError],
         [5, {'bank_id': 2, 'last_four_digits': '6666'},  # nonexistent ID
          NotFound]]
    )
    def test_update_entry_invalid(self, account_db, account_id, mapping,
                                  exception):
        with pytest.raises(exception):
            account_db.update_entry(account_id, mapping)

    def test_update_entry_value(self, account_db):
        account = account_db.update_entry_value(2, 'last_four_digits', '6666')
        assert account['last_four_digits'] == '6666'

    @pytest.mark.parametrize(
        'entry_ids', [(2,), (2, 3)]
    )
    def test_delete_entries(self, app, account_db, entry_ids):
        account_db.delete_entries(entry_ids)
        # Check that the entries were deleted
        for entry_id in entry_ids:
            query = ("SELECT COUNT(id) FROM bank_accounts"
                    f" WHERE id = {entry_id}")
            self.assertQueryEqualsCount(app, query, 0)

    def test_delete_cascading_entries(self, app, account_db):
        account_db.delete_entries((3,))
        # Check that the cascading entries were deleted
        query = ("SELECT COUNT(id) FROM bank_transactions"
                f" WHERE account_id = 3")
        self.assertQueryEqualsCount(app, query, 0)

    @pytest.mark.parametrize(
        'entry_ids, exception',
        [[(1,), NotFound],   # should not be able to delete other user entries
         [(5,), NotFound]]   # should not be able to delete nonexistent entries
    )
    def test_delete_entries_invalid(self, account_db, entry_ids, exception):
        with pytest.raises(exception):
            account_db.delete_entries(entry_ids)


class TestSaveFormFunctions:

    @patch('monopyly.banking.accounts.BankAccountHandler')
    @patch('monopyly.banking.forms.BankAccountForm')
    def test_save_new_transaction(self, mock_form, mock_handler_type):
        # Mock the return values and data
        mock_method = mock_handler_type.return_value.add_entry
        mock_account = {'id': 0, 'bank_id': 0}
        mock_method.return_value = mock_account
        mock_form.account_data = {'key': 'test account data'}
        # Call the function and check for proper call signatures
        account = save_account(mock_form)
        mock_method.assert_called_once_with(mock_form.account_data)
        assert account == mock_account

