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
	PRIMARY KEY(id),
	FOREIGN KEY(card_id) REFERENCES credit_cards(id)
);

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

CREATE VIEW credit_statements_view AS
WITH view AS (
	SELECT
		*
	FROM (
		SELECT
			s.id,
			s.issue_date,
			c.account_id,
			t.transaction_date,
			COALESCE(
				SUM(amount) OVER (PARTITION BY account_id ORDER BY issue_date),
				0
			) balance,
			COALESCE(
			  SUM(charges) OVER (PARTITION BY account_id ORDER BY issue_date),
			  0
			) statement_charge_total,
			COALESCE(
			    SUM(payments)
			    OVER (PARTITION BY account_id ORDER BY transaction_date),
			    0
			) daily_payment_total
	    FROM (
	      SELECT
					statement_id, transaction_date, amount,
	        CASE WHEN amount >= 0 THEN amount END charges,
	        CASE WHEN amount < 0 THEN amount END payments
				FROM credit_transactions
			) t
				LEFT OUTER JOIN credit_statements s
					ON s.id = t.statement_id 
				INNER JOIN credit_cards c
					ON c.id = s.card_id
	)
	GROUP BY id, daily_payment_total
	ORDER BY transaction_date
)
WITH view AS (
	SELECT
		*
	FROM (
		SELECT
			s.id,
			s.issue_date,
			c.account_id,
			t.transaction_date,
			COALESCE(
				/* Get the overall balance by statement */
				SUM(amount) OVER (PARTITION BY account_id ORDER BY issue_date),
				0
			) statement_balance,
			COALESCE(
				/* Get the total charges by statement */
			  SUM(charges) OVER (PARTITION BY account_id ORDER BY issue_date),
			  0
			) statement_charge_total,
			COALESCE(
				/* Get the total payments by day */
			  SUM(payments)
			  OVER (PARTITION BY account_id ORDER BY transaction_date),
			  0
			) daily_payment_total
	    FROM (
	      SELECT
					statement_id, transaction_date, amount,
	        CASE WHEN amount >= 0 THEN amount END charges,
	        CASE WHEN amount < 0 THEN amount END payments
				FROM credit_transactions
			) t
				LEFT OUTER JOIN credit_statements s
					ON s.id = t.statement_id 
				INNER JOIN credit_cards c
					ON c.id = s.card_id
	)
	GROUP BY id, daily_payment_total
	ORDER BY transaction_date
)
SELECT 
	s.*,
	v1.statement_balance balance,
	v2.payment_date
FROM credit_statements s
	LEFT OUTER JOIN view v1
		ON v1.id = s.id
	LEFT OUTER JOIN (
		SELECT
			v1.id,
			v2.transaction_date payment_date
		FROM view v1, view v2
		WHERE
			/* Only compare balances for a single account */
		  v1.account_id = v2.account_id
			/* Get times where payments offset chargest (with float tolerance)*/
			AND v1.statement_charge_total + v2.daily_payment_total < 1E-6
		ORDER BY v1.transaction_date
	) v2
		ON v2.id = s.id
GROUP BY s.id
