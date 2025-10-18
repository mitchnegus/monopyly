import datetime

from dry_foundation.database.models import AuthorizedAccessMixin, Model
from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Model):
    __tablename__ = "users"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password: Mapped[str]
    # Relationships
    banks: Mapped["Bank"] = relationship(back_populates="user", cascade="all, delete")
    bank_account_type_views: Mapped[list["BankAccountTypeView"]] = relationship(
        back_populates="user", viewonly=True
    )


class InternalTransaction(Model):
    __tablename__ = "internal_transactions"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    # Relationships
    bank_transactions: Mapped[list["BankTransaction"]] = relationship(
        back_populates="internal_transaction"
    )
    bank_transaction_views: Mapped[list["BankTransactionView"]] = relationship(
        back_populates="internal_transaction", viewonly=True
    )
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        back_populates="internal_transaction"
    )
    credit_transaction_views: Mapped[list["CreditTransactionView"]] = relationship(
        back_populates="internal_transaction", viewonly=True
    )

    @property
    def transaction_views(self):
        return self.bank_transaction_views + self.credit_transaction_views


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
    _alt_authorized_ids = (0,)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("transaction_tags.id"))
    tag_name: Mapped[str]
    # Relationships
    parent: Mapped["TransactionTag"] = relationship(
        back_populates="children", remote_side=[id]
    )
    children: Mapped[list["TransactionTag"]] = relationship(back_populates="parent")
    bank_subtransactions: Mapped[list["BankSubtransaction"]] = relationship(
        back_populates="tags", secondary=bank_tag_link_table
    )
    credit_subtransactions: Mapped[list["CreditSubtransaction"]] = relationship(
        back_populates="tags", secondary=credit_tag_link_table
    )

    @property
    def depth(self):
        tag, depth = self, 0
        while (tag := tag.parent) is not None:
            depth += 1
        return depth


class Bank(AuthorizedAccessMixin, Model):
    __tablename__ = "banks"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    bank_name: Mapped[str]
    # Relationships
    user: Mapped["User"] = relationship(back_populates="banks")
    bank_account_views: Mapped[list["BankAccountView"]] = relationship(
        back_populates="bank", cascade="all, delete", viewonly=True
    )
    credit_accounts: Mapped[list["CreditAccount"]] = relationship(
        back_populates="bank", cascade="all, delete"
    )


class BankAccountType(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_account_types"
    _alt_authorized_ids = (0,)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_name: Mapped[str]
    type_abbreviation: Mapped[str | None]
    # Relationships
    view: Mapped["BankAccountTypeView"] = relationship(
        back_populates="account_type", uselist=False, viewonly=True
    )


class BankAccountTypeView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_account_types_view"
    _alt_authorized_ids = (0,)
    # Columns
    id = mapped_column(Integer, ForeignKey("bank_account_types.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_name: Mapped[str]
    type_abbreviation: Mapped[str | None]
    type_common_name: Mapped[str]
    # Relationships
    account_type: Mapped["BankAccountType"] = relationship(back_populates="view")
    user: Mapped["User"] = relationship(back_populates="bank_account_type_views")
    account_views: Mapped[list["BankAccountView"]] = relationship(
        back_populates="account_type_view", viewonly=True
    )


class BankAccount(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_accounts"
    _user_id_join_chain = (Bank,)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))
    account_type_id: Mapped[int] = mapped_column(
        ForeignKey("bank_account_types_view.id")
    )
    last_four_digits: Mapped[str]
    active: Mapped[int]
    # Relationships
    view: Mapped["BankAccountView"] = relationship(
        back_populates="account", uselist=False, viewonly=True
    )


class BankAccountView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_accounts_view"
    _user_id_join_chain = (Bank,)
    # Columns
    id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))
    account_type_id: Mapped[int] = mapped_column(
        ForeignKey("bank_account_types_view.id")
    )
    last_four_digits: Mapped[str]
    active: Mapped[int]
    balance: Mapped[float]
    projected_balance: Mapped[float]
    # Relationships
    account: Mapped["BankAccount"] = relationship(back_populates="view")
    bank: Mapped["Bank"] = relationship(back_populates="bank_account_views")
    account_type_view: Mapped["BankAccountTypeView"] = relationship(
        back_populates="account_views", viewonly=True
    )
    transaction_views: Mapped[list["BankTransactionView"]] = relationship(
        back_populates="account_view", viewonly=True
    )


class BankTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions"
    _user_id_join_chain = (BankAccountView, Bank)
    # Denote the transaction subtype
    subtype = "bank"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    internal_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_transactions.id")
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts_view.id"))
    transaction_date: Mapped[datetime.date]
    merchant: Mapped[str | None]
    #  Relationships
    view: Mapped["BankTransactionView"] = relationship(
        back_populates="transaction", uselist=False, viewonly=True
    )
    internal_transaction: Mapped["InternalTransaction"] = relationship(
        back_populates="bank_transactions"
    )


class BankTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_transactions_view"
    _user_id_join_chain = (BankAccountView, Bank)
    # Denote the transaction subtype
    subtype = "bank"
    # Columns
    id: Mapped[int] = mapped_column(
        ForeignKey("bank_transactions.id"), primary_key=True
    )
    internal_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_transactions.id")
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts_view.id"))
    transaction_date: Mapped[datetime.date]
    merchant: Mapped[str | None]
    total: Mapped[float]
    notes: Mapped[str | None]
    balance: Mapped[float]
    # Relationships
    transaction: Mapped["BankTransaction"] = relationship(back_populates="view")
    internal_transaction: Mapped["InternalTransaction"] = relationship(
        back_populates="bank_transaction_views"
    )
    account_view: Mapped["BankAccountView"] = relationship(
        back_populates="transaction_views", viewonly=True
    )
    subtransactions: Mapped[list["BankSubtransaction"]] = relationship(
        back_populates="transaction_view", lazy="selectin", cascade="all, delete"
    )


class BankSubtransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "bank_subtransactions"
    _user_id_join_chain = (BankTransactionView, BankAccountView, Bank)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions_view.id"))
    subtotal: Mapped[float]
    note: Mapped[str]
    # Relationships
    transaction_view: Mapped["BankTransactionView"] = relationship(
        back_populates="subtransactions", viewonly=True
    )
    tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="bank_subtransactions",
        secondary=bank_tag_link_table,
        lazy="selectin",
    )


class CreditAccount(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_accounts"
    _user_id_join_chain = (Bank,)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))
    statement_issue_day: Mapped[int]
    statement_due_day: Mapped[int]
    # ((Should probably have an 'active' field))
    # Relationships
    bank: Mapped["Bank"] = relationship(back_populates="credit_accounts")
    cards: Mapped[list["CreditCard"]] = relationship(
        back_populates="account", cascade="all, delete"
    )


class CreditCard(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_cards"
    _user_id_join_chain = (CreditAccount, Bank)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("credit_accounts.id"))
    last_four_digits: Mapped[str]
    active: Mapped[int]
    # Relationships
    account: Mapped["CreditAccount"] = relationship(back_populates="cards")
    statement_views: Mapped[list["CreditStatementView"]] = relationship(
        back_populates="card", viewonly=True
    )


class CreditStatement(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_statements"
    _user_id_join_chain = (CreditCard, CreditAccount, Bank)
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("credit_cards.id"))
    issue_date: Mapped[datetime.date]
    due_date: Mapped[datetime.date]
    # Relationships
    view: Mapped["CreditStatementView"] = relationship(
        back_populates="statement", uselist=False, viewonly=True
    )


class CreditStatementView(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_statements_view"
    _user_id_join_chain = (CreditCard, CreditAccount, Bank)
    # Columns
    id: Mapped[int] = mapped_column(
        ForeignKey("credit_statements.id"), primary_key=True
    )
    card_id: Mapped[int] = mapped_column(ForeignKey("credit_cards.id"))
    issue_date: Mapped[datetime.date]
    due_date: Mapped[datetime.date]
    balance: Mapped[float]
    payment_date: Mapped[datetime.date]
    # Relationships
    statement: Mapped["CreditStatement"] = relationship(back_populates="view")
    card: Mapped["CreditCard"] = relationship(back_populates="statement_views")
    transaction_views: Mapped[list["CreditTransactionView"]] = relationship(
        back_populates="statement_view", viewonly=True
    )


class CreditTransaction(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions"
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount, Bank)
    # Denote the transaction subtype
    subtype = "credit"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    internal_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_transactions.id")
    )
    statement_id: Mapped[int] = mapped_column(ForeignKey("credit_statements_view.id"))
    transaction_date: Mapped[datetime.date]
    merchant: Mapped[str]
    # Relationships
    view: Mapped["CreditTransactionView"] = relationship(
        back_populates="transaction", uselist=False, viewonly=True
    )
    internal_transaction: Mapped["InternalTransaction"] = relationship(
        back_populates="credit_transactions"
    )


class CreditTransactionView(AuthorizedAccessMixin, Model):
    __tablename__ = "credit_transactions_view"
    _user_id_join_chain = (CreditStatementView, CreditCard, CreditAccount, Bank)
    # Denote the transaction subtype
    subtype = "credit"
    # Columns
    id: Mapped[int] = mapped_column(
        ForeignKey("credit_transactions.id"), primary_key=True
    )
    internal_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_transactions.id")
    )
    statement_id: Mapped[int] = mapped_column(ForeignKey("credit_statements_view.id"))
    transaction_date: Mapped[datetime.date]
    merchant: Mapped[str]
    total: Mapped[float]
    notes: Mapped[str]
    # Relationships
    transaction: Mapped["CreditTransaction"] = relationship(
        back_populates="view", uselist=False
    )
    internal_transaction: Mapped["InternalTransaction"] = relationship(
        back_populates="credit_transaction_views"
    )
    statement_view: Mapped["CreditStatementView"] = relationship(
        back_populates="transaction_views", viewonly=True
    )
    subtransactions: Mapped[list["CreditSubtransaction"]] = relationship(
        back_populates="transaction_view", lazy="selectin", cascade="all, delete"
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
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("credit_transactions_view.id")
    )
    subtotal: Mapped[float]
    note: Mapped[str]
    # Relationships
    transaction_view: Mapped["CreditTransactionView"] = relationship(
        back_populates="subtransactions", viewonly=True
    )
    tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="credit_subtransactions",
        secondary=credit_tag_link_table,
        lazy="selectin",
    )

    @property
    def categorizable(self):
        # Categorizable if no conflicting tags of the same depth exist
        tag_depths = [tag.depth for tag in self.tags]
        return len(tag_depths) == len(set(tag_depths))
