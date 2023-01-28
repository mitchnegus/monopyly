"""Tests for internal transactions."""
from sqlalchemy import select
from sqlalchemy.sql.expression import func

from monopyly.core.internal_transactions import add_internal_transaction
from monopyly.database.models import InternalTransaction
from ..helpers import transaction_lifetime


@transaction_lifetime
def test_add_internal_transaction(app, client_context):
    count_query = select(func.count(InternalTransaction.id))
    count = app.db.session.execute(count_query).scalar()
    assert count == 3
    entry_id = add_internal_transaction()
    assert entry_id == count + 1

