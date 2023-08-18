"""Tests for the credit module managing transaction activity reconciliation."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from monopyly.credit.transactions.activity.data import (
    ActivityLoadingError,
    TransactionActivities,
    TransactionActivityGroup,
    TransactionActivityLoader,
)
from monopyly.credit.transactions.activity.parser import (
    _TransactionActivityParser,
    parse_transaction_activity_file,
)


@pytest.fixture
def mock_csv_file():
    return Mock(name="mock_csv_file", filename="mock_file.csv")


@patch("monopyly.credit.transactions.activity.parser._TransactionActivityParser")
def test_parse_activity_file(mock_parser, mock_csv_file):
    data = parse_transaction_activity_file(mock_csv_file)
    assert data is mock_parser.return_value.data


@patch(
    "monopyly.credit.transactions.activity.parser._TransactionActivityParser",
    side_effect=ActivityLoadingError,
)
def test_parse_activity_file_not_loaded(mock_parser, mock_csv_file):
    data = parse_transaction_activity_file(mock_csv_file)
    assert data is None


def test_parse_real_activity_file(client_context):
    test_activity_file = Path(__file__).parent / "test_reconciliation_data.csv"
    data = parse_transaction_activity_file(test_activity_file)
    assert len(data) == 3
    assert data[0].transaction_date == date(2020, 5, 2)
    assert data[2].total == 99.00


class TestTransactionActivities:
    test_data = [
        ["date0", 100, "description0"],
        ["date1", 200, "description1"],
        ["date2", 300, "description2"],
    ]

    def test_initialization(self):
        activities = TransactionActivities(self.test_data)
        for activity, row_data in zip(activities, self.test_data, strict=True):
            assert activity.transaction_date == row_data[0]
            assert activity.total == row_data[1]
            assert activity.description == row_data[2]

    def test_data_total(self):
        activities = TransactionActivities(self.test_data)
        assert activities.total == 600


class TestTransactionActivityGroup:
    test_data = [
        ["date", 100, "description"],
        ["date", 200, "description"],
        ["date", 300, "description"],
        ["other date", 250, "description"],
        ["date", 150, "other description"],
    ]
    activities = TransactionActivities(test_data)

    def test_initialization(self):
        transaction_activities = self.activities[:3]
        grouping = TransactionActivityGroup(transaction_activities)
        assert grouping.transaction_date == "date"
        assert grouping.total == 600
        assert grouping.description == "description"

    @pytest.mark.parametrize(
        "transaction_activities, exception",
        [
            # Wrong date
            [activities[1:4], ValueError],
            # Wrong description
            [[activities[1], activities[2], activities[4]], ValueError],
        ],
    )
    def test_initialization_invalid(self, transaction_activities, exception):
        with pytest.raises(exception):
            TransactionActivityGroup(transaction_activities)


@pytest.fixture
def activity_dir(tmp_path):
    _activity_dir = tmp_path / ".credit_activity"
    yield _activity_dir


class TestTransactionActivityLoader:
    def test_initialization(self, client_context, activity_dir):
        file_loader = TransactionActivityLoader(activity_dir)
        assert file_loader.activity_dir == activity_dir
        assert activity_dir.exists()

    def test_upload(self, client_context, activity_dir, mock_csv_file):
        file_loader = TransactionActivityLoader(activity_dir)
        assert len(file_loader.loaded_files) == 0
        activity_filepath = file_loader.upload(mock_csv_file)
        mock_csv_file.save.assert_called_once()
        assert activity_filepath == activity_dir / mock_csv_file.filename
        assert len(file_loader.loaded_files) == 1

    def test_upload_invalid(self, client_context, activity_dir):
        invalid_csv_file = Mock(name="mock_csv_file", filename="")
        file_loader = TransactionActivityLoader(activity_dir)
        with pytest.raises(ActivityLoadingError):
            file_loader.upload(invalid_csv_file)

    @pytest.mark.parametrize("loaded_filepaths", [[Mock()], [Mock(), Mock()]])
    @patch("pathlib.Path.unlink")
    def test_cleanup(
        self, mock_unlink_method, loaded_filepaths, client_context, activity_dir
    ):
        file_loader = TransactionActivityLoader(activity_dir)
        file_loader.loaded_files = loaded_filepaths
        file_loader.cleanup()
        for mock_path in loaded_filepaths:
            mock_path.unlink.assert_called_once()


class TestTransactionActivityParser:
    mock_csv_content = {
        "format0": (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment"
        ),
        "format1": (
            "Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment"
        ),
        "format2": (  # JPMCB
            "Transaction Date, Post Date, Description, Category, Type, Amount, Memo\n"
            "1/1/2000, 1/2/2000, RESTAURANT, Food & Drink, Sale, -50,\n"
            "1/2/2000, 1/3/2000, SUPERMARKET, Groceries, Sale, -200,\n"
            "1/2/2000, 1/4/2000, Payment,, Payment, 100,"
        ),
        "format3": (  # Discover
            "Trans. Date, Post Date, Description, Amount, Category\n"
            "1/1/2000, 1/2/2000, RESTAURANT, 50, Restaurants\n"
            "1/2/2000, 1/3/2000, SUPERMARKET, 200, Supermarkets\n"
            "1/2/2000, 1/4/2000, INTERNET PAYMENT, -100, Payments and Credits"
        ),
    }

    # Pass the CSV format to the test for facilitating debugging
    @pytest.mark.parametrize("csv_format, csv_content", mock_csv_content.items())
    @patch("monopyly.credit.transactions.activity.parser.TransactionActivityLoader")
    def test_initialization(
        self,
        mock_file_uploader_cls,
        client_context,
        csv_format,
        csv_content,
        mock_csv_file,
        activity_dir,
    ):
        mock_file_uploader = mock_file_uploader_cls.return_value
        mock_upload_filepath = mock_file_uploader.upload.return_value
        mock_upload_filepath.open = mock_open(read_data=csv_content)
        parser = _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)
        parser.column_indices.values == TransactionActivities.column_types
        assert len(parser.data) == len(csv_content.strip().split("\n")[1:])
        mock_file_uploader.cleanup.assert_called_once()

    def test_initialization_no_data(self, client_context, mock_csv_file, activity_dir):
        missing_content = "Transaction, Total, Description\n"
        mock_open_method = mock_open(read_data=missing_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(ActivityLoadingError):
                _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)

    def test_initialization_missing_column(
        self, client_context, mock_csv_file, activity_dir
    ):
        invalid_content = (
            "Transaction, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment"
        )
        mock_open_method = mock_open(read_data=invalid_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)

    @pytest.mark.parametrize(
        "csv_format, csv_content",
        [
            *mock_csv_content.items(),
            (
                "format0_no-payments_all-postive_charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, 50, Restaurant\n"
                    "1/2/2000, 200, Supermarket"
                ),
            ),
            (
                "format0_no-payments_all-negative_charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, -50, Restaurant\n"
                    "1/2/2000, -200, Supermarket"
                ),
            ),
            (
                "format0_no-payments_majority-negative-charges",
                (
                    "Transaction Date, Total, Description\n"
                    "1/1/2000, -50, Restaurant\n"
                    "1/2/2000, -200, Supermarket\n"
                    "1/2/2000, 100, Refund"
                ),
            ),
        ],
    )
    @patch("monopyly.credit.transactions.activity.parser.TransactionActivityLoader")
    def test_initialization_charge_sign(
        self,
        mock_file_uploader_cls,
        client_context,
        csv_format,
        csv_content,
        mock_csv_file,
        activity_dir,
    ):
        csv_rows = csv_content.split("\n")[1:]
        mock_file_uploader = mock_file_uploader_cls.return_value
        mock_upload_filepath = mock_file_uploader.upload.return_value
        mock_upload_filepath.open = mock_open(read_data=csv_content)
        parser = _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)
        for csv_row, activity in zip(csv_rows, parser.data, strict=True):
            # For database consistency, charges should have positive totals
            if any(word in csv_row for word in ("Payment", "Refund")):
                assert activity.total < 0
            else:
                assert activity.total > 0
        mock_file_uploader.cleanup.assert_called_once()

    def test_initialization_charge_sign_unknown(
        self, client_context, mock_csv_file, activity_dir
    ):
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
                _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)

    def test_initialization_no_payments_charge_sign_unknown(
        self, client_context, mock_csv_file, activity_dir
    ):
        ambiguous_charge_sign_content = (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, -200, Supermarket\n"
        )
        mock_open_method = mock_open(read_data=ambiguous_charge_sign_content)
        with patch.object(Path, "open", new=mock_open_method):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file, activity_dir=activity_dir)
