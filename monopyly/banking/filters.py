"""
Filters defined for the banking blueprint.
"""
from .blueprint import bp


@bp.app_template_filter("is_single_bank_transfer")
def check_transfer_is_within_bank(transaction):
    """Check if the transfer is linked ot another transaction at the same bank."""
    if transaction.internal_transaction:
        linked_bank_transactions = transaction.internal_transaction.bank_transactions
        if len(linked_bank_transactions) > 1:
            common_bank_id = linked_bank_transactions[0].account.bank_id
            return all(
                transaction.account.bank_id == common_bank_id
                for transaction in linked_bank_transactions
            )
    return False
