"""
Tools for interacting with credit cards in the database.
"""

from dry_foundation.database.handler import DatabaseHandler

from ..common.forms.utils import execute_on_form_validation
from ..database.models import Bank, CreditAccount, CreditCard


class CreditCardHandler(DatabaseHandler, model=CreditCard):
    """
    A database handler for managing credit cards.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    @classmethod
    def get_cards(
        cls, bank_ids=None, account_ids=None, last_four_digits=None, active=None
    ):
        """
        Get credit cards from the database.

        Query the database to select credit card fields. Cards can be
        filtered by the issuing bank, account, last four digits of the
        card number or by active status.

        Parameters
        ----------
        bank_ids : tuple of int, optional
            A sequence of bank IDs for which cards will be selected
            (if `None`, all banks will be selected).
        account_ids : tuple of int, optional
            A sequence of account IDs for which cards will be selected
            (if `None`, all accounts will be selected).
        last_four_digits : tuple of str, optional
            A sequence of final 4 digits for which cards will be
            selected (if `None`, cards with any last 4 digits will be
            selected).
        active : bool, optional
            A flag indicating whether to return active cards, inactive
            cards, or both. The default is `None`, where all cards are
            returned regardless of the card's active status.

        Returns
        -------
        cards : sqlalchemy.engine.ScalarResult
            Returns credit cards matching the criteria.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(CreditAccount, "bank_id", bank_ids)
        criteria.add_match_filter(cls.model, "account_id", account_ids)
        criteria.add_match_filter(cls.model, "last_four_digits", last_four_digits)
        criteria.add_match_filter(cls.model, "active", active)
        cards = super().get_entries(criteria=criteria)
        return cards

    @classmethod
    def find_card(cls, bank_name=None, last_four_digits=None):
        """
        Find a credit card using uniquely identifying characteristics.

        Queries the database to find a credit card based on the provided
        criteria. Credit cards in the database can almost always be
        uniquely identified given the user's ID and the last four digits
        of the card number. In rare cases where a user has two cards
        with the same last four digits, the issuing bank can be used to
        help determine the card. (It is expected to be exceptionally
        rare that a user has two cards with the same last four digits
        from the same bank.) If multiple cards do match the criteria,
        only the first one found is returned.

        Parameters
        ----------
        bank_name : str, optional
            The bank of the card to find.
        last_four_digits : int, optional
            The last four digits of the card to find.

        Returns
        -------
        card : sqlite3.Row
            A credit card entry matching the given criteria. If no
            matching card is found, returns `None`.
        """
        criteria = cls._initialize_criteria_list()
        criteria.add_match_filter(Bank, "bank_name", bank_name)
        criteria.add_match_filter(cls.model, "last_four_digits", last_four_digits)
        card = super().find_entry(criteria=criteria)
        return card

    @classmethod
    def _customize_entries_query(
        cls, query, filters, sort_order, offset=None, limit=None
    ):
        query = super()._customize_entries_query(
            query, filters, sort_order, offset=offset, limit=limit
        )
        # Order cards by active status (active cards first)
        query = query.order_by(cls.model.active.desc())
        return query

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete a credit card from the database.

        Given a card ID, delete the credit card from the database.
        Deleting a card will also delete all statements (and
        transactions) for that card.

        Parameters
        ----------
        entry_id : int
            The ID of the credit card to be deleted.
        """
        super().delete_entry(entry_id)


@execute_on_form_validation
def save_card(form, card_id=None):
    """
    Save a credit card.

    Saves a credit card in the database. If a card ID is given, then the
    card is updated with the form information. Otherwise, the form
    information is added as a new entry.

    Parameters
    ----------
    form : CreditCardForm
        The form beign used to provide the data being saved.
    card_id : int
        The ID of hte card to be saved. If provided, the named card will
        be updated in the database. Otherwise, if the card ID is `None`,
        a new card will be added.

    Returns
    -------
    card : database.models.CreditCard
        The saved card.
    """
    card_data = form.card_data
    if card_id:
        # Update the database with the updated card
        card = CreditCardHandler.update_entry(card_id, **card_data)
    else:
        # Insert the new transaction into the database
        card = CreditCardHandler.add_entry(**card_data)
    return card
