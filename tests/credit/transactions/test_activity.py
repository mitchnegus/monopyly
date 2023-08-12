"""Tests for the credit module managing transaction activity reconciliation."""
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from monopyly.credit.transactions.activity.parser import (
    TransactionActivities,
    _TransactionActivityParser,
    parse_transaction_activity_file,
)
from monopyly.credit.transactions.activity.reconciliation import ActivityMatchmaker


@patch("monopyly.credit.transactions.activity.parser._TransactionActivityParser")
def test_parse_activity_file(mock_parser):
    data = parse_transaction_activity_file("path/to/test_activity.csv")
    assert data is mock_parser.return_value.data


class TestTransactionActivities:
    def test_initialization(self):
        test_data = [
            ["date0", "total0", "description0"],
            ["date1", "total1", "description1"],
            ["date2", "total2", "description2"],
        ]
        activities = TransactionActivities(test_data)
        for activity, row_data in zip(activities, test_data):
            assert activity.transaction_date == row_data[0]
            assert activity.total == row_data[1]
            assert activity.description == row_data[2]


class TestTransactionActivityParser:
    mock_csv_content = {
        "format0": (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment\n"
        ),
        "format1": (
            "Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment\n"
        ),
        "format2": (  # JPMCB
            "Transaction Date, Post Date, Description, Category, Type, Amount, Memo\n"
            "1/1/2000, 1/2/2000, RESTAURANT, Food & Drink, Sale, -50,\n"
            "1/2/2000, 1/3/2000, SUPERMARKET, Groceries, Sale, -200,\n"
            "1/2/2000, 1/4/2000, Payment,, Payment, 100,\n"
        ),
        "format3": (  # Discover
            "Trans. Date, Post Date, Description, Amount, Category\n"
            "1/1/2000, 1/2/2000, RESTAURANT, 50, Restaurants\n"
            "1/2/2000, 1/3/2000, SUPERMARKET, 200, Supermarkets\n"
            "1/2/2000, 1/4/2000, INTERNET PAYMENT, -100, Payments and Credits\n"
        ),
    }
    mock_path = Path("path/to/test_data.csv")

    # Pass the CSV format to the test for facilitating debugging
    @pytest.mark.parametrize("csv_format, csv_content", mock_csv_content.items())
    def test_initialization(self, csv_format, csv_content):
        mock_open_method = mock_open(read_data=csv_content)
        with patch.object(Path, "open", new=mock_open_method):
            parser = _TransactionActivityParser(self.mock_path)
            parser.column_indices.values == TransactionActivities.column_types
            assert len(parser.data) == len(csv_content.strip().split("\n")[1:])

    def test_initialization_no_data(self):
        missing_content = "Transaction, Total, Description\n"
        mock_open_method = mock_open(read_data=missing_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(self.mock_path)

    def test_initialization_missing_column(self):
        invalid_content = (
            "Transaction, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment\n"
        )
        mock_open_method = mock_open(read_data=invalid_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(self.mock_path)

    @pytest.mark.parametrize(
        "csv_format, csv_content",
        [
            *mock_csv_content.items(),
            (
                "format0_no-payments_all-postive_charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, 50, Restaurant\n"
                    "1/2/2000, 200, Supermarket\n"
                ),
            ),
            (
                "format0_no-payments_all-negative_charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, -50, Restaurant\n"
                    "1/2/2000, -200, Supermarket\n"
                ),
            ),
            (
                "format0_no-payments_majority-negative-charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, -50, Restaurant\n"
                    "1/2/2000, -200, Supermarket\n"
                    "1/2/2000, 100, Refund\n"
                ),
            ),
        ],
    )
    def test_initialization_charge_sign(self, csv_format, csv_content):
        mock_open_method = mock_open(read_data=csv_content)
        with patch.object(Path, "open", new=mock_open_method):
            parser = _TransactionActivityParser(self.mock_path)
            for csv_row, activity in zip(csv_content.split("\n")[1:], parser.data):
                # For database consistency, charges should have positive totals
                if any(word in csv_row for word in ("Payment", "Refund")):
                    assert activity.total < 0
                else:
                    assert activity.total > 0

    def test_initialization_charge_sign_unknown(self):
        ambiguous_charge_sign_content = (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/3/2000, -100, Payment\n"
            "1/4/2000, 100, Payment\n"
        )
        mock_open_method = mock_open(read_data=ambiguous_charge_sign_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(self.mock_path)

    def test_initialization_no_payments_charge_sign_unknown(self):
        ambiguous_charge_sign_content = (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, -200, Supermarket\n"
        )
        mock_open_method = mock_open(read_data=ambiguous_charge_sign_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(self.mock_path)
