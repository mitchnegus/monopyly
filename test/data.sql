/* Create a test database */
INSERT INTO users
       (username, password)
VALUES ('test', 'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f'),
       ('other', 'pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79'),
       ('mr.monopyly', 'pbkdf2:sha256:150000$Q5aFeirw$74e15d898f6222cc9af4f482ebd9e0096b17cfc9a3664dd12b59c22a58bfcc29');

/* Register two internal transactions */
INSERT INTO internal_transactions DEFAULT VALUES;
INSERT INTO internal_transactions DEFAULT VALUES;
/* Register an unused internal transaction */
INSERT INTO internal_transactions DEFAULT VALUES;

INSERT INTO banks
       (user_id, bank_name)
VALUES (1, 'Test Bank'),   -- user: 'test'
       (3, 'Jail'),        -- user: 'mr.monopyly'
       (3, 'TheBank');     -- user: 'mr.monopyly'

INSERT INTO bank_account_types
       (user_id, type_name, type_abbreviation)
VALUES (1, 'Test Type', 'TT'),
       (3, 'Trustworthy Player', 'Trust'),
       (3, 'Cooperative Enjoyment Depository', 'Mutual FunD');

INSERT INTO bank_accounts
       (bank_id, account_type_id, last_four_digits, active)
VALUES (1, 1, '5555', 1),  -- 'Test Bank' savings account '5555' (active)
       (2, 1, '5556', 1),  -- 'Jail' savings account '5556' (active)
       (2, 2, '5556', 0),  -- 'Jail' checking account '5556' (inactive)
       (3, 3, '5557', 1);  -- 'TheBank' CD '5557' (active)

INSERT INTO bank_transactions
       (internal_transaction_id, account_id, transaction_date)
VALUES (NULL, 1, '2020-05-04'),  -- 'Test Bank' savings transaction on 2020-05-04
       (NULL, 2, '2020-05-04'),  -- 'Jail' savings transaction on 2020-05-04
       (1, 2, '2020-05-05'),     -- 'Jail' savings transaction on 2020-05-05 (link)
       (NULL, 2, '2020-05-06'),  -- 'Jail' savings transaction on 2020-05-06
       (2, 3, '2020-05-04'),     -- 'Jail' checking payment on 2020-05-04
       (1, 3, '2020-05-05'),     -- 'Jail' checking transaction on 2020-05-05 (link)
       (NULL, 4, '2020-05-06'),  -- 'TheBank' CD transaction on 2020-05-06
       (NUll, 4, '2020-05-07');  -- 'TheBank' CD transaction on 2020-05-07
                                      /* (with no defined subtransactions) */
INSERT INTO bank_subtransactions
      (transaction_id, subtotal, note)
VALUES
      (1, 100.00, 'Test bank transaction'),
      (2, 42.00, 'Jail subtransaction 1'),
      (2, 43.00, 'Jail subtransaction 2'),
      (3, 300.00, 'Transfer in'),
      (4, 58.90, 'What else is there to do in Jail?'),
      (5, -109.21, 'Credit card payment'),
      (6, -300.00, 'Transfer out'),
      (7, 200.00, '''Go'' Corner ATM deposit');

INSERT INTO credit_accounts
       (bank_id, statement_issue_day, statement_due_day)
VALUES (1, 1, 20),
       (2, 10, 5),
       (3, 20, 12);

INSERT INTO credit_cards
       (account_id, last_four_digits, active)
VALUES (1, '3333', 1),
       (2, '3334', 0),
       (2, '3335', 1),
       (3, '3336', 1);

INSERT INTO credit_statements
       (card_id, issue_date, due_date)
       /* Note: `issue_date` intentionally different from `statement_issue_day`
                as this connection is typical but not required */
VALUES (1, '2020-05-15', '2020-06-05'),
       (2, '2020-03-15', '2020-04-05'),
       (3, '2020-04-15', '2020-05-05'),
       (3, '2020-05-10', '2020-06-05'),
       (3, '2020-06-10', '2020-07-05'),
       (4, '2020-05-10', '2020-06-03'),
       (4, '2020-06-10', '2020-07-03');

INSERT INTO credit_transactions
       (internal_transaction_id, statement_id, transaction_date, vendor)
VALUES (NULL, 1, '2020-04-20', 'Test vendor'),
       (NULL, 2, '2020-04-13', 'Top Left Corner'),
       (NULL, 3, '2020-03-20', 'Boardwalk'),
       (NULL, 3, '2020-04-05', 'Park Place'),
       (NULL, 4, '2020-04-25', 'Electric Company'),
       (NULL, 4, '2020-05-01', 'Marvin Gardens'),
       (2, 4, '2020-05-04', 'JP Morgan Chance'),
       (NULL, 5, '2020-05-30', 'Water Works'),
       (NULL, 6, '2020-04-20', 'Pennsylvania Avenue'),
       (NULL, 6, '2020-05-10', 'Income Tax Board'),
       (NULL, 7, '2020-06-05', 'Reading Railroad'),
       (NULL, 7, '2020-06-05', 'Boardwalk'),
       (NULL, 2, '2020-03-10', 'Community Chest');

INSERT INTO credit_subtransactions
       (transaction_id, subtotal, note)
VALUES (1, 100.00, 'Test credit transaction'),
       (2, 1.00, 'Parking (thought it was free)'),
       (3, 43.21, 'Merry-go-round'),
       (4, 30.00, 'One for the park'),
       (4, 35.00, 'One for the place'),
       (5, 99.00, 'Electric bill'),
       (6, 6500.00, 'Expensive real estate'),
       (7, -109.21, 'Credit card payment'),
       (8, 26.87, 'Tough loss'),
       (9, 1600.00, 'Expensive house tour'),
       (10, -123.00, 'Refund'),
       (11, 253.99, 'Conducting business'),
       (12, 12.34, 'Back for more...');

