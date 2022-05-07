/* Create a test database */
INSERT INTO users
       (username, password)
VALUES ('test', 'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f'),
       ('other', 'pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79'),
       ('mr.monopyly', 'pbkdf2:sha256:150000$Q5aFeirw$74e15d898f6222cc9af4f482ebd9e0096b17cfc9a3664dd12b59c22a58bfcc29');

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
       (2, 2, '5557', 0),  -- 'Jail' checking account '5557' (inactive)
       (3, 3, '5558', 1);  -- 'TheBank' CD '5558' (active)

