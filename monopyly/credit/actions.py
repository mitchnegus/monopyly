"""Module describing logical credit actions (to be used in routes)."""
from ..common.form_utils import execute_on_form_validation
from ..common.actions import get_groupings
from ..banking.transactions import record_new_transfer
from .cards import CreditCardHandler
from .statements import CreditStatementHandler
from .transactions import CreditTransactionHandler


def get_card_statement_groupings(cards):
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
    # Specify the fields explicitly to make use of date converters
    fields = ('card_id', 'issue_date', 'due_date', 'balance', 'payment_date')
    # Get groupings of statements (grouped by card)
    statement_db = CreditStatementHandler()
    card_statements = get_groupings(cards, statement_db, fields=fields)
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
    if card['active']:
        # Only one other active card must exist for this account
        card_db = CreditCardHandler()
        active_cards = card_db.get_entries(account_ids=(card['account_id'],),
                                           active=True,
                                           fields=('last_four_digits',))
        other_active_cards = [_ for _ in active_cards if _['id'] != card['id']]
        if len(other_active_cards) == 1:
            other_card = other_active_cards[0]
            # That active card must have statements with an unpaid balance
            statement_db = CreditStatementHandler()
            statements = statement_db.get_entries(card_ids=(other_card['id'],),
                                                  fields=('balance',))
            if statements:
                latest_statement = statements[0]
                if latest_statement['balance'] > 0:
                    return other_card
    # Card does not meet all of these conditions
    return None


@execute_on_form_validation
def transfer_credit_card_statement(form, card_id, prior_card_id):
    """Transfer a credit statement between cards based on form input."""
    # If response is affirmative, transfer the statement to the new card
    if form['transfer'].data == 'yes':
        # Get the prior card's most recent statement; assign it to the new card
        statement_db = CreditStatementHandler()
        statement = statement_db.get_entries(card_ids=(prior_card_id,))[0]
        statement_db.update_entry_value(statement['id'], 'card_id', card_id)
        # Deactivate the old card
        card_db = CreditCardHandler()
        prior_card = card_db.get_entry(prior_card_id)
        card_db.update_entry_value(prior_card_id, 'active', 0)


def make_payment(card_id, payment_account_id, payment_date, payment_amount):
    """
    Make a payment towards the credit card balance.

    Parameters
    ----------
    card_id : int
        The ID of the credit card towards which to make a payment.
    payment_account_id : int
        The ID of the bank account from which to draw money to make the
        payment.
    payment_date : datetime.date
        The date on which to make the payment.
    payment_amount : float
        The amount of money to make for the payment.
    """
    # Get the card to be paid
    card = CreditCardHandler().get_entry(card_id)
    # Determine the expected statement based on the payment date
    payment_statement = CreditStatementHandler().infer_statement(card,
                                                                 payment_date,
                                                                 creation=True)
    # Add the payment as a transaction in the database
    if payment_account_id:
        # Populate a mapping for the transfer
        card_name = f"{card['bank_name']}-{card['last_four_digits']}"
        bank_mapping = {
            'account_id': payment_account_id,
            'transaction_date': payment_date,
            'subtransactions': [{
                'subtotal': -payment_amount,
                'note': f"Credit card payment ({card_name})",
            }]
        }
        transfer, subtransactions = record_new_transfer(bank_mapping)
        internal_transaction_id = transfer['internal_transaction_id']
    else:
        internal_transaction_id = None
    credit_mapping = {
        'internal_transaction_id': internal_transaction_id,
        'statement_id': payment_statement['id'],
        'transaction_date': payment_date,
        'vendor': card['bank_name'],
        'subtransactions': [{
            'subtotal': -payment_amount,
            'note': 'Card payment',
            'tags': ['Payments'],
        }],
    }
    CreditTransactionHandler().add_entry(credit_mapping)


def get_credit_statement_details(statement_id):
    """Get default statement details (e.g., the account and transactions)."""
    # Get the statement information from the database
    statement_fields = ('account_id', 'card_id', 'bank_name',
                        'last_four_digits', 'issue_date', 'due_date',
                        'balance', 'payment_date')
    statement_db = CreditStatementHandler()
    statement = statement_db.get_entry(statement_id, fields=statement_fields)
    # Get all of the transactions for the statement from the database
    transaction_fields = ('transaction_date', 'vendor', 'total', 'notes',
                          'internal_transaction_id')
    sort_order = 'DESC'
    transaction_db = CreditTransactionHandler()
    transactions = transaction_db.get_entries(statement_ids=(statement['id'],),
                                              sort_order=sort_order,
                                              fields=transaction_fields)
    return statement, transactions
