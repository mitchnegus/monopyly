/* Set the "global user" as user_id=0 */
INSERT INTO users
  (id, username, password)
VALUES
  (0, 'global', 'n/a');

/* Set a default transaction tag for credit payments */
INSERT INTO transaction_tags
       (user_id, parent_id, tag_name)
VALUES (0, NULL, 'Credit payments');

/* Set some default account types */
INSERT INTO bank_account_types
  (user_id, type_name, type_abbreviation)
VALUES
  (0, 'Savings', NULL),
  (0, 'Checking', NULL),
  (0, 'Certificate of Deposit', 'CD');
