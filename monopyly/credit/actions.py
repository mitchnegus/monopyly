"""Module describing logical credit actions (to be used in routes)."""
from ..common.forms.utils import execute_on_form_validation
from ..banking.transactions import record_new_transfer
from .cards import CreditCardHandler
from .statements import CreditStatementHandler
from .transactions import CreditTransactionHandler


def get_card_statement_grouping(cards):
    """
    Get groupings (by card) of credit card statements.

    Parameters
    ----------
    cards : list of sqlite3.Row
        The database card entries for which to get statements.

    Returns
    -------
    card_statements : dict
        A mapping between the card entries and a list of all
        corresponding statement entries for that card.
    """
    card_statements = {}
    for card in cards:
        card_statements[card] = CreditStatementHandler.get_statements(
            card_ids=(card.id,),
            sort_order="DESC",
        )
    return card_statements


def get_potential_preceding_card(card):
    """
    Get the card that this new card may be intended to replace (if any).

    When a new card is added, there is a good chance that it may be
    replacing an existing card. Check to see if there is a good
    candidate card that might be replaced (a single active card with an
    unpaid balance affiliated with the same account as the new card).

    Parameters
    ----------
    card : sqlite3.Row
        The new card being added to the database.

    Returns
    -------
    preceding_card : sqlite3.Row
        A card that matches the criteria, which may be being replaced by
        the new card.
    """
    # Card must be active
    if card.active:
        # Only one other active card must exist for this account
        active_cards = CreditCardHandler.get_cards(
            account_ids=(card.account_id,),
            active=True,
        )
        other_active_cards = [_ for _ in active_cards if _.id != card.id]
        if len(other_active_cards) == 1:
            other_card = other_active_cards[0]
            # That active card must have statements with an unpaid balance
            statements = CreditStatementHandler.get_statements(
                card_ids=(other_card.id,),
            )
            latest_statement = statements.first()
            if latest_statement:
                if latest_statement.balance > 0:
                    return other_card
    # Card does not meet all of these conditions
    return None


@execute_on_form_validation
def transfer_credit_card_statement(form, card_id, prior_card_id):
    """Transfer a credit statement between cards based on form input."""
    # If response is affirmative, transfer the statement to the new card
    if form.transfer.data == 'yes':
        # Get the prior card's most recent statement; assign it to the new card
        statements = CreditStatementHandler.get_statements(
            card_ids=(prior_card_id,)
        )
        latest_statement = statements.first()
        CreditStatementHandler.update_entry(
            latest_statement.id, card_id=card_id
        )
        # Deactivate the old card
        prior_card = CreditCardHandler.get_entry(prior_card_id)
        CreditCardHandler.update_entry(prior_card_id, active=0)


def make_payment(card_id, payment_account_id, payment_date, payment_amount):
    """
    Make a payment towards the credit card balance.

    Parameters
    ----------
    card_id : int
        The ID of the credit card towards which to make a payment.
    payment_account_id : int, None
        The ID of the bank account from which to draw money to make the
        payment. If the argument is `None` than no paying account is
        registered.
    payment_date : datetime.date
        The date on which to make the payment.
    payment_amount : float
        The amount of money to make for the payment.
    """
    # Get the card to be paid
    card = CreditCardHandler.get_entry(card_id)
    payee = card.account.bank.bank_name
    # Determine the expected statement based on the payment date
    payment_statement = CreditStatementHandler.infer_statement(
        card,
        payment_date,
        creation=True,
    )
    # Add the payment as a transaction in the database
    if payment_account_id:
        # Populate a mapping for the transfer
        payment_note = f"Credit card payment ({payee}-{card.last_four_digits})"
        bank_mapping = {
            'account_id': payment_account_id,
            'transaction_date': payment_date,
            'subtransactions': [
                {'subtotal': -payment_amount, 'note': payment_note},
            ]
        }
        transfer = record_new_transfer(bank_mapping)
        internal_transaction_id = transfer.internal_transaction_id
    else:
        internal_transaction_id = None
    credit_mapping = {
        'internal_transaction_id': internal_transaction_id,
        'statement_id': payment_statement.id,
        'transaction_date': payment_date,
        'vendor': payee,
        'subtransactions': [{
            'subtotal': -payment_amount,
            'note': 'Card payment',
            'tags': ['Payments'],
        }],
    }
    CreditTransactionHandler.add_entry(**credit_mapping)
