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


## 1.0.4 (in progress)

- Renamed database files to end with `.sqlite` extension
- Moved menus on 'Statement Details' and 'Account Details' pages into the sidebar to prevent overlap on collapsed screens
- Introduced statement level statistics
- Renamed `show_*` route functions to `load_*` to clarify that they are for loading the associated pages (as opposed to just displaying content)
