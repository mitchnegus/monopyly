"""Tests for the credit module managing transaction activity reconciliation."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

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
        [date(2020, 1, 1), 100, "description0"],
        [date(2020, 2, 1), 200, "description1"],
        [date(2020, 3, 1), 300, "description2"],
    ]

    def test_initialization(self):
        activities = TransactionActivities(self.test_data)
        for activity, row_data in zip(activities, self.test_data, strict=True):
            assert activity.transaction_date == row_data[0]
            assert activity.total == row_data[1]
            assert activity.description == row_data[2]

    def test_initialization_date_string(self):
        activities = TransactionActivities(
            [(str(_[0]), _[1], _[2]) for _ in self.test_data]
        )
        for activity, row_data in zip(activities, self.test_data, strict=True):
            assert activity.transaction_date == row_data[0]
            assert activity.total == row_data[1]
            assert activity.description == row_data[2]

    def test_initialization_invalid_date(self):
        with pytest.raises(ValueError):
            activities = TransactionActivities([["invalid", 100, "description0"]])

    def test_data_total(self):
        activities = TransactionActivities(self.test_data)
        assert activities.total == 600


class TestTransactionActivityGroup:
    test_data = [
        ["2020-04-01", 100, "description"],
        ["2020-04-01", 200, "description"],
        ["2020-04-01", 300, "description"],
        ["2020-05-05", 250, "description"],
        ["2020-04-01", 150, "other description"],
    ]
    activities = TransactionActivities(test_data)

    def test_initialization(self):
        transaction_activities = self.activities[:3]
        grouping = TransactionActivityGroup(transaction_activities)
        assert grouping.transaction_date == date(2020, 4, 1)
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


class TestActivityMatchFinders:
    mock_transaction = Mock(transaction_date=date(2000, 1, 1), total=50, notes="...")
    mock_small_total_transaction = Mock(
        transaction_date=date(2000, 2, 20), total=3, notes="..."
    )
    mock_refund_transaction = Mock(
        transaction_date=date(2000, 3, 30), total=-1, notes="..."
    )
    mock_activity = TransactionActivities(
        [
            [date(2000, 1, 1), 50, "Restaurant"],
            [date(2000, 1, 1), 51, "Restaurant"],  # ---- only near match
            [date(2000, 1, 2), 50, "Restaurant"],  # ---- only near match
            [date(2000, 1, 1), 40, "Restaurant"],  # ---- too low
            [date(2000, 1, 1), 60, "Restaurant"],  # ---- too high
            [date(1999, 12, 20), 50, "Restaurant"],  # -- too early date
            [date(2000, 1, 10), 50, "Restaurant"],  # --- too late date
            [date(2000, 1, 3), 50, "Restaurant"],  # ---- slightly late, but exact total
            [date(2000, 2, 20), 5, "Pharmacy"],  # ------ near (small value)
            [date(2000, 3, 30), 2, "Pharmacy"],  # ------ near, but wrong sign
        ]
    )

    def test_exact_match_finder_initialization(self):
        mock_data = self.mock_activity[:3]
        # Exact matches should have the same transaction date and total
        expected_matches = mock_data[:1]
        matches = ExactMatchFinder.find(self.mock_transaction, mock_data)
        assert matches == expected_matches

    def test_near_match_finder_initialization(self):
        mock_data = self.mock_activity
        # Near matches should have a date:
        #  - within 1 day or total within 10%
        #  - within 2 days or an exactly matching total
        expected_matches = mock_data[:3] + mock_data[7:8]
        matches = NearMatchFinder.find(self.mock_transaction, mock_data)
        assert matches == expected_matches

    def test_near_match_finder_close_total(self):
        mock_data = self.mock_activity
        # Near match should be close (absolutely) for low values
        expected_matches = [mock_data[8]]
        matches = NearMatchFinder.find(self.mock_small_total_transaction, mock_data)
        print(matches)
        print(expected_matches)
        assert matches == expected_matches

    def test_near_match_finder_close_total_wrong_sign(self):
        mock_data = self.mock_activity
        # Near match should be close (absolutely) for low values,
        # except when that changes the sign
        expected_matches = []
        matches = NearMatchFinder.find(self.mock_refund_transaction, mock_data)
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

    @pytest.mark.parametrize(
        "field, token_count",
        [
            ("Life is a Game", 4),
            ("life is a game", 4),
            ("Monopyly is a game", 4),
            ("Game", 1),
        ],
    )
    def test_matchmaker_tokenization(self, field, token_count):
        tokens = ActivityMatchmaker.tokenize(field)
        assert len(tokens) == token_count
        for token in tokens:
            assert token.lower() == token

    @pytest.mark.parametrize(
        "reference, test, score",
        [
            ("Life is a Game", "Life is a Game", 0),  # --- identical
            ("Life is a Game", "life is a game", 0),  # --- identical
            ("Monopyly is a game", "life is a game", 0.4),
            ("Game", "Life is a Game", 0.75),
            ("Other Test", "Life is a Game", 1),  # ------- entirely dissimilar
        ],
    )
    def test_matchmaker_scoring(self, reference, test, score):
        reference_tokens = ActivityMatchmaker.tokenize(reference)
        test_tokens = ActivityMatchmaker.tokenize(test)
        assert ActivityMatchmaker.score_tokens(reference_tokens, test_tokens) == score
