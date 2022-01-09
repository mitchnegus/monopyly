"""
Tools for interacting with the credit transactions in the database.
"""
import datetime
from sqlite3 import IntegrityError

from ..db import DATABASE_FIELDS
from ..utils import (
    DatabaseHandler, fill_places, filter_items, filter_dates, check_sort_order,
    select_fields
)


class CreditTransactionHandler(DatabaseHandler):
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
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    _table = 'credit_transactions'
    _table_view = 'credit_transactions_view'

    def get_entries(self, card_ids=None, statement_ids=None, active=False,
                    sort_order='DESC', fields=DATABASE_FIELDS[_table_view]):
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
            'credit_cards', 'credit_accounts', or 'banks' tables.

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
                  "  FROM credit_transactions_view AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? "
                 f"       {card_filter} {statement_filter} {active_filter} "
                  " GROUP BY t.id "
                 f" ORDER BY transaction_date {sort_order}")
        placeholders = (self.user_id, *fill_places(card_ids),
                        *fill_places(statement_ids))
        transactions = self._query_entries(query, placeholders)
        return transactions

    def get_entry(self, transaction_id, fields=None):
        """
        Get a transaction from the database given its ID.

        Accesses a set of fields for a given transaction. By default,
        all fields for a transaction, the corresponding statement,
        issuing credit card and account are returned.

        Parameters
        ––––––––––
        transaction_id : int
            The ID of the transaction to be found.
        fields : tuple of str, optional
            The fields (in either the transactions, statements, cards,
            accounts, or banks tables) to be returned.

        Returns
        –––––––
        transaction : sqlite3.Row
            The transaction information from the database.
        """
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_transactions_view AS t "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? AND t.id = ?")
        placeholders = (self.user_id, transaction_id)
        abort_msg = (f'Transaction ID {transaction_id} does not exist for the '
                      'user.')
        transaction = self._query_entry(query, placeholders, abort_msg)
        return transaction

    def add_entry(self, mapping):
        """
        Add a transaction to the database.

        Uses a mapping produced by a `CreditTransactionForm` to add a
        new transaction into the database. The mapping includes
        information for the transaction, along with information for all
        subtransactions (including tags associated with each
        subtransaction).

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
        subtransactions : list of sqlite3.Row
            A list of subtransactions belonging to the saved transaction.
        """
        subtransaction_db = CreditSubtransactionHandler()
        # Override the default method to account for subtransactions
        subtransactions_data = mapping.pop('subtransactions')
        transaction = super().add_entry(mapping)
        subtransactions = self._add_subtransactions(transaction['id'],
                                                    subtransactions_data)
        # Refresh the transaction information
        transaction = self.get_entry(transaction['id'])
        return transaction, subtransactions

    def update_entry(self, entry_id, mapping):
        """Update a transaction (and its subtransactions) in the database."""
        subtransaction_db = CreditSubtransactionHandler()
        # Automatically populate the internal transaction ID field
        transaction = self.get_entry(entry_id)
        field = 'internal_transaction_id'
        mapping[field] = transaction[field]
        # Override the default method to account for subtransactions
        subtransactions_data = mapping.pop('subtransactions')
        transaction = super().update_entry(entry_id, mapping)
        # Replace subtransactions when updating
        subtransactions = subtransaction_db.get_entries((transaction['id'],))
        subtransaction_db.delete_entries(
            [subtransaction['id'] for subtransaction in subtransactions]
        )
        subtransactions = self._add_subtransactions(transaction['id'],
                                                    subtransactions_data)
        # Refresh the transaction information
        transaction = self.get_entry(transaction['id'])
        return transaction, subtransactions

    def _add_subtransactions(self, transaction_id, subtransactions_data):
        """Add subtransactions to the database for the data given."""
        subtransaction_db = CreditSubtransactionHandler()
        # Assemble mappings to add subtransactions
        subtransactions = []
        for subtransaction_data in subtransactions_data:
            # Complete the mapping and add the subtransaction to the database
            sub_mapping = {'transaction_id': transaction_id,
                           **subtransaction_data}
            subtransaction = subtransaction_db.add_entry(sub_mapping)
            subtransactions.append(subtransaction)
        return subtransactions

    def get_associated_transaction(self, transaction_id):
        """
        Find an internal transaction that matches this transaction.

        Checks the bank transaction database for a transaction that
        matches the given transaction.

        Parameters
        ----------
        transaction_id : integer
            The ID for the credit transaction that should be matched.

        Returns
        -------
        associated_transaction : dict
            A dictionary of transaction types and the corresponding
            bank transaction that matches the given transaction. For
            compatibility with the bank transaction handler, the
            returned dictionary contains two types of possible
            transactions: 'bank' and 'credit' transactions. Since this
            class finds a bank transaction corresponding to a given
            credit transaction, the 'credit' key in the dictionary will
            always be assigned a value of `None`.
        """
        transaction = self.get_entry(transaction_id,
                                     ('internal_transaction_id',))
        internal_transaction_id = transaction['internal_transaction_id']
        if not internal_transaction_id:
            return None
        associated_transaction = {'bank': None, 'credit': None}
        # Get matching bank transactions
        query = ("SELECT * "
                 "  FROM bank_transactions_view AS t "
                 "       INNER JOIN bank_accounts AS a "
                 "          ON a.id = t.account_id "
                 "       INNER JOIN banks AS b "
                 "          ON b.id = a.bank_id "
                 "       INNER JOIN bank_account_types AS types "
                 "          ON types.id = a.account_type_id "
                 " WHERE b.user_id =? AND t.id != ? "
                 "       AND t.internal_transaction_id = ?")
        placeholders = (self.user_id, transaction_id, internal_transaction_id)
        bank_transactions = self._query_entries(query, placeholders)
        if bank_transactions:
            associated_transaction['bank'] = bank_transactions[0]
        return associated_transaction


class CreditSubtransactionHandler(DatabaseHandler):
    """
    A database handler for accessing credit subtransactions.

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
    _table = 'credit_subtransactions'

    def get_entries(self, transaction_ids=None, fields=None):
        """
        Get all subtransactions for a credit transaction.

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
            statements, cards, or accounts tables) to be returned. By
            default, all fields are returned.

        Returns
        –––––––
        subtransactions : list of sqlite3.Row
            A list of credit card subtransactions that are associated
            with the given transaction.
        """
        transaction_filter = filter_items(transaction_ids, 'transaction_id',
                                          'AND')
        query = (f"SELECT {select_fields(fields, 's_t.id')} "
                  "  FROM credit_subtransactions AS s_t "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                 f" WHERE user_id = ? {transaction_filter}")
        placeholders = (self.user_id, *fill_places(transaction_ids))
        subtransactions = self._query_entries(query, placeholders)
        return subtransactions

    def get_entry(self, subtransaction_id, fields=None):
        """
        Get a subtransaction from the database given its ID.

        Accesses a set of fields for a given subtransaction. By default,
        all fields for a subtransaction, the corresponding statement,
        issuing credit card and account are returned.

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
        query = (f"SELECT {select_fields(fields, 't.id')} "
                  "  FROM credit_subtransactions AS s_t "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                  "       INNER JOIN credit_cards AS c "
                  "          ON c.id = s.card_id "
                  "       INNER JOIN credit_accounts AS a "
                  "          ON a.id = c.account_id "
                  "       INNER JOIN banks AS b "
                  "          ON b.id = a.bank_id "
                  " WHERE user_id = ? AND s_t.id = ?")
        placeholders = (self.user_id, subtransaction_id)
        abort_msg = (f'Subtransaction ID {subtransaction_id} does not exist '
                      'for the user.')
        subtransaction = self._query_entry(query, placeholders, abort_msg)
        return subtransaction

    def add_entry(self, mapping):
        """
        Add a subtransaction to the database.

        Uses a mapping produced by a `CreditTransactionForm` to add a
        new subtransaction into the database. The mapping includes
        information for the subtransaction, including the corresponding
        transaction. The mapping also provides a list of tags that have
        been assigned to the new subtransaction.

        Parameters
        ––––––––––
        mapping : dict
            A mapping between database fields and the value to be
            entered into that field for the subtransaction.

        Returns
        –––––––
        subtransaction : sqlite3.Row
            The saved transaction.
        """
        tag_db = CreditTagHandler()
        # Override the default method to account for tags
        tags = mapping.pop('tags')
        subtransaction = super().add_entry(mapping)
        # Link tags to the subtransaction
        tag_db.update_tag_links(subtransaction['id'], tags)
        return subtransaction


class CreditTagHandler(DatabaseHandler):
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
    table : str
        The name of the database table that this handler manages.
    db : sqlite3.Connection
        A connection to the database for interfacing.
    cursor : sqlite.Cursor
        A cursor for executing database interactions.
    user_id : int
        The ID of the user who is the subject of database access.
    """
    table = 'credit_tags'

    def __init__(self, db=None, user_id=None, check_user=True):
        super().__init__(db=db, user_id=user_id, check_user=check_user)

    def get_entries(self, tag_names=None, transaction_ids=None,
                    subtransaction_ids=None, fields=DATABASE_FIELDS[table],
                    ancestors=True):
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
        subtransaction_ids : tuple of int, optional
            A sequence of subtransaction IDs for which tags will be
            selected (if `None`, all subtransaction tags will be selected).
        fields : tuple of str, optional
            A sequence of fields to select from the database (if `None`,
            all fields will be selected). A field can be any column from
            the 'credit_tags' table.
        ancestors : bool, optional
            A flag indicating whether the query should include tags
            that are ancestors of other tags in the list of returned
            tags. The default is `True` (ancestor tags are returned).

        Returns
        –––––––
        tags : list of sqlite3.Row
            A list of credit card transaction tags matching the criteria.
        """
        name_filter = filter_items(tag_names, 'tag_name', 'AND')
        transaction_filter = filter_items(transaction_ids,
                                          'transaction_id',
                                          'AND')
        subtransaction_filter = filter_items(subtransaction_ids,
                                             'subtransaction_id',
                                             'AND')
        query = (f"SELECT {select_fields(fields, 'DISTINCT tags.id')} "
                  "  FROM credit_tags AS tags "
                  "       LEFT OUTER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_subtransactions AS s_t "
                  "          ON s_t.id = l.subtransaction_id "
                 f" WHERE user_id = ? {name_filter} "
                 f"       {transaction_filter} {subtransaction_filter}")
        placeholders = (self.user_id, *fill_places(tag_names),
                        *fill_places(transaction_ids),
                        *fill_places(subtransaction_ids))
        tags = self._query_entries(query, placeholders)
        # If specified, remove ancestors from the list of tags
        if not ancestors:
            for tag in tags:
                for ancestor in self.get_ancestors(tag['id']):
                    if ancestor in tags:
                        tags.remove(ancestor)
        return tags

    def get_entry(self, tag_id, fields=None):
        """
        Get a credit transaction tag from the database given its ID.

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
        query = (f"SELECT {select_fields(fields, 'tags.id')} "
                  "  FROM credit_tags AS tags "
                  " WHERE user_id = ? AND id = ?")
        placeholders = (self.user_id, tag_id)
        abort_msg = (f'Tag ID {tag_id} does not exist for the user.')
        tag = self._query_entry(query, placeholders, abort_msg)
        return tag

    def get_subtags(self, tag_id, fields=None):
        """
        Get subcategories of a credit transaction tag.

        Accesses a set of fields for children of a given tag. By
        default, all fields for a tag are returned.

        Parameters
        ––––––––––
        tag_id : int
            The ID of the tag for which to find subtags.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        subtags : list of sqlite3.Row
            A list of credit card transaction tags that are
            subcategories of the given tag.
        """
        query = (f"SELECT {select_fields(fields, 'tags.id')} "
                  "  FROM credit_tags AS tags "
                  " WHERE user_id = ? AND parent_id IS ?")
        placeholders = (self.user_id, tag_id)
        subtags = self._query_entries(query, placeholders)
        return subtags

    def get_supertag(self, tag_id, fields=None):
        """
        Get the supercategory (parent) of a credit transaction tag.

        Accesses a set of fields for the parent of a given tag. By
        default, all fields for a tag are returned.

        Parameters
        ––––––––––
        tag_id : int
            The ID of the tag for which to find supertags.
        fields : tuple of str, optional
            The fields (in the tags table) to be returned.

        Returns
        –––––––
        supertag : sqlite3.Row, None
            The credit card transaction tag that is the parent category
            of the given tag. Returns `None` if no parent tag is found.
        """
        tag = self.get_entry(tag_id)
        if tag['parent_id']:
            supertag = self.get_entry(tag['parent_id'])
        else:
            supertag = None
        return supertag

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
        query = (f"SELECT {select_fields(fields, 'tags.id')} "
                  "  FROM credit_tags AS tags "
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
            The dictionary representing the user's tags. Keys are
            sqlite3.Row objects.
        """
        heirarchy = {}
        for tag in self.get_subtags(parent_id):
            heirarchy[tag] = self.get_heirarchy(tag['id'])
        return heirarchy

    def get_ancestors(self, tag_id):
        """
        Get the ancestor tags of a given tag.

        Traverses the heirarchy, starting from the given tag and returns
        a list of all tags that are ancestors of the given tag.

        Parameters
        ––––––––––
        tag_id : int
            The ID of the tag for which to find ancestors.

        Returns
        –––––––
        ancestors : list of sqlite3.Row
            The ancestors of the given tag.
        """
        ancestors = []
        ancestor = self.get_supertag(tag_id, fields=('tag_name',))
        while ancestor:
            ancestors.append(ancestor)
            ancestor = self.get_supertag(ancestor['id'], fields=('tag_name',))
        return ancestors

    def update_tag_links(self, subtransaction_id, tag_names):
        """
        Update the tag links for a transaction in the database.

        Given a subtransaction and a list of tag names, each tag is
        applied to the subtransaction. Then, each existing tag that is
        not in the list of tag names is disassociated with the
        subtransaction. Tag names that do not already have database
        entries are created.

        Parameters
        ––––––––––
        subtransaction_id : int
            The ID of a subtransaction database entry that will be
            assigned the tags.
        tag_names : list of str
            Tag names to be assigned to the given transactions.
        """
        # Remove existing tags
        for tag in self.get_entries(subtransaction_ids=(subtransaction_id,)):
            # Unlink the tag from the subtransaction
            self.unlink(tag['id'], subtransaction_id)
        # Add the new tags
        linked_tags = []
        for tag_name in tag_names:
            # Get the matching tag
            tag = self.find_tag(tag_name, fields=('tag_name',))
            # Create the tag if it does not already exist in the database
            if not tag:
                tag_data = {'parent_id': None,
                            'user_id': self.user_id,
                            'tag_name': tag_name}
                tag = self.add_entry(tag_data)
            # Link the tag to the transaction
            if tag not in linked_tags:
                # Link all ancestor tags with this tag
                for ancestor in self.get_ancestors(tag['id']):
                    if ancestor not in linked_tags:
                        self.link(ancestor['id'], subtransaction_id)
                        linked_tags.append(ancestor)
                self.link(tag['id'], subtransaction_id)
                linked_tags.append(tag)

    def link(self, tag_id, subtransaction_id):
        """Add a tag to the given subtransaction."""
        # Add the subtransaction-tag link if the two are not already associated
        try:
            self.cursor.execute(
                "INSERT INTO credit_tag_links (subtransaction_id, tag_id) "
               f"     VALUES (?, ?)",
                (subtransaction_id, tag_id)
            )
            self.db.commit()
        except IntegrityError:
            # The tag link already exists
            pass

    def unlink(self, tag_id, subtransaction_id):
        """Remove a tag from the given subtransaction."""
        # Delete the subtransaction-tag link
        self.cursor.execute(
            "DELETE "
            "  FROM credit_tag_links "
            " WHERE subtransaction_id = ? AND tag_id = ? ",
            (subtransaction_id, tag_id)
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
        fields = ['SUM(subtotal) total', 'tag_name']
        groups = ['tags.id']
        if group_statements:
            fields.append('t.statement_id')
            groups.append('t.statement_id')
        query = (f"SELECT {', '.join(fields)} "
                  "  FROM credit_tags AS tags "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_subtransactions AS s_t "
                  "          ON s_t.id = l.subtransaction_id "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
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
                    "       INNER JOIN banks AS b "
                    "             ON b.id = a.bank_id "
                   f" WHERE b.user_id = ? {statement_filter}")
        tag_filter = filter_items(tag_ids, 'tag_id', 'AND')
        statement_filter = filter_items(statement_ids, 'statement_id', 'AND')
        query = (f"SELECT SUM(subtotal) / ({subquery}) average_total, tag_name "
                  "  FROM credit_tags AS tags "
                  "       INNER JOIN credit_tag_links AS l "
                  "          ON l.tag_id = tags.id "
                  "       INNER JOIN credit_subtransactions AS s_t "
                  "          ON s_t.id = l.subtransaction_id "
                  "       INNER JOIN credit_transactions AS t "
                  "          ON t.id = s_t.transaction_id "
                  "       INNER JOIN credit_statements AS s "
                  "          ON s.id = t.statement_id "
                 f" WHERE tags.user_id = ? {tag_filter} {statement_filter} "
                 f" GROUP BY tags.id")
        placeholders = (self.user_id, *fill_places(statement_ids),
                        self.user_id, *fill_places(statement_ids))
        tag_average_totals = self._query_entries(query, placeholders)
        return tag_average_totals


def save_transaction(form, transaction_id=None):
    """
    Save a credit transaction.

    Saves a transaction in the database. If a transaction ID is given,
    then the transaction is updated with the form information. Otherwise
    the form information is added as a new entry.

    Parameters
    ----------
    form : flask_wtf.FlaskForm
        The form being used to provide the data being saved.
    transaction_id : int
        The ID of the transaction to be saved. If provided, the
        named transaction will be updated in the database. Otherwise, if
        the transaction ID is `None`, a new transaction will be added.

    Returns
    -------
    entry : tuple (sqlite3.Row, list of sqlite3.Row)
        An "entry" corresponding to a transaction in the database and
        all associated subtransactions.

    Raises
    ------
    wtfforms.validators.ValidationError
        Raised when the form does not validate properly.
    """
    if form.validate():
        transaction_db = CreditTransactionHandler()
        transaction_data = form.transaction_data
        if transaction_id:
            # Update the database with the updated transaction
            entry = transaction_db.update_entry(transaction_id,
                                                transaction_data)
        else:
            # Insert the new transaction into the database
            entry = transaction_db.add_entry(transaction_data)
        return entry
    else:
        # Show an error to the user and print the errors for the admin
        flash(form_err_msg)
        print(form.errors)
        raise ValidationError('The form did not validate properly.')

