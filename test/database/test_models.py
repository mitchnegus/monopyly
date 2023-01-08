"""Tests for the database models."""
from datetime import date

import pytest

from monopyly.database.models import (
    Model, AuthorizedAccessMixin, User, Bank, BankAccountType, BankAccount,
    BankTransaction, BankSubtransaction, CreditAccount, CreditCard,
    CreditStatement, CreditTransaction, CreditSubtransaction, CreditTag
)


class TestModel:

    def assert_accurate_model_field_assignment(self, model_type, mapping):
        model = model_type(**mapping)
        for field in mapping:
            assert getattr(model, field) == mapping[field]


class TestUser(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "username": "test_user",
            "password": "something-secure",
        }
        self.assert_accurate_model_field_assignment(User, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "username": "test_user", "password": "something-secure"},
          "User(id=100, username='test_user', password='something-secure')"],
         [{"id": 100, "username": "test_user",
           "password": "something-else-more-secure"},
          "User(id=100, username='test_user', "
          "password='something-else-more-secur...')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        user = User(**mapping)
        assert repr(user) == expected_repr_string


class TestBank(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "user_id": 10,
            "bank_name": "New Bank",
        }
        self.assert_accurate_model_field_assignment(Bank, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "user_id": 10, "bank_name": "New Bank"},
          "Bank(id=100, user_id=10, bank_name='New Bank')"],
         [{"id": 100, "user_id": 10,
           "bank_name": "New Bank with a very long name"},
          "Bank(id=100, user_id=10, "
          "bank_name='New Bank with a very long...')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        user = Bank(**mapping)
        assert repr(user) == expected_repr_string


class TestBankAccountType(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "user_id": 10,
            "type_name": "New Bank Account Type",
            "type_abbreviation": "New BAT",
        }
        self.assert_accurate_model_field_assignment(BankAccountType, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "user_id": 10, "type_name": "New Bank Account Type",
           "type_abbreviation": "New BAT"},
          "BankAccountType(id=100, user_id=10, "
          "type_name='New Bank Account Type', type_abbreviation='New BAT')"],
         [{"id": 100, "user_id": 10,
           "type_name": "New Bank Account Type with a very long name",
           "type_abbreviation": "New BAT"},
          "BankAccountType(id=100, user_id=10, "
          "type_name='New Bank Account Type wit...', "
          "type_abbreviation='New BAT')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        account_type = BankAccountType(**mapping)
        assert repr(account_type) == expected_repr_string


class TestBankAcount(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "bank_id": 200,
            "account_type_id": 10,
            "last_four_digits": "####",
            "active": 1,
        }
        self.assert_accurate_model_field_assignment(BankAccount, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "bank_id": 200, "account_type_id": 10,
           "last_four_digits": "####", "active": 1},
          "BankAccount(id=100, bank_id=200, account_type_id=10, "
          "last_four_digits='####', active=1)"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        account = BankAccount(**mapping)
        assert repr(account) == expected_repr_string


class TestBankTransaction(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "internal_transaction_id": None,
            "account_id": 200,
            "transaction_date": date(2022, 11, 15),
        }
        self.assert_accurate_model_field_assignment(BankTransaction, mapping)
        assert BankTransaction.subtype == "bank"

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "internal_transaction_id": None, "account_id": 200,
           "transaction_date": date(2022, 11, 15)},
          "BankTransaction(id=100, internal_transaction_id=None, "
          "account_id=200, transaction_date='2022-11-15')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        transaction = BankTransaction(**mapping)
        assert repr(transaction) == expected_repr_string


class TestBankSubtransaction(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "transaction_id": 200,
            "subtotal": 300.00,
            "note": "New subtransaction",
        }
        self.assert_accurate_model_field_assignment(
            BankSubtransaction, mapping
        )

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "transaction_id": 200, "subtotal": 300.00,
           "note": "New subtransaction"},
          "BankSubtransaction(id=100, transaction_id=200, subtotal=300.0, "
          "note='New subtransaction')"],
         [{"id": 100, "transaction_id": 200, "subtotal": 300.00,
           "note": "New subtransaction with a very long note"},
          "BankSubtransaction(id=100, transaction_id=200, subtotal=300.0, "
          "note='New subtransaction with a...')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        subtransaction = BankSubtransaction(**mapping)
        assert repr(subtransaction) == expected_repr_string


class TestCreditAccount(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "bank_id": 200,
            "statement_issue_day": 28,
            "statement_due_day": 1,
        }
        self.assert_accurate_model_field_assignment(CreditAccount, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "bank_id": 200, "statement_issue_day": 28,
           "statement_due_day": 1},
          "CreditAccount(id=100, bank_id=200, statement_issue_day=28, "
          "statement_due_day=1)"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        account = CreditAccount(**mapping)
        assert repr(account) == expected_repr_string


class TestCreditCard(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "account_id": 200,
            "last_four_digits": "####",
            "active": 1,
        }
        self.assert_accurate_model_field_assignment(CreditCard, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "account_id": 200, "last_four_digits": "####",
           "active": 1},
          "CreditCard(id=100, account_id=200, last_four_digits='####', "
          "active=1)"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        card = CreditCard(**mapping)
        assert repr(card) == expected_repr_string


class TestCreditStatement(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "card_id": 200,
            "issue_date": date(2022, 11, 24),
            "due_date": date(2022, 12, 13),
        }
        self.assert_accurate_model_field_assignment(CreditStatement, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "card_id": 200, "issue_date": date(2022, 11, 24),
           "due_date": date(2022, 12, 13)},
          "CreditStatement(id=100, card_id=200, issue_date='2022-11-24', "
          "due_date='2022-12-13')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        statement = CreditStatement(**mapping)
        assert repr(statement) == expected_repr_string


class TestCreditTransaction(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "internal_transaction_id": None,
            "statement_id": 200,
            "transaction_date": date(2022, 11, 23),
            "vendor": "New vendor"
        }
        self.assert_accurate_model_field_assignment(CreditTransaction, mapping)
        assert CreditTransaction.subtype == "credit"

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "internal_transaction_id": None, "statement_id": 200,
           "transaction_date": date(2022, 11, 23), "vendor": "New vendor"},
          "CreditTransaction(id=100, internal_transaction_id=None, "
          "statement_id=200, transaction_date='2022-11-23', "
          "vendor='New vendor')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        transaction = CreditTransaction(**mapping)
        assert repr(transaction) == expected_repr_string


class TestCreditSubtransaction(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "transaction_id": 200,
            "subtotal": 300.00,
            "note": "New subtransaction",
        }
        self.assert_accurate_model_field_assignment(
            CreditSubtransaction, mapping
        )

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "transaction_id": 200, "subtotal": 300.00,
           "note": "New subtransaction"},
          "CreditSubtransaction(id=100, transaction_id=200, subtotal=300.0, "
          "note='New subtransaction')"],
         [{"id": 100, "transaction_id": 200, "subtotal": 300.00,
           "note": "New subtransaction with a very long note"},
          "CreditSubtransaction(id=100, transaction_id=200, subtotal=300.0, "
          "note='New subtransaction with a...')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        subtransaction = CreditSubtransaction(**mapping)
        assert repr(subtransaction) == expected_repr_string


class TestCreditTag(TestModel):

    def test_model_initialization(self):
        mapping = {
            "id": 100,
            "user_id": 10,
            "parent_id": None,
            "tag_name": "New tag",
        }
        self.assert_accurate_model_field_assignment(CreditTag, mapping)

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [[{"id": 100, "user_id": 10, "parent_id": None, "tag_name": "New tag"},
          "CreditTag(id=100, user_id=10, parent_id=None, tag_name='New tag')"]]
    )
    def test_model_representation(self, mapping, expected_repr_string):
        tag = CreditTag(**mapping)
        assert repr(tag) == expected_repr_string


class TestAlternateModels:

    def test_no_representation(self):
        # Define a generic class to test default string representations
        class GenericModel(Model):
            # Pass a valid table name
            __tablename__ = "users"
        # Test that the model's string representation is generic
        generic_model = GenericModel()
        assert str(generic_model)[0] == "<"
        assert str(generic_model)[-1] == ">"

    def test_invalid_authorized_model(self):
        # Define an "authorized access" class to test authorization
        class AuthorizedModel(AuthorizedAccessMixin, Model):
            # Pass a valid table name
            __tablename__ = "users"
        # Test that the model cannot make a selection based on the user
        authorized_model = AuthorizedModel()
        with pytest.raises(AttributeError):
            authorized_model.select_for_user()
