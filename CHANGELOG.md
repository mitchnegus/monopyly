# Changelog


## 1.0.0

- Initial release


## 1.0.1

- Added dependencies to `setup.py` for self-contained installation
- Added this changelog
- Added a generally comprehensive [README](README.md)
- Fixed a few minor bugs with the display interface


## 1.0.2

- Added image support to PyPI description


## 1.0.3

- Implemented (rudimentary) interface for adding and removing transaction tags
- Added button to add more statements to a transaction (from submission complete page)
- Fixed bug in updating a transaction's statement date to a new statement
- Fixed bug where tags where not saved on new transactions


## 1.0.4

- Improved tagging interface with a 'Manage Tags' page
- Introduced statement level statistics
- Renamed database files to end with `.sqlite` extension
- Moved menus on 'Statement Details' and 'Account Details' pages into the sidebar to prevent overlap on collapsed screens
- Renamed `show_*` route functions to `load_*` to clarify that they are for loading the associated pages (as opposed to just displaying content)


## 1.0.5

- Transactions may be split into an arbitrary number of subtransactions, each with a separate subtotal and note
- Backend properly handles duplicate/ancestor tags; all tags are saved in the database, but only the lowest-level child tag must be entered
- Removed statement level statistics display (not yet mature)


## 1.1.0

- Added banking interface
- Added interface for displaying linked transactions (including between bank transactions and credit transactions)
- Grayed out pending transactions
- Fixed bug where transaction tags appeared in front of header bar
- Improved modularity of autocomplete JavaScript
- Improved modularity of transaction table templates (for banking and credit transactions)
- Minor cosmetic enhancements


## 1.1.1 (in progress)

- Banking interface updated to use subtransactions
- Added the ability to transfer statements when a new credit card is added to an account
- Fixed error on handling subtransactions in credit forms
- Fixed error updating transaction display from widget bar
- Adding minimal set of tests

