"""
Tools for interacting with the credit transactions in the database.
"""
import datetime
from sqlite3 import IntegrityError

from ..utils import (
    DatabaseHandler, fill_places, filter_items, filter_dates, check_sort_order
)
from .constants import TRANSACTION_FIELDS, TAG_FIELDS
from .tools import select_fields


class TransactionHandler(DatabaseHandler):
    """
    A database handler for accessing credit transactions.

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
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_transactions'
    table_fields = TRANSACTION_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, card_ids=None, statement_ids=None, active=False,
                    sort_order='DESC', fields=TRANSACTION_FIELDS):
        """
        Get credit card transactions from the database.

        Query the database to select credit card transaction information.
        Transaction information includes details specific to the
        transaction, the transaction's statement, and the credit card
        used to make the transaction. Transactions can be filtered by
        statement or the credit card used. Query results can be ordered
        by either ascending or descending transaction date.

        Parameters
        ––––––––––
        card_ids : tuple of int, optional
            A sequence of card IDs with which to filter transactions (if
            `None`, all card IDs will be shown).
        statement_ids : tuple of str, optional
            A sequence of statement IDs with which to filter
            transactions (if `None`, all statement IDs will be shown).
        active : bool, optional
            A flag indicating whether only transactions for active cards
            will be returned. The default is `False` (all transactions
            are returned).
        sort_order : {'ASC', 'DESC'}
            An indicator of whether the transactions should be ordered
            in ascending (oldest at top) or descending (newest at top)
            order.
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_transactions', credit_statements',
            'credit_cards', or 'credit_accounts' tables.

        Returns
        –––––––
        transactions : list of sqlite3.Row
            A list of credit card transactions matching the criteria.
        """
        check_sort_order(sort_order)
        card_filter = filter_items(card_ids, 'card_id', 'AND')
        statement_filter = filter_items(statement_ids, 'statement_id', 'AND')
        active_filter = "AND active = 1" if active else ""
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {statement_filter} {active_filter} "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(card_ids),
                        *fill_places(statement_ids))
        transactions = self._query_entries(query, placeholders)
        return transactions

    def get_entry(self, transaction_id, fields=None):
        """
        Get a transaction from the database given its transaction ID.

        Accesses a set of fields for a given transaction. By default,
        all fields for a transaction, the corresponding statement,
        issuing credit card and account are returned.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of the transaction to be found.
        fields : tuple of str, optional
            The fields (in either the transactions, statements, cards,
            or accounts tables) to be returned.

        Returns
        –––––––
        transaction : sqlite3.Row
            The transaction information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  " WHERE t.id = ? AND user_id = ?")
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self._query_entry(transaction_id, query, abort_msg)
        return transaction

    def add_transaction(self, statement_id, transaction_date, vendor, amount,
                        notes):
        """Add a transaction to the database."""
        transaction_data = {'statement_id': statement_id,
                            'transaction_date': transaction_date,
                            'vendor': vendor,
                            'amount': amount,
                            'notes': notes}
        transaction = self.add_entry(transaction_data)
        return transaction


class TagHandler(DatabaseHandler):
    """
    A database handler for managing credit transaction tags.

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
    table_name : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table_name = 'credit_tags'
    table_fields = TAG_FIELDS

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, tag_names=None, transaction_ids=None,
                    fields=TAG_FIELDS):
        """
        Get credit card transaction tags from the database.

        Query the database to select credit transaction tag fields. Tags
        can be filtered by tag name or transaction. All fields for a tag
        are shown by default.

        Parameters
        ––––––––––
        tag_names : tuple of str, optional
            A sequence of names of tags to be selected (if `None`, all
            tag names will be selected).
        transaction_ids : tuple of int, optional
            A sequence of transaction IDs for which tags will be
            selected (if `None`, all transaction tags will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_tags' table.

        Returns
        –––––––
        tags : list of sqlite3.Row
            A list of credit card transaction tags matching the criteria.
        """
        name_filter = filter_items(tag_names, 'tag_name', 'AND')
        transaction_filter = filter_items(transaction_ids,
                                          'transaction_id',
                                          'AND')
        query = (f"SELECT {select_fields(fields, 'DISTINCT t.id')} "
                  "  FROM credit_tags AS t "
                  "       LEFT OUTER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = t.id "
                 f" WHERE user_id = ? {name_filter} {transaction_filter}")
        placeholders = (self.user_id, *fill_places(tag_names),
                        *fill_places(transaction_ids))
        tags = self._query_entries(query, placeholders)
        return tags

    def get_entry(self, tag_id, fields=None):
        """
        Get a credit transaction tag from the database given its tag ID.

        Accesses a set of fields for a given tag. By default, all fields
        for a tag are returned.

        Parameters
        ––––––––––
        tag_id : int
            The ID of the tag to be found.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        tag : sqlite3.Row
            The tag information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_tags AS t "
                  " WHERE t.id = ? AND user_id = ?")
        abort_msg = (f'Tag ID {tag_id} does not exist for the user.')
        tag = self._query_entry(tag_id, query, abort_msg)
        return tag

    def get_subtags(self, tag_id, fields=None):
        """
        Get subcategories of a credit transaction tag given its tag ID.

        Accesses a set of fields for children of a given tag. By
        default, all fields for a tag are returned.

        Parameters
        ––––––––––
        tag_id : int, None
            The ID of the tag to be found.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        subtags : list of sqlite3.Row
            A list of credit card transaction tags that are
            subcategories of the given tag.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_tags AS t "
                  " WHERE parent_id IS ? AND user_id = ?")
        subtags = self._query_entries(query, (tag_id, self.user_id))
        return subtags

    def find_tag(self, tag_name, fields=None):
        """
        Find a tag using uniquely identifying characteristics.

        Queries the database to find a transaction tag based on the
        provided criteria (the tag's name).

        Parameters
        ––––––––––
        tag_name : str
            The name of the tag to be found.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        tag : sqlite3.Row
            The tag entry matching the given criteria. If no matching
            tag is found, returns `None`.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_tags AS t "
                 f" WHERE user_id = ? AND tag_name = ?")
        placeholders = (self.user_id, tag_name)
        tag = self.cursor.execute(query, placeholders).fetchone()
        return tag

    def get_heirarchy(self, parent_id=None):
        """
        Get the heirarchy of tags as a dictionary.

        Recurses through the tags database to return a dictionary
        representation of the tags. The dictionary has keys representing
        each tag, and each key is paired to a similar dictionary of
        subtags for that tag. The top level of the dictionary consists
        only of tags without parent tags.

        Parameters
        ––––––––––
        parent_id : int, None
            The ID of the parent tag to use as the starting point when
            recursing through the tree. If the parent ID is `None`, the
            recursion begins at the highest level of tags.

        Returns
        –––––––
        heirarchy : dict
            The dictionary representing the user's tags. Keys are a
            tuple of tag IDs and tag names.
        """
        heirarchy = {}
        for tag in self.get_subtags(parent_id):
            tag_key = (tag['id'], tag['tag_name'])
            heirarchy[tag_key] = self.get_heirarchy(tag['id'])
        return heirarchy

    def update_tags(self, transaction_id, tag_names):
        """
        Update the tags for a transaction in the database.

        Given a transaction and a list of tag names, each tag is applied
        to the transaction. Then, each existing tag that is not in the
        list of tag names is disassociated with the transaction. Tag
        names that do not already have database entries are created.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of a transaction database entry that will be assigned
            the tags.
        tag_names : tuple of str
            Tag names to be assigned to the given transactions.
        """
        # Get all of the current tags for the transaction
        current_tags = self.get_entries(transaction_ids=(transaction_id,))
        current_tag_names = [tag['tag_name'] for tag in current_tags]
        # Determine tags to be added and tags to be removed
        new_tag_names = [name for name in tag_names
                         if name not in current_tag_names]
        old_tag_names = [name for name in current_tag_names
                         if name not in tag_names]
        for tag_name in new_tag_names:
            # Get the matching tag
            tag = self.find_tag(tag_name, fields=('tag_name',))
            # Create the tag if it does not already exist in the database
            if not tag:
                tag_data = {'parent_id': None,
                            'user_id': self.user_id,
                            'tag_name': tag_name}
                tag = self.add_entry(tag_data)
            # Link the tag to the transaction
            self.link(tag['id'], transaction_id)
        for tag_name in old_tag_names:
            # Get the matching tag
            tag = self.find_tag(tag_name, fields=())
            # Unlink the tag from the transaction
            self.unlink(tag['id'], transaction_id)

    def link(self, tag_id, transaction_id):
        """Add a tag to the given transaction."""
        # Add the transaction-tag link if the two are not already associated
        try:
            self.cursor.execute(
                "INSERT INTO credit_tag_links (transaction_id, tag_id) "
               f"     VALUES (?, ?)",
                (transaction_id, tag_id)
            )
            self.db.commit()
        except IntegrityError:
            # The tag link already exists
            pass

    def unlink(self, tag_id, transaction_id):
        """Remove a tag from the given transaction."""
        # Delete the transaction-tag link
        self.cursor.execute(
            "DELETE "
            "  FROM credit_tag_links "
            " WHERE transaction_id = ? AND tag_id = ? ",
            (transaction_id, tag_id)
        )
        self.db.commit()

    def get_totals(self, tag_ids=None, statement_ids=None, start_date=None,
                   end_date=None, group_statements=False):
        """
        Get the totals for tags given the criteria.

        Find the sum of all transactions for tags matching provided
        criteria. Only tags where a transaction was registered that
        matches the criteria will be returned.

        Parameters
        ––––––––––
        tag_ids : tuple of int
            A set of tag IDs for which to get tag totals. If left as
            `None`, totals for any matching tags will be found.
        statement_ids : tuple of int
            A set of statement IDs for which to get tag totals. If left
            as `None`, tag totals will be found for all statements in
            the date range.
        start_date : datetime.date
            The first date to consider in the time interval over which
            to get tag totals. If left as `None`, the date range will
            extend back to the first transaction made.
        end_date : datetime.date
            The last date to consider in the time interval over which to
            get tag totals. If left as `None`, the date range will
            extend up to the last transaction made.
        group_statements : bool
            A flag indicating whether totals should be grouped by
            statement.

        Returns
        –––––––
        tag_totals : dict
            The list of totals for all tags matching the criteria.
        """
        tag_filter = filter_items(tag_ids, 'tag_id', 'AND')
        statement_filter = filter_items(statement_ids, 'statement_id', 'AND')
        date_filter = filter_dates(start_date, end_date, 'transaction_date',
                                   'AND')
        fields = ['SUM(amount) total', 'tag_name']
        groups = ['tags.id']
        if group_statements:
            fields.append('t.statement_id')
            groups.append('t.statement_id')
        query = (f"SELECT {', '.join(fields)} "
                  "  FROM credit_tags AS tags "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = l.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  " WHERE tags.user_id = ? "
                 f"       {tag_filter} {statement_filter} {date_filter} "
                 f" GROUP BY {', '.join(groups)}")
        placeholders = (self.user_id, *fill_places(statement_ids))
        tag_totals = self._query_entries(query, placeholders)
        return tag_totals

    def get_statement_average_totals(self, tag_ids=None, statement_ids=None):
        """
        Get the average tag totals per statement given the criteria.

        Find the average total (per statement) of all transactions for
        tags matching provided criteria. Only tags where a transaction
        was registered that matches the criteria will be returned.

        Parameters
        ––––––––––
        tag_ids : tuple of int
            A set of tag IDs for which to get tag average totals. If
            left as `None`, average totals for any matching tags will be
            found.
        statement_ids : tuple of int
            A set of statement IDs for which to get tag average totals.
            If left as `None`, tag average totals will be found for all
            statements in the date range.

        Returns
        –––––––
        tag_average_totals : list of sqlite3.Row
            The list of average totals for all tags matching the
            criteria.
        """
        statement_filter = filter_items(statement_ids, 'id', 'AND')
        subquery = ("SELECT COUNT(s.id) "
                    "  FROM credit_statements AS s "
                    "       INNER JOIN credit_cards AS c "
                    "             ON c.id = s.card_id "
                    "       INNER JOIN credit_accounts AS a "
                    "             ON a.id = c.account_id "
                   f" WHERE a.user_id = ? {statement_filter}")
        tag_filter = filter_items(tag_ids, 'tag_id', 'AND')
        statement_filter = filter_items(statement_ids, 'statement_id', 'AND')
        query = (f"SELECT SUM(amount) / ({subquery}) average_total, tag_name "
                 "  FROM credit_tags AS tags "
                 "       INNER JOIN credit_tag_links AS l "
                 "          ON l.tag_id = tags.id "
                 "       INNER JOIN credit_transactions AS t "
                 "          ON t.id = l.transaction_id "
                 "       INNER JOIN credit_statements AS s "
                 "          ON s.id = t.statement_id "
                f" WHERE tags.user_id = ? {tag_filter} {statement_filter} "
                f" GROUP BY tags.id")
        placeholders = (self.user_id, *fill_places(statement_ids),
                        self.user_id, *fill_places(statement_ids))
        tag_average_totals = self._query_entries(query, placeholders)
        return tag_average_totals
