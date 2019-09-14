DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS credit_transactions;
DROP TABLE IF EXISTS credit_cards;

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
	statement_day INTEGER NOT NULL,
	active INTEGER NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE credit_transactions (
	id INTEGER,
	card_id INTEGER NOT NULL,
	transaction_date TEXT NOT NULL,
	vendor TEXT NOT NULL,
	price REAL NOT NULL,
	notes TEXT NOT NULL,
	statement_date TEXT NOT NULL,
	PRIMARY KEY(id),
	FOREIGN KEY(card_id) REFERENCES credit_cards(id)
);
