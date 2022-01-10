/* Set some default account types (user_id=0 indicates all users) */
INSERT INTO bank_account_types
  (user_id, type_name, type_abbreviation)
VALUES
  (0, 'Savings', NULL),
  (0, 'Checking', NULL),
  (0, 'Certificate of Deposit', 'CD');
