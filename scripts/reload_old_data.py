import sqlite3

db = sqlite3.connect('instance/monopyly.sql')

with open('instance/credit_cards_old.sql', 'r') as f:
    db.executescript(f.read())

db.execute(
    "INSERT INTO credit_cards (user_id, bank, last_four_digits) "
    "VALUES (1, 'Discover', '2373')"
)
db.execute(
    "INSERT INTO credit_cards (user_id, bank, last_four_digits) "
    "VALUES (1, 'Chase', '0592')"
)
db.execute(
    "INSERT INTO credit_cards (user_id, bank, last_four_digits) "
    "VALUES (1, 'Discover', '3896')"
)
db.commit()
