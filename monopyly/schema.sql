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

CREATE TABLE credit_cards (
	id INTEGER,
	user_id INTEGER NOT NULL,
	bank TEXT NOT NULL,
	last_four_digits TEXT NOT NULL,
	statement_issue_day INTEGER NOT NULL,
	statement_due_day INTEGER NOT NULL,
	active INTEGER NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(user_id) REFERENCES users(id)
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

CREATE TABLE credit_transactions (
	id INTEGER,
	statement_id INTEGER NOT NULL,
	transaction_date TEXT NOT NULL,
	vendor TEXT NOT NULL,
	price REAL NOT NULL,
	notes TEXT NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(statement_id) REFERENCES credit_statements(id)
);
