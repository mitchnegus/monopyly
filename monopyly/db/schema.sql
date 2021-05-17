DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS internal_transactions;
DROP TABLE IF EXISTS banks;
DROP TABLE IF EXISTS bank_accounts;
DROP TABLE IF EXISTS bank_account_types;
DROP TABLE IF EXISTS bank_transactions;
DROP TABLE IF EXISTS credit_accounts;
DROP TABLE IF EXISTS credit_cards;
DROP TABLE IF EXISTS credit_statements;
DROP TABLE IF EXISTS credit_transactions;
DROP TABLE IF EXISTS credit_subtransactions;
DROP TABLE IF EXISTS credit_tags;
DROP TABLE IF EXISTS credit_tag_links;


/* Store user information */
CREATE TABLE users (
  id INTEGER,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  PRIMARY KEY (id)
);


/* Store a common link for paired transactions */
CREATE TABLE internal_transactions (
  id INTEGER,
  PRIMARY KEY (id)
);

/* Store information about banks */
CREATE TABLE banks (
  id INTEGER,
  user_id INTEGER NOT NULL,
  bank_name TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (user_id) REFERENCES users (id),
  UNIQUE (user_id, bank_name)
);


/* Store bank account type information */
CREATE TABLE bank_account_types (
  id INTEGER,
  user_id INTEGER NOT NULL,
  type_name TEXT NOT NULL,
  type_abbreviation TEXT,
  PRIMARY KEY (id),
  UNIQUE (user_id, type_name),
  UNIQUE (user_id, type_abbreviation)
);


/* Store bank account information */
CREATE TABLE bank_accounts (
  id INTEGER,
  bank_id INTEGER NOT NULL,
  account_type_id INTEGER NOT NULL,
  last_four_digits TEXT NOT NULL,
  active INTEGER NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (bank_id) REFERENCES banks (id),
  FOREIGN KEY (account_type_id) REFERENCES bank_account_types (id),
  UNIQUE (last_four_digits, account_type_id)
);


/* Store bank transaction information */
CREATE TABLE bank_transactions (
  id INTEGER,
  internal_transaction_id INTEGER DEFAULT NULL,
  account_id INTEGER NOT NULL,
  transaction_date TEXT NOT NULL,
  total REAL NOT NULL,
  note TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (internal_transaction_id) REFERENCES internal_transactions (id),
  FOREIGN KEY (account_id) REFERENCES bank_accounts (id)
);


/* Store credit account information */
CREATE TABLE credit_accounts (
  id INTEGER,
  bank_id INTEGER NOT NULL,
  statement_issue_day INTEGER NOT NULL,
  statement_due_day INTEGER NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (bank_id) REFERENCES banks (id)
    ON DELETE CASCADE
);


/* Store credit card information */
CREATE TABLE credit_cards (
  id INTEGER,
  account_id INTEGER NOT NULL,
  last_four_digits TEXT NOT NULL,
  active INTEGER NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (account_id) REFERENCES credit_accounts (id)
    ON DELETE CASCADE
);


/* Store credit card statement information */
CREATE TABLE credit_statements (
  id INTEGER,
  card_id INTEGER NOT NULL,
  issue_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (card_id) REFERENCES credit_cards (id)
    ON DELETE CASCADE
);


/* Store credit card transaction information */
CREATE TABLE credit_transactions (
  id INTEGER,
  internal_transaction_id INTEGER DEFAULT NULL,
  statement_id INTEGER NOT NULL,
  transaction_date TEXT NOT NULL,
  vendor TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (internal_transaction_id) REFERENCES internal_transactions (id),
  FOREIGN KEY (statement_id) REFERENCES credit_statements (id)
    ON DELETE CASCADE
);


/* Store subtransaction breakdown of transaction */
CREATE TABLE credit_subtransactions (
  id INTEGER,
  transaction_id INTEGER NOT NULL,
  subtotal REAL NOT NULL,
  note TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (transaction_id) REFERENCES credit_transactions (id)
    ON DELETE CASCADE
);


/* Store credit card transaction tags */
CREATE TABLE credit_tags (
  id INTEGER,
  parent_id INTEGER,
  user_id INTEGER NOT NULL,
  tag_name TEXT NOT NULL COLLATE NOCASE,
  PRIMARY KEY (id),
  FOREIGN KEY (parent_id) REFERENCES credit_tags (id)
    ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users (id),
  UNIQUE (user_id, tag_name)
);


/* Associate credit transactions with tags in a link table */
CREATE TABLE credit_tag_links (
  subtransaction_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (subtransaction_id, tag_id),
  FOREIGN KEY (subtransaction_id) REFERENCES credit_subtransactions (id)
    ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES credit_tags (id)
    ON DELETE CASCADE
);

