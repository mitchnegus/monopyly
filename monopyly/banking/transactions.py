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
    _table_view = 'bank_transactions_view'

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
                  "       INNER JOIN bank_account_types AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE b.user_id = ? "
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
                  "  FROM bank_transactions_view AS t "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN bank_account_types AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE b.user_id = ? AND t.id = ?")
        placeholders = (self.user_id, transaction_id)
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self._query_entry(query, placeholders, abort_msg)
        return transaction

    def update_entry(self, entry_id, mapping):
        """Update a transaction in the database."""
        # Automatically populate the internal transaction ID field
        transaction = self.get_entry(entry_id)
        field = 'internal_transaction_id'
        mapping[field] = transaction[field]
        transaction = super().update_entry(entry_id, mapping)
        return transaction

    def get_matching_transactions(self, transaction_id):
        """
        Find all internal transactions that match this transaction.

        Checks all transaction databases for transactions that match the
        given transaction.

        Parameters
        ----------
        transaction_id : integer
            The ID for the transaction that should be matched.

        Returns
        -------
        matching_transactions : dict
            A dictionary of transaction types and the corresponding
            transactions that match the given transaction. The
            transactions may be rows in either the `bank_transactions` or
            `credit_transactions` databases, depending on the dictionary
            key (either 'bank' or 'credit' respectively). If no matching
            transactions are found, `None` is returned.
        """
        transaction = self.get_entry(transaction_id,
                                     ('internal_transaction_id'))
        internal_transaction_id = transaction['internal_transaction_id']
        if not internal_transaction_id:
            return None
        matching_transactions = {'bank': None, 'credit': None}
        # Get matching bank transactions
        query = ("SELECT * "
                 "  FROM bank_transactions_view AS t "
                 "       INNER JOIN bank_accounts AS a "
                 "          ON a.id = t.account_id "
                 "       INNER JOIN banks AS b "
                 "          ON b.id = a.bank_id "
                 " WHERE b.user_id =? AND t.id != ? "
                 "       AND t.internal_transaction_id = ?")
        placeholders = (self.user_id, transaction_id, internal_transaction_id)
        bank_transactions = self.query_entry(query, placeholders)
        if bank_transactions:
            matching_transactions['bank'] = bank_transactions
        # Get matching credit transactions
        query = ("SELECT * "
                 "  FROM credit_transactions_view AS t "
                 "       INNER JOIN credit_statements AS s "
                 "          ON s.id = t.statement_id "
                 "       INNER JOIN credit_cards AS c "
                 "          ON c.id = s.card_id "
                 "       INNER JOIN credit_accounts AS a "
                 "          ON a.id = c.account_id "
                 "       INNER JOIN banks AS b "
                 "          ON b.id = a.bank_id "
                 " WHERE b.user_id =? AND t.id != ? "
                 "       AND t.internal_transaction_id = ?")
        placeholders = (self.user_id, transaction_id, internal_transaction_id)
        credit_transactions = self.query_entry(query, placeholders)
        credit_transactions = self.query_entry(query, placeholders)
        if credit_transactions:
            matching_transactions['credit'] = credit_transactions
        return matching_transactions

