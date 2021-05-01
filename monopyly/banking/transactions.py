"""
Tools for interacting with the bank transactions in the database.
"""
import datetime
from sqlite3 import IntegrityError

from ..db import DATABASE_FIELDS
from ..utils import (
    DatabaseHandler, fill_places, filter_items, filter_dates, check_sort_order,
    select_fields
)


class BankTransactionHandler(DatabaseHandler):
    """
    A database handler for accessing bank transactions.

    Parameters
    ––––––––––
    db : sqlite3.Connection
        A connection to the database for interfacing.
    user_id : int
        The ID of the user who is the subject of database access. If not
        given, the handler defaults to using the logged-in user.
    check_user : bool
        A flag indicating whether the handler should check that the
        provided user ID matches the logged-in user.

    Attributes
    ––––––––––
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    _table = 'bank_transactions'

    def get_entries(self, account_ids=None, active=False, sort_order='DESC',
                    fields=DATABASE_FIELDS[_table]):
        """
        Get bank transactions from the database.

        Query the database to select bank transaction information.
        Transaction information includes details specific to the
        transaction and the corresponding bank account. Transactions can
        be filtered by bank, and query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ––––––––––
        account_ids : tuple of int, optional
            A sequence of bank account IDs with which to filter
            transactions (if `None`, all bank account IDs will be
            shown).
        active : bool, optional
            A flag indicating whether only transactions for active
            accounts will be returned. The default is `False` (all
            transactions are returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'bank_transactions', 'bank_accounts', or 'banks' tables,

        Returns
        –––––––
        transactions : list of sqlite3.Row
            A list of bank account transactions matching the criteria.
        """
        check_sort_order(sort_order)
        account_filter = filter_items(account_ids, 'account_id', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM bank_transactions_view AS t "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {account_filter} {active_filter} "
                  " GROUP BY t.id "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(account_ids))
        transactions = self._query_entries(query, placeholders)
        return transactions

    def get_entry(self, transaction_id, fields=None):
        """
        Get a transaction from the database given its ID.

        Accesses a set of fields for a given transaction. By default,
        all fields for a transaction and the corresponding bank account
        are returned.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of the transaction to be found.
        fields : tuple of str, optional
            The fields (in either the transactions or banks tables) to
            be returned.

        Returns
        –––––––
        transaction : sqlite3.Row
            The transaction information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM bank_transactions AS t "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE t.id = ? AND user_id = ?")
        placeholders = (transaction_id, self.user_id)
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self._query_entry(query, placeholders, abort_msg)
        return transaction
