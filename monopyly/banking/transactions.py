"""
Tools for interacting with the bank transactions in the database.
"""
from ..core.internal_transactions import add_internal_transaction
from ..common.form_utils import execute_on_form_validation
from ..common.transactions import Transaction
from ..db import DATABASE_FIELDS
from ..db.handler import DatabaseHandler


class BankTransaction(Transaction):
    """A bank transaction."""
    subtype = 'bank'


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
    table = 'bank_transactions'
    table_view = 'bank_transactions_view'
    _entry_type = BankTransaction

    def get_entries(self, account_ids=None, active=False, sort_order='DESC',
                    fields=DATABASE_FIELDS[table]):
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
        self._queries.validate_sort_order(sort_order)
        account_filter = self._queries.filter_items(account_ids, 'account_id',
                                                    'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {self._queries.select_fields(fields, 't.id')} "
                  "  FROM bank_transactions_view AS t "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE b.user_id = ? "
                 f"       {account_filter} {active_filter} "
                  " GROUP BY t.id "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *self._queries.fill_places(account_ids))
        transactions = self.query_entries(query, placeholders)
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
        query = (f"SELECT {self._queries.select_fields(fields, 't.id')} "
                  "  FROM bank_transactions_view AS t "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE b.user_id = ? AND t.id = ?")
        placeholders = (self.user_id, transaction_id)
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self.query_entry(query, placeholders, abort_msg)
        return transaction

    def add_entry(self, mapping):
        """
        Add a transaction to the database.

        Uses a mapping produced by a `BankTransactionForm` to add a new
        transaction into the database. The mapping includes information
        for the transaction, along with information for all
        subtransactions.

        Parameters
        ––––––––––
        mapping : dict
            A mapping between database fields and the value to be
            entered into that field for the transaction. The mapping
            also contains subtransaction information (including tags).

        Returns
        –––––––
        transaction : sqlite3.Row
            The saved transaction.
        subtransaction : list of sqlite3.Row
            A list of subtransactions belonging to the saved transaction.
        """
        subtransaction_db = BankSubtransactionHandler()
        # Override the default method to account for subtransactions
        subtransactions_data = mapping.pop('subtransactions')
        transaction = super().add_entry(mapping)
        subtransactions = self._add_subtransactions(transaction['id'],
                                                    subtransactions_data)
        # Refresh the transaction information
        transaction = self.get_entry(transaction['id'])
        return transaction, subtransactions

    def update_entry(self, entry_id, mapping):
        """Update a transaction in the database."""
        subtransaction_db = BankSubtransactionHandler()
        # Automatically populate the internal transaction ID field
        transaction = self.get_entry(entry_id)
        field = 'internal_transaction_id'
        mapping[field] = transaction[field]
        # Override the default method to account for subtransactions
        subtransactions = subtransaction_db.get_entries((entry_id,))
        if 'subtransactions' in mapping:
            subtransactions_data = mapping.pop('subtransactions')
            # Replace subtransactions when updating
            subtransaction_db.delete_entries(
                [subtransaction['id'] for subtransaction in subtransactions]
            )
            subtransactions = self._add_subtransactions(entry_id,
                                                        subtransactions_data)
        transaction = super().update_entry(entry_id, mapping)
        return transaction, subtransactions

    def _add_subtransactions(self, transaction_id, subtransactions_data):
        """Add subtransactions to the database for the data given."""
        subtransaction_db = BankSubtransactionHandler()
        # Assemble mappings to add subtransactions
        subtransactions = []
        for subtransaction_data in subtransactions_data:
            # Complete the mapping and add the subtransaction to the database
            sub_mapping = {'transaction_id': transaction_id,
                           **subtransaction_data}
            subtransaction = subtransaction_db.add_entry(sub_mapping)
            subtransactions.append(subtransaction)
        return subtransactions

    def _get_entry_user_id(self, entry_id):
        # Get the user ID for an entry (this override eliminates ambiguity)
        return self.get_entry(entry_id, fields=('b.user_id',))['user_id']


class BankSubtransactionHandler(DatabaseHandler):
    """
    A database handler for accessing bank subtransactions.

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
    table = 'bank_subtransactions'

    def get_entries(self, transaction_ids=None, fields=None):
        """
        Get all subtransactions for a bank transaction.

        Accesses a set of fields for subtransactions belonging to a set
        of transactions. By default, all fields for the subtransactions
        are returned.

        Parameters
        ––––––––––
        transaction_ids : tuple of int, optional
            The IDs of the transactions for which to retrieve
            subtransactions.
        fields : tuple of str, optional
            The fields (in either the transactions, subtransactions,
            or accounts tables) to be returned. By default, all fields
            are returned.

        Returns
        –––––––
        subtransactions : list of sqlite3.Row
            A list of bank subtransactions that are associated with the
            given transaction.
        """
        transaction_filter = self._queries.filter_items(transaction_ids,
                                                        'transaction_id',
                                                        'AND')
        query = (f"SELECT {self._queries.select_fields(fields, 's_t.id')} "
                  "  FROM bank_subtransactions AS s_t "
                  "       INNER JOIN bank_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                 f" WHERE b.user_id = ? {transaction_filter}")
        placeholders = (self.user_id,
                        *self._queries.fill_places(transaction_ids))
        subtransactions = self.query_entries(query, placeholders)
        return subtransactions

    def get_entry(self, subtransaction_id, fields=None):
        """
        Get a subtransaction from the database given its ID.

        Accesses a set of fields for a given subtransaction. By default,
        all fields for a subtransaction and the corresponding account
        are returned.

        Parameters
        ––––––––––
        subtransaction_id : int
            The ID of the subtransaction to be found.
        fields : tuple of str, optional
            The fields (in either the subtransactions, transactions,
            statements, cards, or accounts tables) to be returned.

        Returns
        –––––––
        subtransaction : sqlite3.Row
            The subtransaction information from the database.
        """
        query = (f"SELECT {self._queries.select_fields(fields, 't.id')} "
                  "  FROM bank_subtransactions AS s_t "
                  "       INNER JOIN bank_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN bank_accounts AS a "
                  "          ON a.id = t.account_id "
                  "       INNER JOIN bank_account_types_view AS types "
                  "          ON types.id = a.account_type_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE b.user_id = ? AND s_t.id = ?")
        placeholders = (self.user_id, subtransaction_id)
        abort_msg = (f'Subtransaction ID {subtransaction_id} does not exist '
                      'for the user.')
        subtransaction = self.query_entry(query, placeholders, abort_msg)
        return subtransaction

    def _get_entry_user_id(self, entry_id):
        # Get the user ID for a given entry
        return self.get_entry(entry_id, fields=('b.user_id',))['user_id']


@execute_on_form_validation
def save_transaction(form, transaction_id=None):
    """
    Save a banking transaction.

    Saves a transaction in the database. If a transaction ID is given,
    then the transaction is updated with the form information. Otherwise
    the form information is added as a new entry.

    Parameters
    ----------
    form : BankTransactionForm
        The form being used to provide the data being saved.
    transaction_id : int
        The ID of the transaction to be saved. If provided, the
        named transaction will be updated in the database. Otherwise, if
        the transaction ID is `None`, a new transaction will be added.

    Returns
    -------
    transaction : Transaction
        The saved transaction.
    subtransactions : list of sqlite3.Row
        The subtransactions of the saved transaction.
    """
    db = BankTransactionHandler()
    transaction_data = form.transaction_data
    transfer_data = form.transfer_data
    if transaction_id:
        # Update the database with the updated transaction
        transaction, subtransactions = db.update_entry(transaction_id,
                                                       transaction_data)
        # The transfer is not updated; update it independently
    else:
        # Insert the new transaction into the database
        if transfer_data:
            transfer, subtransactions = record_new_transfer(transfer_data)
            internal_id_field = 'internal_transaction_id'
            transaction_data[internal_id_field] = transfer[internal_id_field]
        transaction, subtransactions = db.add_entry(transaction_data)
    return transaction, subtransactions


def record_new_transfer(transfer_data):
    """Record a new transfer given the data for populating the database."""
    db = BankTransactionHandler()
    # Create a new internal transaction ID to assign to the transfer
    internal_transaction_id = add_internal_transaction()
    # Recreate the data dictionary since the mapping must be properly ordered
    transfer_transaction_data = {
        'internal_transaction_id': internal_transaction_id,
        **transfer_data,
    }
    # Add the transfer to the database
    transfer, subtransactions = db.add_entry(transfer_transaction_data)
    return transfer, subtransactions

