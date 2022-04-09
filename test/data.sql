/* Create a test database */
INSERT INTO users (username, password)
VALUES ('test', 'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f'),
       ('other', 'pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79'),
       ('mr.monopyly', 'pbkdf2:sha256:150000$Q5aFeirw$74e15d898f6222cc9af4f482ebd9e0096b17cfc9a3664dd12b59c22a58bfcc29');

INSERT INTO banks (user_id, bank_name)
VALUES (1, 'Test Bank'),
       (3, 'Jail'),
       (3, 'TheBank');
