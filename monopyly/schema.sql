DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS credit_cards;
DROP TABLE IF EXISTS credit_statements;
DROP TABLE IF EXISTS credit_transactions;

CREATE TABLE users (
	id INTEGER,
	username TEXT UNIQUE NOT NULL,
	password TEXT NOT NULL,
	PRIMARY KEY(id)
);

CREATE TABLE credit_accounts (
	id INTEGER,
	user_id INTEGER NOT NULL,
	bank TEXT NOT NULL,
	statement_issue_day INTEGER NOT NULL,
	statement_due_day INTEGER NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE credit_cards (
	id INTEGER,
	account_id INTEGER NOT NULL,
	last_four_digits TEXT NOT NULL,
	active INTEGER NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(account_id) REFERENCES credit_accounts(id)
);

CREATE TABLE credit_statements (
	id INTEGER,
	card_id INTEGER NOT NULL,
	issue_date TEXT NOT NULL,
	due_date TEXT NOT NULL,
	paid INTEGER NOT NULL,
	payment_date TEXT,
	PRIMARY KEY(id),
	FOREIGN KEY(card_id) REFERENCES credit_cards(id)
);

CREATE VIEW credit_statements_view AS
SELECT *
  FROM (SELECT s.*,
	       COALESCE(SUM(amount)
	          	OVER (PARTITION BY c.account_id ORDER BY s.issue_date),
		       	0
	       ) balance
	  FROM credit_statements AS s 
	       INNER JOIN credit_cards AS c
	       ON c.id = s.card_id
               LEFT OUTER JOIN credit_transactions AS t
	       ON t.statement_id = s.id
)
GROUP BY id;

CREATE TABLE credit_transactions (
	id INTEGER,
	statement_id INTEGER NOT NULL,
	transaction_date TEXT NOT NULL,
	vendor TEXT NOT NULL,
	amount REAL NOT NULL,
	notes TEXT NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(statement_id) REFERENCES credit_statements(id)
);
