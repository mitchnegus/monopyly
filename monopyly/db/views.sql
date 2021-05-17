/*
 * Views enabling enhanced database functionality without additional overhead
 */
 DROP VIEW IF EXISTS bank_account_types_view;
 DROP VIEW IF EXISTS bank_accounts_view;
 DROP VIEW IF EXISTS bank_transactions_view;
 DROP VIEW IF EXISTS credit_transactions_view;
 DROP VIEW IF EXISTS credit_statements_view;


/* Prepare a view giving consolidated bank account type information */
CREATE VIEW bank_account_types_view AS
SELECT
  id,
  user_id,
  IFNULL(type_abbreviation, type_name) type_name,
  type_name type_full_name
FROM bank_account_types;


/* Prepare a view giving enhanced bank account information */
CREATE VIEW bank_accounts_view AS
SELECT
  a.*,
  COALESCE(SUM(total), 0) balance
FROM bank_accounts AS a
  LEFT OUTER JOIN bank_transactions AS t
    ON t.account_id = a.id
GROUP BY a.id;


/* Prepare a view giving enhanced bank account transaction information */
CREATE VIEW bank_transactions_view AS
SELECT
  id,
  internal_transaction_id,
  account_id,
  transaction_date,
  total,
  SUM(total) OVER (PARTITION BY account_id ORDER BY transaction_date) balance,
  note
FROM bank_transactions;


/* Prepare a view giving consolidated credit card transaction information */
CREATE VIEW credit_transactions_view AS
SELECT
  t.id,
  internal_transaction_id,
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
