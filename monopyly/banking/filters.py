"""
Filters defined for the banking blueprint.
"""

from .blueprint import bp


@bp.app_template_filter("is_single_bank_transfer")
def check_transfer_is_within_bank(transaction_view):
    """Check if the transfer is linked to another transaction at the same bank."""
    if internal_transaction := transaction_view.internal_transaction:
        linked_bank_transactions = internal_transaction.bank_transaction_views
        if len(linked_bank_transactions) > 1:
            common_bank_id = linked_bank_transactions[0].account_view.bank_id
            return all(
                transaction.account_view.bank_id == common_bank_id
                for transaction in linked_bank_transactions
            )
    return False
