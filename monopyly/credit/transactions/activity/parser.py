"""Define a parser and associated functionality for reading activity data CSV files."""

import csv
from abc import ABC, abstractmethod
from pathlib import Path

from flask import abort, current_app

from ....common.utils import parse_date
from .data import ActivityLoadingError, TransactionActivities, TransactionActivityLoader

SUPPORTED_BANKS = ("Bank of America", "Chase", "Discover")


def parse_transaction_activity_file(transaction_file):
    """
    Parse a CSV file containing reported transaction activity.

    Parameters
    ----------
    activity_file : werkzeug.datastructures.FileStorage, pathlib.Path
        The file object containing transaction activity data or a path
        to a file containing transaction activity data.

    Returns
    -------
    activities : TransactionActivities
        The list-like object containing credit transaction activity
        data.
    """
    try:
        return _TransactionActivityParser(transaction_file).data
    except ActivityLoadingError:
        return None


class _ColumnIdentifier(ABC):
    """
    An object to aid in identifying the column matching a certain type.

    Parameters
    ----------
    raw_header : list
        The header row as a list of column titles.
    """

    def __init__(self, raw_header):
        self._raw_header = raw_header
        self._potential_column_indices = []

    def determine_index(self):
        """
        Given the data header, determine the current column type index.

        Returns
        -------
        index : int, None
            The index of the column corresponding to the current column
            type.
        """
        for column_index, column_title in enumerate(self._raw_header):
            standardized_title = column_title.strip().casefold()
            column_match = self.check(standardized_title)
            if column_match is True:
                return column_index
            elif column_match is None:
                self._potential_column_indices.append(column_index)
        return self._infer_column_index()

    @abstractmethod
    def check(self, standardized_title):
        raise NotImplementedError(
            "Define how a column identification check is performed in a subclass. "
            "A check should return `True` if the title does describe the class's "
            "column type, `False` if the title does *not* describe the class's column "
            "type, and `None` if the title may describe the column type but more "
            "information is required."
        )

    def _infer_column_index(self):
        # Attempt to infer the current column type index from a potential match
        if len(self._potential_column_indices) == 1:
            return self._potential_column_indices[0]
        return None


class _TransactionDateColumnIdentifier(_ColumnIdentifier):
    def check(self, standardized_title):
        """Check if the title indicates this column contains a transaction date."""
        if standardized_title == "transaction date":
            return True
        elif "date" in standardized_title.split():
            if "trans." in standardized_title:
                return True
            elif standardized_title == "date" or standardized_title == "posted date":
                return None
        return False


class _TransactionTotalColumnIdentifier(_ColumnIdentifier):
    def check(self, standardized_title):
        """Check if the title indicates this column contains an amount."""
        return standardized_title in ("amount", "total")


class _TransactionDescriptionColumnIdentifier(_ColumnIdentifier):
    def check(self, standardized_title):
        """Check if the title indicates this column contains a description (payee)."""
        return standardized_title in ("description", "desc.", "payee")


class _TransactionCategoryColumnIdentifier(_ColumnIdentifier):
    def check(self, standardized_title):
        """Check if the title indicates this column contains a category."""
        return standardized_title == "category"


class _TransactionTypeColumnIdentifier(_ColumnIdentifier):
    def check(self, standardized_title):
        """Check if the title indicates this column contains a transaction type."""
        return standardized_title == "type"


class _TransactionActivityParser:
    """
    A parser for arbitrary CSV files containing transaction activity.

    This object contains logic and utilities for parsing aribtrary CSV
    files containing transaction activity data. It is generalized to
    work with various CSV labeling schemes, inferring information about
    the CSV data from the contents of the file.

    Parameters
    ----------
    activity_file : werkzeug.datastructures.FileStorage, pathlib.Path
        The file object containing transaction activity data or a path
        to a file containing transaction activity data.
    activity_dir : pathlib.Path
        The path to the directory where activity files to be parsed will
        be stored after uploading.
    """

    _column_identifiers = {
        "transaction_date": _TransactionDateColumnIdentifier,
        "total": _TransactionTotalColumnIdentifier,
        "description": _TransactionDescriptionColumnIdentifier,
        "category": _TransactionCategoryColumnIdentifier,
        "type": _TransactionTypeColumnIdentifier,
    }
    _raw_column_types = list(_column_identifiers.keys())
    column_types = _raw_column_types[:3]

    def __init__(self, activity_file, activity_dir=None):
        file_loader = TransactionActivityLoader(activity_dir=activity_dir)
        if isinstance(activity_file, Path):
            activity_filepath = activity_file
        else:
            activity_filepath = file_loader.upload(activity_file)
        # Load data from the activity file
        raw_header, raw_data = self._load_data(activity_filepath)
        if not raw_data:
            raise ActivityLoadingError("The activity file contains no actionable data.")
        # Parse the loaded activity data
        self._raw_column_indices = self._determine_column_indices(raw_header)
        self._negative_charges = self._determine_expenditure_sign(raw_data)
        self.column_indices = {name: i for i, name in enumerate(self.column_types)}
        self.data = TransactionActivities(self._process_data(row) for row in raw_data)
        # Remove the loaded activity file
        file_loader.cleanup()

    @staticmethod
    def _load_data(transaction_filepath):
        # Load raw header information and data from the transaction file
        with transaction_filepath.open() as csv_file:
            csv_reader = csv.reader(csv_file)
            raw_header = next(csv_reader)
            raw_data = list(csv_reader)
        return raw_header, raw_data

    def _determine_column_indices(self, raw_header):
        # Determine the indices of various columns in the raw header/data
        raw_column_indices = {
            column_type: identifier(raw_header).determine_index()
            for column_type, identifier in self._column_identifiers.items()
        }
        for column_type in self.column_types:
            if raw_column_indices[column_type] is None:
                current_app.logger.debug(
                    f"The '{column_type}' column could not be identified in the data. "
                )
                msg = (
                    "The data was unable to be parsed, most likely because it did not "
                    "match a recognized format. Supported data formats include those "
                    f"from the following banks: {', '.join(SUPPORTED_BANKS)}."
                )
                abort(400, msg)
        return raw_column_indices

    def _determine_expenditure_sign(self, raw_data):
        # Determine the sign of expenditures
        # - Charges may be reported as either positive or negative amounts
        # - Negatively valued charges (positively valued payments) return `True`;
        #   positively valued charges (negatively valued payments) return `False`
        # Note: This method assumes that an activity file will not report a standard
        #       transaction as a "payment"
        contextual_column_types = ("category", "description", "type")
        contextual_column_indices = [
            index
            for column_type, index in self._raw_column_indices.items()
            if column_type in contextual_column_types and index is not None
        ]

        def _infer_payment_row(row):
            # Infer whether the row constitutes a payment transaction
            contextual_info = [row[i].lower() for i in contextual_column_indices]
            return any("payment" in element for element in contextual_info)

        payment_rows = list(filter(_infer_payment_row, raw_data))
        return self._extrapolate_payments_positive(payment_rows, raw_data)

    def _extrapolate_payments_positive(self, payment_rows, raw_data):
        if payment_rows:
            payments_positive = self._evaluate_payment_signs(payment_rows)
        else:
            payments_positive = self._evaluate_nonpayment_signs(raw_data)
        if payments_positive is None:
            raise RuntimeError(
                "The sign of credits/debits could not be determined from the data."
            )
        return payments_positive

    def _evaluate_payment_signs(self, payment_rows):
        # Iterate over each payment row and collect sign information
        amount_index = self._raw_column_indices["total"]
        payment_signs_positive = [float(row[amount_index]) > 0 for row in payment_rows]
        # Evaluate whether payment amounts are treated as positively valued
        if all(payment_signs_positive):
            payments_positive = True
        elif not any(payment_signs_positive):
            payments_positive = False
        else:
            payments_positive = None
        return payments_positive

    def _evaluate_nonpayment_signs(self, nonpayment_rows):
        # Iterate over each non-payment and collect sign information
        # - Assume the majority of transactions are charges if no payments are found
        amount_index = self._raw_column_indices["total"]
        negative_charge_count = sum(
            float(row[amount_index]) < 0 for row in nonpayment_rows
        )
        # Evaluate whether assumed non-payment amounts seem positively valued
        negative_charge_frac = negative_charge_count / len(nonpayment_rows)
        if negative_charge_frac == 0.5:
            payments_positive = None
        else:
            # Payments are assumed to be positive if most of the transactions are
            # charges and most of the charges are negative
            payments_positive = negative_charge_frac > 0.5
        return payments_positive

    def _process_data(self, row):
        # Process the raw data into an output format
        processed_row = []
        for column_type in self.column_types:
            value = row[self._raw_column_indices[column_type]]
            if column_type == "transaction_date":
                value = self._process_date_data(value)
            elif column_type == "total":
                value = self._process_amount_data(value)
            processed_row.append(value)
        return processed_row

    def _process_amount_data(self, value):
        # Charges should be positively valued, payments negatively valued
        value = float(value)
        return -value if self._negative_charges else value

    def _process_date_data(self, value):
        # Output dates as `datetime.date` objects
        return parse_date(value)
