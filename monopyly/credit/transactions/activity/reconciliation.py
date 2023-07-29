"""
Tools for reconciling credit transactions with associated activity data.
"""

from abc import ABC, abstractmethod
from datetime import timedelta

from nltk import wordpunct_tokenize
from nltk.metrics.distance import jaccard_distance


class MatchFinder(ABC):
    """An abstract base class for finding transaction-activity matches."""

    @classmethod
    def find(cls, transaction, data):
        """
        Find potential matches for the transaction in the data.

        Parameters
        ----------
        transaction : CreditTransactionView
            The transaction to use when finding potential matches.
        data : TransactionActivities
            The data to search for potential matches.

        Returns
        -------
        matches : list
            The full set of activities that may match this finder's
            transaction.
        """
        matches = [row for row in data if cls.is_match(transaction, row)]
        return matches

    @abstractmethod
    def is_match(cls, transaction, activity):
        raise NotImplementedError("Define what constitutes a match in a subclass.")


class ExactMatchFinder(MatchFinder):
    """
    An object for finding "exact" transaction-activity matches.

    Notes
    -----
    An "exact" match is a transaction and activity that share the same
    transaction date and same transaction total/amount.
    """

    @classmethod
    def is_match(cls, transaction, activity):
        """Evaluate whether the activity is an "exact" match."""
        same_date = transaction.transaction_date == activity.transaction_date
        same_amount = transaction.total == activity.total
        return same_date and same_amount


class NearMatchFinder(MatchFinder):
    """
    An object for finding "near" transaction-activity matches.

    Notes
    -----
    A "near" match is a transaction and activity that are within some
    acceptable range (e.g., the activity date is within a similar time
    frame as the transaction date, and the activity transaction amount
    is comparable to the recorded transaction total). Specifically,
    transactions are considered a near match if they are within 1 day
    of each other and the transaction total is no more than $3.00 or 10%
    larger (whichever is greater) than the reported activity amount, or
    they have the same transaction total but occur within two days of
    each other.
    """

    @classmethod
    def is_match(cls, transaction, activity):
        """Evaluate whether the activity is a "near" match."""
        near_date = cls._is_near_date(transaction, activity)
        near_amount = cls._is_near_amount(transaction, activity)
        less_near_date = cls._is_near_date(transaction, activity, proximity_days=2)
        exact_amount = transaction.total == activity.total
        return (near_date and near_amount) or (less_near_date and exact_amount)

    @classmethod
    def _is_near_date(cls, transaction, activity, proximity_days=1):
        low_date = activity.transaction_date - timedelta(days=proximity_days)
        high_date = activity.transaction_date + timedelta(days=proximity_days)
        return low_date <= transaction.transaction_date <= high_date

    @classmethod
    def _is_near_amount(cls, transaction, activity):
        # Ensure that the low amount is fixed at zero for small magnitudes
        sign = 1 if activity.total >= 0 else -1
        total_magnitude = abs(activity.total)
        low_amount = sign * min(max(0, total_magnitude - 3), total_magnitude * 0.9)
        high_amount = sign * max(total_magnitude + 3, total_magnitude * 1.1)
        return low_amount <= transaction.total <= high_amount


class _Matchmaker(ABC):
    """An abstract base class for defining matchmaker objects."""

    def __init__(self, transactions, data, best_matches=None):
        self.best_matches = best_matches if best_matches else {}

    @property
    def match_discrepancies(self):
        def _match_has_discrepancy(item):
            transaction, activity = item
            return transaction.total != activity.total

        return dict(filter(_match_has_discrepancy, self.best_matches.items()))

    def _assign_best_match(self, transaction, activity):
        """Assign the transaction-activity pair to be a "best match"."""
        self.best_matches[transaction] = activity

    def _assign_unambiguous_best_matches(self, matches):
        """Find unambiguous matches and assign them as the "best" matches."""
        for transaction, activities in self._get_potential_matches(matches):
            # Check that this transaction only matches one activity
            if len(activities) == 1:
                activity = activities[0]
                if self._is_unambiguous_match(transaction, activity, matches):
                    self._assign_best_match(transaction, activity)

    def _is_unambiguous_match(self, transaction, activity, matches):
        """Check whether the transaction and activity match unambiguously."""
        other_transactions_activities = filter(
            lambda item: item[0] is not transaction,
            self._get_potential_matches(matches),
        )
        for _, other_activities in other_transactions_activities:
            if activity in other_activities:
                return False
        return True

    def _disambiguate_best_matches(self, matches):
        """Disambiguate the best matches from sets of potential matches."""
        ambiguous_matches = self._get_potential_matches(matches)
        for transaction, activities in ambiguous_matches:
            activity = self._choose_best_ambiguous_match(transaction, activities)
            self._assign_best_match(transaction, activity)

    def _choose_best_ambiguous_match(self, transaction, activities):
        """Determine a transaction-activity match from an ambiuguous set."""
        # Score each activity based on its similarity to the transaction
        merchant_tokens = self.tokenize(transaction.merchant)
        notes_tokens = self.tokenize(transaction.notes)
        score_records = []
        for activity in activities:
            activity_tokens = self.tokenize(activity.description)
            score = self._compute_transaction_activity_similarity_score(
                merchant_tokens, notes_tokens, activity_tokens
            )
            score_records.append((score, activity))
        # The activity with the lowest score is chosen as the best match
        best_match = min(score_records)[1]
        return best_match

    @staticmethod
    def tokenize(field):
        """
        Convert text in a field into tokens.

        Given a string of text, convert the text into tokens via the
        NLTK regex tokenizer. Before tokenization, standardize inputs
        by removing all apostrophes (which are uncommon in credit
        activity listings) and by computing the casefold of the input.

        Parameters
        ----------
        field : str
            The string of text to be tokenized.
        """
        return set(wordpunct_tokenize(field.replace("'", "").casefold()))

    def _compute_transaction_activity_similarity_score(
        self, merchant_tokens, notes_tokens, activity_tokens
    ):
        """
        Use tokens for the transaction and activity to compute a score.

        Evaluate the similarity of a transaction and activity by
        scoring the distances between tokenized representations of the
        fields. The primary scoring metric is the similarity between the
        transaction merchant and activity description, but ties are
        broken by a secondary metric comparing the similarity between
        the transaction notes and activity description.
        """
        merchant_score = self.score_tokens(merchant_tokens, activity_tokens)
        notes_score = self.score_tokens(notes_tokens, activity_tokens)
        return merchant_score, notes_score

    @staticmethod
    def score_tokens(reference, test):
        """Use the Jaccard distance to measure the similarity of token sets."""
        return jaccard_distance(reference, test)

    def _get_potential_matches(self, matches):
        """Get the set of potential valid matches from the set of matches."""
        # Potential matches are only those where the transaction is unmatched
        for transaction in filter(self._is_unmatched, matches):
            activities = matches[transaction]
            # Potential matches are only those where activities are unmatched
            potential_activities = sorted(
                set(activities) - set(self.best_matches.values())
            )
            if potential_activities:
                yield transaction, potential_activities

    def _is_unmatched(self, transaction):
        """Check whether the given transaction is not yet matched."""
        return transaction not in self.best_matches


class ExactMatchmaker(_Matchmaker):
    """
    An object to find exact matches between transactions and activity data.

    Given a set of database credit transactions and a dataset of
    recorded activity data, this object traverses the two sets of
    information and determines which transactions appear to exactly
    match which activities.

    The object's search takes an iterative approach. It first finds all
    "exact" matches (those with the same data and same total/amount).
    Then, if there are ambiguities in this information, the procedure
    attempts to compare merchant and note information from the
    transaction with the description of the activity to make a
    determination.

    Parameters
    ----------
    transactions : list
        A list of transactions to be matched with the activities.
    activities : TransactionActivities
        A list-like collection of activity data to be matched with
        transactions.
    best_matches : dict
        A mapping between any transactions and the activity believed to
        represent the best match in the data.

    Attributes
    ----------
    best_matches : dict
        A mapping between transactions and their best match (as
        determined by the matcher's algorithm).
    """

    _match_finder = ExactMatchFinder

    def __init__(self, transactions, data, best_matches=None):
        super().__init__(transactions, data, best_matches=best_matches)
        matches = {
            transaction: self._match_finder.find(transaction, data)
            for transaction in transactions
        }
        self._assign_unambiguous_best_matches(matches)
        self._disambiguate_best_matches(matches)


class NearMatchmaker(_Matchmaker):
    """
    An object to find near matches between transactions and activity data.

    Given a set of database credit transactions and a dataset of
    recorded activity data, this object traverses the two sets of
    information and determines which transactions appear to nearly
    match which activities.

    The object's search takes an iterative approach. It first finds all
    "near" matches (those activities with transaction dates within a
    short window around the target transaction and amounts comparable to
    the target total). Then, if there are ambiguities in this
    information, the procedure attempts to compare merchant and note
    information from the transaction with the description of the
    activity to make a determination.

    Parameters
    ----------
    transactions : list
        A list of transactions to be matched with the activities.
    activities : TransactionActivities
        A list-like collection of activity data to be matched with
        transactions.
    best_matches : dict
        A mapping between any transactions and the activity believed to
        represent the best match in the data.

    Attributes
    ----------
    best_matches : dict
        A mapping between transactions and their best match (as
        determined by the matcher's algorithm).
    """

    _match_finder = NearMatchFinder

    def __init__(self, transactions, data, best_matches=None):
        super().__init__(transactions, data, best_matches=best_matches)
        matches = {
            transaction: self._match_finder.find(transaction, data)
            for transaction in transactions
        }
        self._assign_unambiguous_best_matches(matches)
        self._disambiguate_best_matches(matches)

    def _assign_best_match(self, transaction, activity):
        """Assign the transaction-activity pair to be a "best match"."""
        self.best_matches[transaction] = activity


class ActivityMatchmaker(_Matchmaker):
    """
    An object to find matches between transactions and activity data.

    Given a set of database credit transactions and a dataset of
    recorded activity data, this object traverses the two sets of
    information and determines which transactions match which
    activities.

    The object's search takes an iterative approach. First, it finds all
    "exact" matches (those with the same data and same total/amount). If
    there are ambiguities in this information, the procedure attempts to
    compare merchant and note information from the transaction with
    the description of the activity to make a determination.

    If that first attempt fails to match transactions exactly, a second
    pass of the data occurs to find "near" matches (those activities
    with transaction dates within a short window around the target
    transaction and amounts comparable to the target total). Again,
    the procedure attempts to resolve ambiguities by falling back to
    the contextual textual data.

    Parameters
    ----------
    transactions : list
        A list of transactions to be matched with the activities.
    activities : TransactionActivities
        A list-like collection of activity data to be matched with
        transactions.
    best_matches : dict
        A mapping between any transactions and the activity believed to
        represent the best match in the data.

    Attributes
    ----------
    best_matches : dict
        A mapping between transactions and their best match (as
        determined by the matcher's algorithm).
    match_discrepancies : dict
        A mapping between only transactions and their best match
        activity that are not considered "exact" matches (e.g., they do
        not share the same transaction date and same amount).
        This dictionary will be subset of the `best_matches` dictionary.
    unmatched_transactions : list
        A list of transactions where no matching activity could be
        identified.
    unmatched_activities : list
        A list of activities where no matching transaction could be
        identified.
    """

    def __init__(self, transactions, data, best_matches=None):
        # Collect all "exact" matches (same date and amount), then near matches
        for matchmaker in (ExactMatchmaker, NearMatchmaker):
            best_matches = matchmaker(transactions, data, best_matches).best_matches
        super().__init__(transactions, data, best_matches=best_matches)
        # Store references to unmatched transactions and activities
        self.unmatched_transactions = list(filter(self._is_unmatched, transactions))
        self.unmatched_activities = [
            activity for activity in data if activity not in self.best_matches.values()
        ]
