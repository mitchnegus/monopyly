"""Tests for internal transactions."""
from sqlalchemy import select
from sqlalchemy.sql.expression import func

from monopyly.core.internal_transactions import add_internal_transaction
from monopyly.database import db
from monopyly.database.models import InternalTransaction


def test_add_internal_transaction(client_context):
    count_query = select(func.count(InternalTransaction.id))
    count = db.session.execute(count_query).scalar()
    assert count == 3
    entry_id = add_internal_transaction()
    assert entry_id == count + 1

