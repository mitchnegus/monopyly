DROP TABLE IF EXISTS users;
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

/* Store credit account information */
CREATE TABLE credit_accounts (
	id INTEGER,
	user_id INTEGER NOT NULL,
	bank TEXT NOT NULL,
	statement_issue_day INTEGER NOT NULL,
	statement_due_day INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY (user_id) REFERENCES users(id)
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
	statement_id INTEGER NOT NULL,
	transaction_date TEXT NOT NULL,
	vendor TEXT NOT NULL,
	PRIMARY KEY (id),
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

/* Prepare a view giving consolidated credit card transaction information */
CREATE VIEW credit_transactions_view AS
SELECT
  t.id,
	statement_id,
	transaction_date,
	vendor,
	SUM(subtotal) total,
	GROUP_CONCAT(note, '; ') notes
FROM credit_transactions AS t
  LEFT OUTER JOIN credit_subtransactions AS s_t
	  ON s_t.transaction_id = t.id
GROUP BY t.id;

/* Prepare a view giving enhanced credit card statement information */
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
			/* Determine the balance on an account for each statement */
			COALESCE(
				SUM(subtotals) OVER (PARTITION BY account_id ORDER BY issue_date),
				0
			) statement_balance,
			/* Determine the total charges on an account for each statement */
			COALESCE(
			  SUM(charges) OVER (PARTITION BY account_id ORDER BY issue_date),
			  0
			) statement_charge_total,
			/* Determine the total payments on an account for each transaction */
			COALESCE(
			    SUM(payments)
			    OVER (PARTITION BY account_id ORDER BY transaction_date),
			    0
			) daily_payment_total
	    FROM (
	      SELECT
					statement_id,
					transaction_date,
					SUM(subtotal) subtotals,
	        CASE WHEN SUM(subtotal) >= 0 THEN SUM(subtotal) END charges,
	        CASE WHEN SUM(subtotal) < 0 THEN SUM(subtotal) END payments
				FROM credit_transactions
					INNER JOIN credit_subtransactions
					  ON credit_subtransactions.transaction_id = credit_transactions.id
				GROUP BY transaction_id
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
			/* Get times where payments offset charges (with float tolerance)*/
			AND v1.statement_charge_total + v2.daily_payment_total < 1E-6
			/* Exclude times where the statement charges are zero (new statements)*/
			AND ABS(v1.statement_balance) > 1E-6
		ORDER BY v1.transaction_date
	) v2
		ON v2.id = s.id
GROUP BY s.id;
