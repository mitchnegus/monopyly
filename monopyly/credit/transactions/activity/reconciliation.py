"""
Tools for reconciling credit transactions with associated activity data.
"""

from abc import ABC, abstractmethod
from collections import UserDict
from datetime import timedelta
from itertools import chain, combinations

from nltk import wordpunct_tokenize
from nltk.metrics.distance import jaccard_distance

from .data import TransactionActivityGroup


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

    class _BestMatches(UserDict):
        """A dictionary with custom methods for querying membership."""

        def includes_transaction(self, transaction):
            return transaction in self.keys()

        def includes_activity(self, activity):
            for value in self.values():
                same_activity = activity == value
                same_group = (
                    isinstance(value, TransactionActivityGroup) and activity in value
                )
                if same_activity or same_group:
                    return True
            return False

        def pair(self, transaction, activity):
            """Assign the transaction-activity pair to be a "best match"."""
            self[transaction] = activity

    def __init__(self, transactions, activities, best_matches=None):
        self._transactions = transactions
        self._activities = activities
        self.best_matches = self._BestMatches(best_matches if best_matches else {})

    @property
    def unmatched_transactions(self):
        return list(filter(self._is_unmatched_transaction, self._transactions))

    @property
    def unmatched_activities(self):
        return list(filter(self._is_unmatched_activity, self._activities))

    @property
    def match_discrepancies(self):
        def _match_has_discrepancy(item):
            transaction, activity = item
            return transaction.total != activity.total

        return dict(filter(_match_has_discrepancy, self.best_matches.items()))

    def _is_unmatched_transaction(self, transaction):
        """Check whether the given transaction is not yet matched."""
        return not self.best_matches.includes_transaction(transaction)

    def _is_unmatched_activity(self, activity):
        """Check whether the given activity is not yet matched."""
        return not self.best_matches.includes_activity(activity)

    def _get_potential_matches(self, matches):
        """Get the set of potential valid matches from the set of matches."""
        # Potential matches are only those where the transaction is unmatched
        for transaction in filter(self._is_unmatched_transaction, matches):
            activities = matches[transaction]
            # Potential matches are only those where activities are unmatched
            potential_activities = sorted(
                set(activities) - set(self.best_matches.values())
            )
            if potential_activities:
                yield transaction, potential_activities

    def _assign_unambiguous_best_matches(self, matches):
        """Find unambiguous matches and assign them as the "best" matches."""
        for transaction, activities in self._get_potential_matches(matches):
            # Check that this transaction only matches one activity
            if len(activities) == 1:
                activity = activities[0]
                if self._is_unambiguous_match(transaction, activity, matches):
                    self.best_matches.pair(transaction, activity)

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
            self.best_matches.pair(transaction, activity)

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
        replacements = [
            # Remove disruptive punctuation
            ("1-800", "1800"),
            ("-", " "),
            (".", " "),
            (",", " "),
            ("(", " "),
            (")", " "),
            ("'", ""),
            # Standardize characters
            ("&", "and"),
            ("é", "e"),
        ]
        for original, replacement in replacements:
            field = field.replace(original, replacement)
        tokens = set(wordpunct_tokenize(field.replace("'", "").casefold()))
        removals = ["and", "the", "of"]
        for word in removals:
            tokens.discard(word)
        return tokens

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
    unmatched_transactions : list
        An list of transactions where no matching activity could be
        identified.
    unmatched_activities : list
        An list of activities where no matching transaction could be
        identified.
    """

    _match_finder = ExactMatchFinder

    def __init__(self, transactions, activities, best_matches=None):
        super().__init__(transactions, activities, best_matches=best_matches)
        matches = {
            transaction: self._match_finder.find(transaction, activities)
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
    unmatched_transactions : list
        An list of transactions where no matching activity could be
        identified.
    unmatched_activities : list
        An list of activities where no matching transaction could be
        identified.
    """

    _match_finder = NearMatchFinder

    def __init__(self, transactions, activities, best_matches=None):
        super().__init__(transactions, activities, best_matches=best_matches)
        matches = {
            transaction: self._match_finder.find(transaction, activities)
            for transaction in transactions
        }
        self._assign_unambiguous_best_matches(matches)
        self._disambiguate_best_matches(matches)


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

    def __init__(self, transactions, activities, best_matches=None):
        # Collect all "exact" matches (same date and amount), then near matches
        for matchmaker_cls in (ExactMatchmaker, NearMatchmaker):
            matchmaker = matchmaker_cls(transactions, activities, best_matches)
            best_matches = matchmaker.best_matches
        super().__init__(transactions, activities, best_matches=best_matches)
        # Find further matches between transactions and groups of activity information
        for transaction in self.unmatched_transactions:
            self._match_activity_groups(transaction, activities)

    def _match_activity_groups(self, transaction, activities):
        """Match transaction to groups of activity with the same total and merchant."""
        potential_activity_groups = self._gather_potential_activity_groups(
            transaction.transaction_date
        )
        for group in potential_activity_groups:
            for group_subset in self._get_group_subsets(group):
                if (
                    sum(activity.total for activity in group_subset)
                    == transaction.total
                ):
                    self.best_matches.pair(
                        transaction, TransactionActivityGroup(group_subset)
                    )
                    break

    def _gather_potential_activity_groups(self, transaction_date):
        # Group activities on the transaction date by shared descriptions
        date_activities = self._group_activities_for_date(transaction_date)
        potential_activity_groups = {}
        for activity in date_activities:
            if activity.description in potential_activity_groups:
                potential_activity_groups[activity.description].append(activity)
            else:
                potential_activity_groups[activity.description] = [activity]
        # Only return the groups with multiple potential activities
        return filter(lambda group: len(group) != 1, potential_activity_groups.values())

    def _group_activities_for_date(self, transaction_date):
        # Provide a list of activities that share a transaction date
        return [
            activity
            for activity in self.unmatched_activities
            if activity.transaction_date == transaction_date
        ]

    def _get_group_subsets(self, group):
        # Return combinations of activities that represent a subset of the full group
        return chain.from_iterable(
            combinations(group, r=r) for r in range(len(group), 0, -1)
        )
