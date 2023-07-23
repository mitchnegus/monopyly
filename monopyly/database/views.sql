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
  t.*,
  IFNULL(t.type_abbreviation, t.type_name) type_common_name
FROM bank_account_types AS t;


/* Prepare a view giving enhanced bank account transaction information */
CREATE VIEW bank_transactions_view AS
WITH view AS (
  SELECT
    t.*,
    ROUND(SUM(subtotal), 2) total,
    GROUP_CONCAT(note, '; ') notes
  FROM bank_transactions AS t
    LEFT OUTER JOIN bank_subtransactions AS s_t
      ON s_t.transaction_id = t.id
  GROUP BY t.id
)
SELECT
  view.*,
  ROUND(
    SUM(total) OVER (PARTITION BY account_id ORDER BY transaction_date, id),
    2
  ) balance
FROM view;


/* Prepare a view giving enhanced bank account information */
CREATE VIEW bank_accounts_view AS
SELECT
  a.*,
  ROUND(COALESCE(
      SUM(CASE WHEN t.transaction_date <= DATE('now', 'localtime') THEN t.total END),
      0
  ), 2) balance,
  ROUND(COALESCE(SUM(t.total), 0), 2) projected_balance
FROM bank_accounts AS a
  LEFT OUTER JOIN bank_transactions_view AS t
    ON t.account_id = a.id
GROUP BY a.id;


/* Prepare a view giving consolidated credit card transaction information */
CREATE VIEW credit_transactions_view AS
SELECT
  t.*,
  ROUND(SUM(subtotal), 2) total,
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
      ROUND(COALESCE(
        SUM(subtotals) OVER (PARTITION BY account_id ORDER BY issue_date),
        0
      ), 2) statement_balance,
      /* Determine the total charges on an account for each statement */
      ROUND(COALESCE(
        SUM(charges) OVER (PARTITION BY account_id ORDER BY issue_date),
        0
      ), 2) statement_charge_total,
      /* Determine the total payments on an account for each transaction */
      ROUND(COALESCE(
        SUM(payments)
        OVER (PARTITION BY account_id ORDER BY transaction_date),
        0
      ), 2) daily_payment_total
      FROM (
        SELECT
          statement_id,
          transaction_date,
          SUM(subtotal) subtotals,
          CASE WHEN ROUND(SUM(subtotal), 2) >= 0 THEN SUM(subtotal) END charges,
          CASE WHEN ROUND(SUM(subtotal), 2) < 0 THEN SUM(subtotal) END payments
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
      /* Get times where payments offset charges */
      AND ROUND(v1.statement_charge_total + v2.daily_payment_total, 2) <= 0
    ORDER BY v1.transaction_date
  ) v2
    ON v2.id = s.id
GROUP BY s.id;
