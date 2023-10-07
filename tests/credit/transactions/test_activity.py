"""Tests for the credit module managing transaction activity reconciliation."""
from datetime import date
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from monopyly.credit.transactions.activity.data import (
    TransactionActivities,
    TransactionActivityGroup,
)
from monopyly.credit.transactions.activity.parser import (
    _TransactionActivityParser,
    parse_transaction_activity_file,
)
from monopyly.credit.transactions.activity.reconciliation import (
    ActivityMatchmaker,
    ExactMatchFinder,
    ExactMatchmaker,
    NearMatchFinder,
    NearMatchmaker,
)


@pytest.fixture
def mock_csv_file():
    return Mock(name="mock_csv_file", filename="mock_file.csv")


@patch("monopyly.credit.transactions.activity.parser._TransactionActivityParser")
def test_parse_activity_file(mock_parser, mock_csv_file):
    data = parse_transaction_activity_file(mock_csv_file)
    assert data is mock_parser.return_value.data


class TestTransactionActivities:
    def test_initialization(self):
        test_data = [
            ["date0", 100, "description0"],
            ["date1", 200, "description1"],
            ["date2", 300, "description2"],
        ]
        activities = TransactionActivities(test_data)
        for activity, row_data in zip(activities, test_data):
            assert activity.transaction_date == row_data[0]
            assert activity.total == row_data[1]
            assert activity.description == row_data[2]


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
    activity_dir = tmp_path / ".credit_activity"
    activity_dir.mkdir()
    yield activity_dir


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

    # Pass the CSV format to the test for facilitating debugging
    @pytest.mark.parametrize("csv_format, csv_content", mock_csv_content.items())
    def test_initialization(
        self, client_context, activity_dir, csv_format, csv_content, mock_csv_file
    ):
        mock_open_method = mock_open(read_data=csv_content)
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            parser = _TransactionActivityParser(mock_csv_file)
            mock_csv_file.save.assert_called_once()
            parser.column_indices.values == TransactionActivities.column_types
            assert len(parser.data) == len(csv_content.strip().split("\n")[1:])

    def test_initialization_make_activity_dir(self, client_context, mock_csv_file):
        csv_content = (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment\n"
        )
        mock_open_method = mock_open(read_data=csv_content)
        with (
            patch.object(Path, "open", new=mock_open_method),
            patch.object(Path, "mkdir") as mock_mkdir_method,
        ):
            parser = _TransactionActivityParser(mock_csv_file)
            mock_csv_file.save.assert_called_once()
            parser.column_indices.values == TransactionActivities.column_types
            assert len(parser.data) == len(csv_content.strip().split("\n")[1:])

    def test_initialization_no_data(self, client_context, mock_csv_file, activity_dir):
        missing_content = "Transaction, Total, Description\n"
        mock_open_method = mock_open(read_data=missing_content)
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file)

    def test_initialization_missing_column(
        self, client_context, mock_csv_file, activity_dir
    ):
        invalid_content = (
            "Transaction, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, 200, Supermarket\n"
            "1/2/2000, -100, Payment\n"
        )
        mock_open_method = mock_open(read_data=invalid_content)
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file)

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
    def test_initialization_charge_sign(
        self, client_context, csv_format, csv_content, mock_csv_file, activity_dir
    ):
        mock_open_method = mock_open(read_data=csv_content)
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            parser = _TransactionActivityParser(mock_csv_file)
            for csv_row, activity in zip(csv_content.split("\n")[1:], parser.data):
                # For database consistency, charges should have positive totals
                if any(word in csv_row for word in ("Payment", "Refund")):
                    assert activity.total < 0
                else:
                    assert activity.total > 0

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
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file)

    def test_initialization_no_payments_charge_sign_unknown(
        self, client_context, mock_csv_file, activity_dir
    ):
        ambiguous_charge_sign_content = (
            "Transaction Date, Total, Description\n"
            "1/1/2000, 50, Restaurant\n"
            "1/2/2000, -200, Supermarket\n"
        )
        mock_open_method = mock_open(read_data=ambiguous_charge_sign_content)
        with (
            patch.object(_TransactionActivityParser, "_activity_dir", new=activity_dir),
            patch.object(Path, "open", new=mock_open_method),
        ):
            with pytest.raises(RuntimeError):
                _TransactionActivityParser(mock_csv_file)


class TestActivityMatchFinders:
    mock_activity = TransactionActivities(
        [
            [date(2000, 1, 1), 50, "Restaurant"],
            [date(2000, 1, 1), 51, "Restaurant"],  # ---- only near match
            [date(2000, 1, 2), 50, "Restaurant"],  # ---- only near match
            [date(2000, 1, 1), 40, "Restaurant"],  # ---- too low
            [date(2000, 1, 1), 60, "Restaurant"],  # ---- too high
            [date(1999, 12, 20), 50, "Restaurant"],  # -- too early date
            [date(2000, 1, 10), 50, "Restaurant"],  # --- too late date
            [date(2000, 2, 20), 5, "Pharmacy"],  # ------ near (small value)
            [date(2000, 3, 30), 2, "Pharmacy"],  # ------ near, but wrong sign
        ]
    )

    def test_exact_match_finder_initialization(self):
        mock_transaction = Mock(
            transaction_date=date(2000, 1, 1), total=50, notes="..."
        )
        mock_data = self.mock_activity[:3]
        # Exact matches should have the same transaction date and total
        expected_matches = mock_data[:1]
        matches = ExactMatchFinder.find(mock_transaction, mock_data)
        assert matches == expected_matches

    def test_near_match_finder_initialization(self):
        mock_transaction = Mock(
            transaction_date=date(2000, 1, 1), total=50, notes="..."
        )
        mock_data = self.mock_activity
        # Near matches should have a date within a day or total within 10%
        expected_matches = mock_data[:3]
        matches = NearMatchFinder.find(mock_transaction, mock_data)
        assert matches == expected_matches

    def test_near_match_finder_close_total(self):
        mock_transaction = Mock(
            transaction_date=date(2000, 2, 20), total=3, notes="..."
        )
        mock_data = self.mock_activity
        # Near match should be close (absolutely) for low values
        expected_matches = [mock_data[7]]
        matches = NearMatchFinder.find(mock_transaction, mock_data)
        assert matches == expected_matches

    def test_near_match_finder_close_total_wrong_sign(self):
        mock_transaction = Mock(
            transaction_date=date(2000, 3, 30), total=-1, notes="..."
        )
        mock_data = self.mock_activity
        # Near match should be close (absolutely) for low values,
        # except when that changes the sign
        expected_matches = []
        matches = NearMatchFinder.find(mock_transaction, mock_data)
        assert matches == expected_matches


class TestActivityMatchmakers:
    mock_transactions = [
        Mock(
            transaction_date=date(2000, 1, 1),
            total=50,
            merchant="Restaurant",
            notes="Brunch",
        ),
        Mock(
            transaction_date=date(2000, 1, 1),
            total=51,
            merchant="Restaurant",
            notes="Brunch",
        ),
        Mock(
            transaction_date=date(2000, 1, 1),
            total=25,
            merchant="Restaurant",
            notes="Lunch",
        ),
        Mock(
            transaction_date=date(2000, 1, 5),
            total=60,
            merchant="Restaurant",
            notes="Dinner",
        ),
        Mock(
            transaction_date=date(2000, 1, 10),
            total=30,
            merchant="Restaurant",
            notes="Lunch",
        ),
        Mock(
            transaction_date=date(2000, 1, 15),
            total=40,
            merchant="Restaurant One",
            notes="Dinner",
        ),
        Mock(
            transaction_date=date(2000, 1, 15),
            total=40,
            merchant="Restaurant Two",
            notes="Dinner",
        ),
        Mock(
            transaction_date=date(2000, 2, 14),
            total=66,
            merchant="Florist",
            notes="Flowers",
        ),
        Mock(
            transaction_date=date(2000, 2, 14),
            total=82.17,
            merchant="Restaurant",
            notes="Romantic dinner",
        ),
        Mock(
            transaction_date=date(2000, 4, 1),
            total=0,
            merchant="Magician",
            notes="April Fools!",
        ),
        Mock(
            transaction_date=date(2000, 6, 1),
            total=19,
            merchant="Pharmacy",
            notes="Snacks, groceries",
        ),
    ]
    mock_activity = TransactionActivities(
        [
            # Unique exact match:
            [date(2000, 1, 1), 50, "Restaurant"],
            # Ambiguous exact match (ambiguous activity, selected by description):
            [date(2000, 1, 1), 51, "Restaurant"],
            # Ambiguous exact match (ambiguous activity):
            [date(2000, 1, 1), 51, "Mechanic"],
            # Unique exact match:
            [date(2000, 1, 5), 60, "Restaurant"],
            # Ambiguous exact match (best match indeterminable from description)
            [date(2000, 1, 10), 30, "Restaurant One"],
            # Ambiguous exact match (best match indeterminable from description)
            [date(2000, 1, 10), 30, "Restaurant Two"],
            # Ambiguous exact match (matches multiple transactions)
            [date(2000, 1, 15), 40, "Restaurant"],
            # Non-match
            [date(2000, 2, 1), 100, "Supermarket"],
            # Near match by amount
            [date(2000, 2, 14), 80, "Restaurant"],
            # Near match by date
            [date(2000, 2, 15), 66, "Florist"],
            # Activity group matches single transaction
            [date(2000, 4, 1), 1000, "Magic Show"],
            [date(2000, 4, 1), 2000, "Magic Show"],
            [date(2000, 4, 1), -3000, "Magic Show"],
            # Subset of activity group matches single transaction
            [date(2000, 6, 1), 4, "Pharmacy"],
            [date(2000, 6, 1), 15, "Pharmacy"],
            [date(2000, 6, 1), 40, "Pharmacy"],
        ]
    )

    def test_exact_matchmaker_initialization(self):
        mock_transactions = self.mock_transactions[:8]
        mock_data = self.mock_activity[:8]
        # Use the `ExactMatchmaker` to find exact matches
        expected_best_matches = {
            mock_transactions[0]: mock_data[0],
            mock_transactions[1]: mock_data[1],
            mock_transactions[3]: mock_data[3],
            mock_transactions[4]: mock_data[4],  # indeterminate; match based on order
            mock_transactions[5]: mock_data[6],  # indeterminate; match based on order
        }
        matchmaker = ExactMatchmaker(mock_transactions, mock_data)
        assert matchmaker.best_matches == expected_best_matches

    def test_near_matchmaker_initialization(self):
        mock_transactions = self.mock_transactions
        mock_data = self.mock_activity
        # Use the `NearMatchmaker` to find near matches
        # (near matches should include all exact matches for this test)
        expected_best_matches = {
            mock_transactions[0]: mock_data[0],
            mock_transactions[1]: mock_data[1],
            mock_transactions[3]: mock_data[3],
            mock_transactions[4]: mock_data[4],  # indeterminate; match based on order
            mock_transactions[5]: mock_data[6],  # indeterminate; match based on order
            mock_transactions[8]: mock_data[8],
            mock_transactions[7]: mock_data[9],
        }
        matchmaker = NearMatchmaker(mock_transactions, mock_data)
        assert matchmaker.best_matches == expected_best_matches

    def test_activity_matchmaker_initialization(self):
        mock_transactions = self.mock_transactions
        mock_data = self.mock_activity
        # Use the `ActivityMatchmaker` to find exact and near matches
        expected_best_matches = {
            mock_transactions[0]: mock_data[0],
            mock_transactions[1]: mock_data[1],
            mock_transactions[3]: mock_data[3],
            mock_transactions[4]: mock_data[4],  # indeterminate; match based on order
            mock_transactions[5]: mock_data[6],  # indeterminate; match based on order
            mock_transactions[8]: mock_data[8],
            mock_transactions[7]: mock_data[9],
            mock_transactions[9]: TransactionActivityGroup(mock_data[10:13]),
            mock_transactions[10]: TransactionActivityGroup(mock_data[13:15]),
        }
        expected_unmatched_transactions = [
            mock_transactions[2],
            mock_transactions[6],
        ]
        expected_unmatched_activities = [
            mock_data[2],
            mock_data[5],
            mock_data[7],
            mock_data[15],
        ]
        expected_match_discrepancies = {
            mock_transactions[8]: mock_data[8],
            # Date discrepancies are not considered notable and are excluded
        }
        matchmaker = ActivityMatchmaker(mock_transactions, mock_data)
        assert matchmaker.best_matches == expected_best_matches
        assert matchmaker.unmatched_transactions == expected_unmatched_transactions
        assert matchmaker.unmatched_activities == expected_unmatched_activities
        assert matchmaker.match_discrepancies == expected_match_discrepancies
