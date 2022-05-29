"""
Tools for building a common transaction interface.
"""
from abc import ABC, abstractmethod
from functools import wraps


class Transaction(ABC):
    """
    A transaction pulled from the database.

    Using an entry returned from a database query, this object wraps
    entry and identifies it as a transaction. In addition to that
    identification, it also provides for added functionality.

    Parameters
    ----------
    entry : sqlite3.Row
        An entry returned from a database query.
    db : DatabaseHandler
        A reference to the database handler used to retrieve the
        transaction.

    Attributes
    ----------
    db : DatabaseHandler
        A reference to the database handler used to retrieve the
        transaction.

    Notes
    -----
    This is not currently a complete wrapper, as more pass through
    methods remain to be added.
    """

    def __init__(self, entry, db):
        self._entry = entry
        self.db = db

    def __getattr__(self, name):
        return getattr(self._entry, name)

    def __getitem__(self, index):
        return self._entry[index]

    def __len__(self):
        return len(self._entry)


def get_linked_transaction(transaction):
    """
    Find a transaction that is linked to the given transaction.

    Checks all transaction databases for a transaction that matches
    the given transaction.

    Parameters
    ----------
    transaction : Transaction
        The transaction for which to find a linked transaction.

    Returns
    -------
    linked_transaction : Transaction
        A transaction that is linked to the given transaction. If no
        linked transaction is found, `None` is returned.
    """
    transaction = transaction.db.get_entry(transaction['id'],
                                           ('internal_transaction_id',))
    internal_transaction_id = transaction['internal_transaction_id']
    if not internal_transaction_id:
        return None
    # First, check if there is a matching bank transaction
    linked_transaction = _get_linked_bank_transaction(
        transaction['id'],
        internal_transaction_id
    )
    if linked_transaction:
        return linked_transaction
    # Second, check if there is a matching credit transaction
    linked_transaction = _get_linked_credit_transaction(
        transaction['id'],
        internal_transaction_id
    )
    return linked_transaction


def linked_transaction_querier(func):
    @wraps(func)
    def wrapper(transaction_id, internal_transaction_id):
        db, query = func(transaction_id, internal_transaction_id)
        placeholders = (db.user_id, transaction_id, internal_transaction_id)
        transactions = db.query_entries(query, placeholders)
        return transactions[0] if transactions else None
    return wrapper


@linked_transaction_querier
def _get_linked_bank_transaction(transaction_id, internal_transaction_id):
    from ..banking.transactions import BankTransactionHandler
    db = BankTransactionHandler()
    query = ("SELECT * "
             "  FROM bank_transactions_view AS t "
             "       INNER JOIN bank_accounts AS a "
             "          ON a.id = t.account_id "
             "       INNER JOIN bank_account_types_view AS types "
             "          ON types.id = a.account_type_id "
             "       INNER JOIN banks AS b "
             "          ON b.id = a.bank_id "
             " WHERE b.user_id =? AND t.id != ? "
             "       AND t.internal_transaction_id = ?")
    # Decorator uses returned database and query to check for transactions
    return db, query


@linked_transaction_querier
def _get_linked_credit_transaction(transaction_id, internal_transaction_id):
    from ..credit.transactions import CreditTransactionHandler
    db = CreditTransactionHandler()
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
    # Decorator uses returned database and query to check for transactions
    return db, query

