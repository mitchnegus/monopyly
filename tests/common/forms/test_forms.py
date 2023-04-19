"""Tests for custom forms."""
import pytest

from monopyly.common.forms import TransactionForm


@pytest.fixture
def abstract_subform():
    return TransactionForm.SubtransactionSubform()


class TestSubtransactionForm:

    def test_abstract_subform_gather_entry_data_invalid(self, client_context, abstract_subform):
        with pytest.raises(RuntimeError):
            abstract_subform.gather_entry_data(None)
