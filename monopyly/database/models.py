from datetime import date

from flask import g
from sqlalchemy import (
    Table, Column, Integer, Float, String, Date, ForeignKey, select
)
from sqlalchemy.orm import (
    declarative_base, relationship, with_loader_criteria
)


class ModelBase:
    """A declarative base for all models."""
    _repr_attributes = ()

    def _format_repr_attr(self, name):
        value = getattr(self, name)
        value_str = f"{value}"
        # Abbreviate the string if it's longer than a set length
        abbrev_len = 25
        if len(value_str) > abbrev_len:
            value_str = f"{value_str[:abbrev_len]}..."
        if type(value) in (str, date):
            value_str = f"'{value_str}'"
        return f"{name}={value_str}"

    def __repr__(self):
        if self._repr_attributes:
            pairs = [self._format_repr_attr(_) for _ in self._repr_attributes]
            attributes_str = ", ".join(pairs)
            repr_str = f"{self.__class__.__name__}({attributes_str})"
        else:
            repr_str = super().__repr__()
        return repr_str


Model = declarative_base(cls=ModelBase)


class AuthorizedAccessMixin:
    """A mixin class to facilitate making user-restricted queries."""
    _user_id_join_chain = ()
    _alt_authorized_ids = ()

    @classmethod
    @property
    def user_id_model(cls):
        if cls._user_id_join_chain:
            return cls._user_id_join_chain[-1]
        return cls

    @classmethod
    @property
    def _authorizing_criteria(cls):
        try:
            user_id_field = cls.user_id_model.user_id
        except AttributeError:
            msg = ("An authorized access model must either contain a direct "
                   "reference to the user ID or specify a chain of joins to a "
                   "table where the user ID can be verified.")
            raise AttributeError(msg)
        return user_id_field.in_(cls.authorized_ids)

    @classmethod
    @property
    def authorized_ids(cls):
        # Add any extra IDs specified (e.g., user ID 0 for common entries)
        return (g.user.id, *cls._alt_authorized_ids)

    @classmethod
    def select_for_user(cls, *args, guaranteed_joins=(), **kwargs):
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
    _repr_attributes = ("id", "username", "password")
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
    _repr_attributes = ("id", "user_id", "bank_name")
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
    _repr_attributes = ("id", "user_id", "type_name", "type_abbreviation")
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
    _repr_attributes = ("id", "user_id", "type_name", "type_common_name")
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
    _repr_attributes = ("id", "bank_id", "account_type_id", "last_four_digits",
                        "active")
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
    _repr_attributes = ("id", "bank_id", "account_type_id", "last_four_digits",
                        "active", "balance")
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
        "BankTransactionView",
        viewonly=True,
        back_populates="account"
    )


class BankTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions"
    _repr_attributes = ("id", "internal_transaction_id", "account_id",
                        "transaction_date")
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
    # ((Should have optional vendor field?))
    #  Relationships
    view = relationship(
        "BankTransactionView",
        viewonly=True,
        back_populates="transaction",
        uselist=False,
    )


class BankTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions_view"
    _repr_attributes = ("id", "internal_transaction_id", "account_id",
                        "transaction_date", "total", "notes", "balance")
    _user_id_join_chain = (BankAccountView, Bank)
    # Denote the transaction subtype
    subtype = "bank"
    # Columns
    id = Column(Integer, ForeignKey('bank_transactions.id'), primary_key=True)
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
    total = Column(Float)
    notes = Column(String)
    balance = Column(Float)
    # ((Should have optional vendor field?))
    # Relationships
    transaction = relationship(
        "BankTransaction",
        back_populates="view",
    )
    internal_transaction = relationship(
        "InternalTransaction",
        back_populates="bank_transactions"
    )
    account = relationship("BankAccountView", back_populates="transactions")
    subtransactions = relationship(
        "BankSubtransaction",
        back_populates="transaction",
    )


class BankSubtransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_subtransactions"
    _repr_attributes = ("id", "transaction_id", "subtotal", "note")
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
    _repr_attributes = ("id", "bank_id", "statement_issue_day",
                        "statement_due_day")
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
    _repr_attributes = ("id", "account_id", "last_four_digits", "active")
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
    _repr_attributes = ("id", "card_id", "issue_date", "due_date")
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
    _repr_attributes = ("id", "card_id", "issue_date", "due_date")
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
        "CreditTransactionView",
        viewonly=True,
        back_populates="statement"
    )


class CreditTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions"
    _repr_attributes = ("id", "internal_transaction_id", "statement_id",
                        "transaction_date", "vendor")
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount,
                           Bank)
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
    vendor = Column(String, nullable=False)
    # Relationships
    view = relationship(
        "CreditTransactionView",
        viewonly=True,
        back_populates="transaction",
        uselist=False,
    )


class CreditTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions_view"
    _repr_attributes = ("id", "internal_transaction_id", "statement_id",
                        "transaction_date", "vendor", "total", "notes")
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount,
                           Bank)
    # Denote the transaction subtype
    subtype = "credit"
    # Columns
    id = Column(
        Integer,
        ForeignKey('credit_transactions.id'),
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
    vendor = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    notes = Column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "CreditTransaction",
        back_populates="view",
        uselist=False,
    )
    internal_transaction = relationship(
        "InternalTransaction",
        back_populates="credit_transactions"
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
    _repr_attributes = ("id", "transaction_id", "subtotal", "note")
    _user_id_join_chain = (CreditTransactionView, CreditStatementView,
                           CreditCard, CreditAccount, Bank)
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
    _repr_attributes = ("id", "user_id", "parent_id", "tag_name")
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
    _repr_attributes = ("id",)
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

