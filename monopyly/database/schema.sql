DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS internal_transactions;
DROP TABLE IF EXISTS transaction_tags;
DROP TABLE IF EXISTS banks;
DROP TABLE IF EXISTS bank_accounts;
DROP TABLE IF EXISTS bank_account_types;
DROP TABLE IF EXISTS bank_transactions;
DROP TABLE IF EXISTS bank_subtransactions;
DROP TABLE IF EXISTS bank_tag_links;
DROP TABLE IF EXISTS credit_accounts;
DROP TABLE IF EXISTS credit_cards;
DROP TABLE IF EXISTS credit_statements;
DROP TABLE IF EXISTS credit_transactions;
DROP TABLE IF EXISTS credit_subtransactions;
DROP TABLE IF EXISTS credit_tag_links;


/* Store user information */
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);


/* Store a common link for paired transactions */
CREATE TABLE internal_transactions (
  id INTEGER PRIMARY KEY
);


/* Store transaction tags */
CREATE TABLE transaction_tags (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id),
  parent_id INTEGER REFERENCES transaction_tags (id)
    ON DELETE CASCADE,
  tag_name TEXT NOT NULL COLLATE NOCASE,
  UNIQUE(user_id, tag_name)
);


/* Store information about banks */
CREATE TABLE banks (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id),
  bank_name TEXT NOT NULL,
  UNIQUE(user_id, bank_name)
);


/* Store bank account type information */
CREATE TABLE bank_account_types (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id),
  type_name TEXT NOT NULL,
  type_abbreviation TEXT,
  UNIQUE(user_id, type_name)
);


/* Store bank account information */
CREATE TABLE bank_accounts (
  id INTEGER PRIMARY KEY,
  bank_id INTEGER NOT NULL REFERENCES banks (id)
    ON DELETE CASCADE,
  account_type_id INTEGER NOT NULL REFERENCES bank_account_types (id)
    ON DELETE CASCADE,
  last_four_digits TEXT NOT NULL,
  active INTEGER NOT NULL
    CHECK(active IN (0, 1)),
  UNIQUE(bank_id, account_type_id, last_four_digits)
);


/* Store bank transaction information */
CREATE TABLE bank_transactions (
  id INTEGER PRIMARY KEY,
  internal_transaction_id INTEGER DEFAULT NULL REFERENCES internal_transactions (id),
  account_id INTEGER NOT NULL REFERENCES bank_accounts (id)
    ON DELETE CASCADE,
  transaction_date DATE NOT NULL,
  merchant TEXT
);


/* Store bank subtransaction infromation */
CREATE TABLE bank_subtransactions (
  id INTEGER PRIMARY KEY,
  transaction_id INTEGER NOT NULL REFERENCES bank_transactions (id)
    ON DELETE CASCADE,
  subtotal REAL NOT NULL,
  note TEXT NOT NULL
);


/* Associate bank transactions with tags in a link table */
CREATE TABLE bank_tag_links (
  subtransaction_id INTEGER NOT NULL REFERENCES bank_subtransactions (id)
    ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES transaction_tags (id)
    ON DELETE CASCADE,
  PRIMARY KEY (subtransaction_id, tag_id)
);


/* Store credit account information */
CREATE TABLE credit_accounts (
  id INTEGER PRIMARY KEY,
  bank_id INTEGER NOT NULL REFERENCES banks (id)
    ON DELETE CASCADE,
  statement_issue_day INTEGER NOT NULL
    CHECK(statement_issue_day > 0 AND statement_issue_day < 28),
  statement_due_day INTEGER NOT NULL
    CHECK(statement_due_day > 0 AND statement_due_day < 28)
);


/* Store credit card information */
CREATE TABLE credit_cards (
  id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES credit_accounts (id)
    ON DELETE CASCADE,
  last_four_digits TEXT NOT NULL,
  active INTEGER NOT NULL
    CHECK(active IN (0, 1))
);


/* Store credit card statement information */
CREATE TABLE credit_statements (
  id INTEGER PRIMARY KEY,
  card_id INTEGER NOT NULL REFERENCES credit_cards (id)
    ON DELETE CASCADE,
  issue_date DATE NOT NULL,
  due_date DATE NOT NULL
);


/* Store credit card transaction information */
CREATE TABLE credit_transactions (
  id INTEGER PRIMARY KEY,
  internal_transaction_id INTEGER DEFAULT NULL REFERENCES internal_transactions (id),
  statement_id INTEGER NOT NULL REFERENCES credit_statements (id)
    ON DELETE CASCADE,
  transaction_date DATE NOT NULL,
  merchant TEXT NOT NULL
);


/* Store subtransaction breakdown of transaction */
CREATE TABLE credit_subtransactions (
  id INTEGER PRIMARY KEY,
  transaction_id INTEGER NOT NULL REFERENCES credit_transactions (id)
    ON DELETE CASCADE,
  subtotal REAL NOT NULL,
  note TEXT NOT NULL
);


/* Associate credit transactions with tags in a link table */
CREATE TABLE credit_tag_links (
  subtransaction_id INTEGER NOT NULL REFERENCES credit_subtransactions (id)
    ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES transaction_tags (id)
    ON DELETE CASCADE,
  PRIMARY KEY (subtransaction_id, tag_id)
);

