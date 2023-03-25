from datetime import date

from flask import g
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Table, select
from sqlalchemy.orm import (
    DeclarativeBase,
    declared_attr,
    relationship,
    with_loader_criteria,
)


class Model(DeclarativeBase):
    """A declarative base for all models."""

    def _format_repr_attr(self, name):
        value = getattr(self, name)
        value_str = f"{value}"
        # Abbreviate the string if it is longer than a set length
        abbrev_len = 25
        if len(value_str) > abbrev_len:
            value_str = f"{value_str[:abbrev_len]}..."
        if type(value) in (str, date):
            value_str = f"'{value_str}'"
        return f"{name}={value_str}"

    def __repr__(self):
        repr_attributes = self.__table__.columns.keys()
        pairs = [self._format_repr_attr(_) for _ in repr_attributes]
        attributes_str = ", ".join(pairs)
        return f"{self.__class__.__name__}({attributes_str})"


class AuthorizedAccessMixin:
    """A mixin class to facilitate making user-restricted queries."""

    _user_id_join_chain = ()
    _alt_authorized_ids = ()

    @declared_attr.directive
    @classmethod
    def user_id_model(cls):
        if cls._user_id_join_chain:
            return cls._user_id_join_chain[-1]
        return cls

    @declared_attr.directive
    @classmethod
    def _authorizing_criteria(cls):
        try:
            user_id_field = cls.user_id_model.user_id
        except AttributeError:
            msg = (
                "An authorized access model must either contain a direct "
                "reference to the user ID or specify a chain of joins to a "
                "table where the user ID can be verified."
            )
            raise AttributeError(msg)
        return user_id_field.in_(cls.authorized_ids)

    @declared_attr.directive
    @classmethod
    def authorized_ids(cls):
        # Add any extra IDs specified (e.g., user ID 0 for common entries)
        return (g.user.id, *cls._alt_authorized_ids)

    @classmethod
    def select_for_user(cls, *args, guaranteed_joins=(), **kwargs):
        """
        Build a select query restricting results to only an authorized user.

        Parameters
        ----------
        *args :
            The arguments to pass to the `sqlalchemy.select` function.
            If no arguments are given, the query selects the
        guaranteed_joins : tuple
            Database models (and by extension, their tables) that are
            not included in this model's "user ID join chain" but which
            should be added to this specific user-authorized join.
        **kwargs :
            The keyword arguments to pass to the `sqlalchemy.select`
            function.

        Returns
        -------
        query : sqlalchemy.sql.selectable.Select
            A statement representing the select query to make against
            the database.
        """
        if args:
            query = select(*args, **kwargs)
        else:
            query = select(cls, **kwargs)
        query = cls._join_user(query)
        for target in guaranteed_joins:
            if target not in cls._user_id_join_chain:
                query = query.join(target)
        return query.where(cls._authorizing_criteria)

    @classmethod
    def _join_user(cls, query):
        """Perform joins necessary to link the current model to a `User`."""
        from_arg = cls
        for join_model in cls._user_id_join_chain:
            # Specify left ("from") and right ("target") sides of joins exactly
            target_arg = join_model
            query = query.join_from(from_arg, target_arg)
            from_arg = target_arg
        return query


class User(Model):
    __tablename__ = "users"
    # Columns
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    # Relationships
    banks = relationship(
        "Bank",
        back_populates="user",
        cascade="all, delete",
    )
    bank_account_types = relationship(
        "BankAccountTypeView",
        viewonly=True,
        back_populates="user",
    )


class Bank(AuthorizedAccessMixin, Model):
    __tablename__ = "banks"
    # Columns
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    # Relationships
    user = relationship("User", back_populates="banks")
    bank_accounts = relationship(
        "BankAccountView",
        viewonly=True,
        back_populates="bank",
    )
    credit_accounts = relationship(
        "CreditAccount",
        back_populates="bank",
        cascade="all, delete",
    )


class BankAccountType(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_account_types"
    _alt_authorized_ids = (0,)
    # Columns
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type_name = Column(String, nullable=False)
    type_abbreviation = Column(String)
    # Relationships
    view = relationship(
        "BankAccountTypeView",
        viewonly=True,
        back_populates="account_type",
        uselist=False,
    )


class BankAccountTypeView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_account_types_view"
    _alt_authorized_ids = (0,)
    # Columns
    id = Column(Integer, ForeignKey("bank_account_types.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type_name = Column(String, nullable=False)
    type_abbreviation = Column(String)
    type_common_name = Column(String, nullable=False)
    # Relationships
    account_type = relationship(
        "BankAccountType",
        back_populates="view",
    )
    user = relationship("User", back_populates="bank_account_types")
    accounts = relationship(
        "BankAccountView",
        viewonly=True,
        back_populates="account_type",
    )


class BankAccount(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_accounts"
    _user_id_join_chain = (Bank,)
    # Columns
    id = Column(Integer, primary_key=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    account_type_id = Column(
        Integer,
        ForeignKey("bank_account_types_view.id"),
        nullable=False,
    )
    last_four_digits = Column(String, nullable=False)
    active = Column(Integer, nullable=False)
    # Relationships
    view = relationship(
        "BankAccountView",
        viewonly=True,
        back_populates="account",
        uselist=False,
    )


class BankAccountView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_accounts_view"
    _user_id_join_chain = (Bank,)
    # Columns
    id = Column(Integer, ForeignKey("bank_accounts.id"), primary_key=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    account_type_id = Column(
        Integer,
        ForeignKey("bank_account_types_view.id"),
        nullable=False,
    )
    last_four_digits = Column(String, nullable=False)
    active = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False)
    # Relationships
    account = relationship("BankAccount", back_populates="view")
    bank = relationship("Bank", back_populates="bank_accounts")
    account_type = relationship(
        "BankAccountTypeView",
        viewonly=True,
        back_populates="accounts",
    )
    transactions = relationship(
        "BankTransactionView", viewonly=True, back_populates="account"
    )


class BankTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions"
    _user_id_join_chain = (BankAccountView, Bank)
    # Denote the transaction subtype
    subtype = "bank"
    # Columns
    id = Column(Integer, primary_key=True)
    internal_transaction_id = Column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    account_id = Column(
        Integer,
        ForeignKey("bank_accounts_view.id"),
        nullable=False,
    )
    transaction_date = Column(Date, nullable=False)
    merchant = Column(String)
    # ((Should have optional merchant field?))
    #  Relationships
    view = relationship(
        "BankTransactionView",
        viewonly=True,
        back_populates="transaction",
        uselist=False,
    )


class BankTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions_view"
    _user_id_join_chain = (BankAccountView, Bank)
    # Denote the transaction subtype
    subtype = "bank"
    # Columns
    id = Column(Integer, ForeignKey("bank_transactions.id"), primary_key=True)
    internal_transaction_id = Column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    account_id = Column(
        Integer,
        ForeignKey("bank_accounts_view.id"),
        nullable=False,
    )
    transaction_date = Column(Date, nullable=False)
    merchant = Column(String)
    total = Column(Float)
    notes = Column(String)
    balance = Column(Float)
    # ((Should have optional merchant field?))
    # Relationships
    transaction = relationship(
        "BankTransaction",
        back_populates="view",
    )
    internal_transaction = relationship(
        "InternalTransaction", back_populates="bank_transactions"
    )
    account = relationship("BankAccountView", back_populates="transactions")
    subtransactions = relationship(
        "BankSubtransaction",
        back_populates="transaction",
    )


class BankSubtransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_subtransactions"
    _user_id_join_chain = (BankTransactionView, BankAccountView, Bank)
    # Columns
    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer,
        ForeignKey("bank_transactions_view.id"),
        nullable=False,
    )
    subtotal = Column(Float, nullable=False)
    note = Column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "BankTransactionView",
        viewonly=True,
        back_populates="subtransactions",
    )


class CreditAccount(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_accounts"
    _user_id_join_chain = (Bank,)
    # Columns
    id = Column(Integer, primary_key=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    statement_issue_day = Column(Integer, nullable=False)
    statement_due_day = Column(Integer, nullable=False)
    # ((Should probably have an 'active' field))
    # Relationships
    bank = relationship("Bank", back_populates="credit_accounts")
    cards = relationship(
        "CreditCard",
        back_populates="account",
        cascade="all, delete",
    )


class CreditCard(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_cards"
    _user_id_join_chain = (CreditAccount, Bank)
    # Columns
    id = Column(Integer, primary_key=True)
    account_id = Column(
        Integer,
        ForeignKey("credit_accounts.id"),
        nullable=False,
    )
    last_four_digits = Column(String, nullable=False)
    active = Column(Integer, nullable=False)
    # Relationships
    account = relationship("CreditAccount", back_populates="cards")
    statements = relationship(
        "CreditStatementView",
        viewonly=True,
        back_populates="card",
    )


class CreditStatement(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_statements"
    _user_id_join_chain = (CreditCard, CreditAccount, Bank)
    # Columns
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    # Relationship
    view = relationship(
        "CreditStatementView",
        viewonly=True,
        back_populates="statement",
        uselist=False,
    )


class CreditStatementView(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_statements_view"
    _user_id_join_chain = (CreditCard, CreditAccount, Bank)
    # Columns
    id = Column(Integer, ForeignKey("credit_statements.id"), primary_key=True)
    card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    balance = Column(Float, nullable=False)
    payment_date = Column(Date)
    # Relationships
    statement = relationship(
        "CreditStatement",
        back_populates="view",
    )
    card = relationship("CreditCard", back_populates="statements")
    transactions = relationship(
        "CreditTransactionView", viewonly=True, back_populates="statement"
    )


class CreditTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions"
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount, Bank)
    # Denote the transaction subtype
    subtype = "credit"
    # Columns
    id = Column(Integer, primary_key=True)
    internal_transaction_id = Column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    statement_id = Column(
        Integer,
        ForeignKey("credit_statements_view.id"),
        nullable=False,
    )
    transaction_date = Column(Date, nullable=False)
    merchant = Column(String, nullable=False)
    # Relationships
    view = relationship(
        "CreditTransactionView",
        viewonly=True,
        back_populates="transaction",
        uselist=False,
    )


class CreditTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions_view"
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount, Bank)
    # Denote the transaction subtype
    subtype = "credit"
    # Columns
    id = Column(
        Integer,
        ForeignKey("credit_transactions.id"),
        primary_key=True,
    )
    internal_transaction_id = Column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    statement_id = Column(
        Integer,
        ForeignKey("credit_statements_view.id"),
        nullable=False,
    )
    transaction_date = Column(Date, nullable=False)
    merchant = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    notes = Column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "CreditTransaction",
        back_populates="view",
        uselist=False,
    )
    internal_transaction = relationship(
        "InternalTransaction", back_populates="credit_transactions"
    )
    statement = relationship(
        "CreditStatementView",
        viewonly=True,
        back_populates="transactions",
    )
    subtransactions = relationship(
        "CreditSubtransaction",
        back_populates="transaction",
    )


tag_link_table = Table(
    # Not sure why this table is necessary because it should already be
    # reflected; perhaps explore or wait until sqlalchemy 2.0
    "credit_tag_links",
    Model.metadata,
    Column(
        "subtransaction_id",
        ForeignKey("credit_subtransactions.id"),
        primary_key=True,
    ),
    Column("tag_id", ForeignKey("credit_tags.id"), primary_key=True),
)


class CreditSubtransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_subtransactions"
    _user_id_join_chain = (
        CreditTransactionView,
        CreditStatementView,
        CreditCard,
        CreditAccount,
        Bank,
    )
    # Columns
    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer,
        ForeignKey("credit_transactions_view.id"),
        nullable=False,
    )
    subtotal = Column(Float, nullable=False)
    note = Column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "CreditTransactionView",
        viewonly=True,
        back_populates="subtransactions",
    )
    tags = relationship(
        "CreditTag",
        secondary=tag_link_table,
        back_populates="subtransactions",
    )


class CreditTag(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_tags"
    # Columns
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("credit_tags.id"))
    tag_name = Column(String, nullable=False)
    # Relationships
    subtransactions = relationship(
        "CreditSubtransaction",
        secondary=tag_link_table,
        back_populates="tags",
    )


class InternalTransaction(Model):
    __tablename__ = "internal_transactions"
    # Columns
    id = Column(Integer, primary_key=True)
    # Relationships
    bank_transactions = relationship(
        "BankTransactionView",
        back_populates="internal_transaction",
    )
    credit_transactions = relationship(
        "CreditTransactionView",
        back_populates="internal_transaction",
    )
