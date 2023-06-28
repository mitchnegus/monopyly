from authanor.database.models import AuthorizedAccessMixin, Model
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import mapped_column, relationship


class User(Model):
    __tablename__ = "users"
    # Columns
    id = mapped_column(Integer, primary_key=True)
    username = mapped_column(String, nullable=False)
    password = mapped_column(String, nullable=False)
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


class InternalTransaction(Model):
    __tablename__ = "internal_transactions"
    # Columns
    id = mapped_column(Integer, primary_key=True)
    # Relationships
    bank_transactions = relationship(
        "BankTransactionView",
        back_populates="internal_transaction",
    )
    credit_transactions = relationship(
        "CreditTransactionView",
        back_populates="internal_transaction",
    )


# Not sure why these tables are necessary, because they should already be reflected;
# perhaps explore or wait until sqlalchemy 2.0

bank_tag_link_table = Table(
    "bank_tag_links",
    Model.metadata,
    Column(
        "subtransaction_id",
        ForeignKey("bank_subtransactions.id"),
        primary_key=True,
    ),
    Column("tag_id", ForeignKey("transaction_tags.id"), primary_key=True),
)


credit_tag_link_table = Table(
    "credit_tag_links",
    Model.metadata,
    Column(
        "subtransaction_id",
        ForeignKey("credit_subtransactions.id"),
        primary_key=True,
    ),
    Column("tag_id", ForeignKey("transaction_tags.id"), primary_key=True),
)


class TransactionTag(AuthorizedAccessMixin, Model):
    __tablename__ = "transaction_tags"
    # Columns
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = mapped_column(Integer, ForeignKey("transaction_tags.id"))
    tag_name = mapped_column(String, nullable=False)
    # Relationships
    bank_subtransactions = relationship(
        "BankSubtransaction",
        secondary=bank_tag_link_table,
        back_populates="tags",
    )
    credit_subtransactions = relationship(
        "CreditSubtransaction",
        secondary=credit_tag_link_table,
        back_populates="tags",
    )


class Bank(AuthorizedAccessMixin, Model):
    __tablename__ = "banks"
    # Columns
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    bank_name = mapped_column(String, nullable=False)
    # Relationships
    user = relationship("User", back_populates="banks")
    bank_accounts = relationship(
        "BankAccountView",
        viewonly=True,
        back_populates="bank",
        cascade="all, delete",
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
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    type_name = mapped_column(String, nullable=False)
    type_abbreviation = mapped_column(String)
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
    id = mapped_column(Integer, ForeignKey("bank_account_types.id"), primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    type_name = mapped_column(String, nullable=False)
    type_abbreviation = mapped_column(String)
    type_common_name = mapped_column(String, nullable=False)
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
    id = mapped_column(Integer, primary_key=True)
    bank_id = mapped_column(Integer, ForeignKey("banks.id"), nullable=False)
    account_type_id = mapped_column(
        Integer,
        ForeignKey("bank_account_types_view.id"),
        nullable=False,
    )
    last_four_digits = mapped_column(String, nullable=False)
    active = mapped_column(Integer, nullable=False)
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
    id = mapped_column(Integer, ForeignKey("bank_accounts.id"), primary_key=True)
    bank_id = mapped_column(Integer, ForeignKey("banks.id"), nullable=False)
    account_type_id = mapped_column(
        Integer,
        ForeignKey("bank_account_types_view.id"),
        nullable=False,
    )
    last_four_digits = mapped_column(String, nullable=False)
    active = mapped_column(Integer, nullable=False)
    balance = mapped_column(Float, nullable=False)
    projected_balance = mapped_column(Float, nullable=False)
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
    id = mapped_column(Integer, primary_key=True)
    internal_transaction_id = mapped_column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    account_id = mapped_column(
        Integer,
        ForeignKey("bank_accounts_view.id"),
        nullable=False,
    )
    transaction_date = mapped_column(Date, nullable=False)
    merchant = mapped_column(String)
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
    id = mapped_column(Integer, ForeignKey("bank_transactions.id"), primary_key=True)
    internal_transaction_id = mapped_column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    account_id = mapped_column(
        Integer,
        ForeignKey("bank_accounts_view.id"),
        nullable=False,
    )
    transaction_date = mapped_column(Date, nullable=False)
    merchant = mapped_column(String)
    total = mapped_column(Float)
    notes = mapped_column(String)
    balance = mapped_column(Float)
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
    id = mapped_column(Integer, primary_key=True)
    transaction_id = mapped_column(
        Integer,
        ForeignKey("bank_transactions_view.id"),
        nullable=False,
    )
    subtotal = mapped_column(Float, nullable=False)
    note = mapped_column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "BankTransactionView",
        viewonly=True,
        back_populates="subtransactions",
    )
    tags = relationship(
        "TransactionTag",
        secondary=bank_tag_link_table,
        back_populates="bank_subtransactions",
    )


class CreditAccount(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_accounts"
    _user_id_join_chain = (Bank,)
    # Columns
    id = mapped_column(Integer, primary_key=True)
    bank_id = mapped_column(Integer, ForeignKey("banks.id"), nullable=False)
    statement_issue_day = mapped_column(Integer, nullable=False)
    statement_due_day = mapped_column(Integer, nullable=False)
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
    id = mapped_column(Integer, primary_key=True)
    account_id = mapped_column(
        Integer,
        ForeignKey("credit_accounts.id"),
        nullable=False,
    )
    last_four_digits = mapped_column(String, nullable=False)
    active = mapped_column(Integer, nullable=False)
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
    id = mapped_column(Integer, primary_key=True)
    card_id = mapped_column(Integer, ForeignKey("credit_cards.id"), nullable=False)
    issue_date = mapped_column(Date, nullable=False)
    due_date = mapped_column(Date, nullable=False)
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
    id = mapped_column(Integer, ForeignKey("credit_statements.id"), primary_key=True)
    card_id = mapped_column(Integer, ForeignKey("credit_cards.id"), nullable=False)
    issue_date = mapped_column(Date, nullable=False)
    due_date = mapped_column(Date, nullable=False)
    balance = mapped_column(Float, nullable=False)
    payment_date = mapped_column(Date)
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
    id = mapped_column(Integer, primary_key=True)
    internal_transaction_id = mapped_column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    statement_id = mapped_column(
        Integer,
        ForeignKey("credit_statements_view.id"),
        nullable=False,
    )
    transaction_date = mapped_column(Date, nullable=False)
    merchant = mapped_column(String, nullable=False)
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
    id = mapped_column(
        Integer,
        ForeignKey("credit_transactions.id"),
        primary_key=True,
    )
    internal_transaction_id = mapped_column(
        Integer,
        ForeignKey("internal_transactions.id"),
    )
    statement_id = mapped_column(
        Integer,
        ForeignKey("credit_statements_view.id"),
        nullable=False,
    )
    transaction_date = mapped_column(Date, nullable=False)
    merchant = mapped_column(String, nullable=False)
    total = mapped_column(Float, nullable=False)
    notes = mapped_column(String, nullable=False)
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
    id = mapped_column(Integer, primary_key=True)
    transaction_id = mapped_column(
        Integer,
        ForeignKey("credit_transactions_view.id"),
        nullable=False,
    )
    subtotal = mapped_column(Float, nullable=False)
    note = mapped_column(String, nullable=False)
    # Relationships
    transaction = relationship(
        "CreditTransactionView",
        viewonly=True,
        back_populates="subtransactions",
    )
    tags = relationship(
        "TransactionTag",
        secondary=credit_tag_link_table,
        back_populates="credit_subtransactions",
    )
