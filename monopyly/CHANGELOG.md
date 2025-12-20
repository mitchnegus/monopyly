# Changelog

<a class="latest-release" href="#bottom">Latest</a>

## 1.0.0

- Initial release


### 1.0.1

- Added dependencies to `setup.py` for self-contained installation
- Added this changelog
- Added a generally comprehensive [README](README.md)
- Fixed a few minor bugs with the display interface


### 1.0.2

- Added image support to PyPI description


### 1.0.3

- Implemented (rudimentary) interface for adding and removing transaction tags
- Added button to add more statements to a transaction (from submission complete page)
- Fixed bug in updating a transaction's statement date to a new statement
- Fixed bug where tags where not saved on new transactions


### 1.0.4

- Improved tagging interface with a 'Manage Tags' page
- Introduced statement level statistics
- Renamed database files to end with `.sqlite` extension
- Moved menus on 'Statement Details' and 'Account Details' pages into the sidebar to prevent overlap on collapsed screens
- Renamed `show_*` route functions to `load_*` to clarify that they are for loading the associated pages (as opposed to just displaying content)


### 1.0.5

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


## 1.2.0

- Database backend converted to use SQLAlchemy (2.0)
- Complete test suite created
- Banking interface updated to use subtransactions
- Added the ability to transfer statements when a new credit card is added to an account
- Fixed error on handling subtransactions in credit forms
- Fixed error updating transaction display from widget bar


### 1.2.1

- Improve development functionality; better/safer cleaning with a separate database and preloaded data
- Add custom form fields for consistent app-wide form implementations
- Overhaul documentation formatting with _isort_ and _Black_
- Fixed bug where multiple subtransactions failed to update properly
- Fixed error where validation was not raised for blank inputs to a `CustomChoiceSelectField`
- Fixed errors in field validation for nested subforms with unset values


### 1.2.2

- Use `pyproject.toml` via Hatch
- Added version information to app footer
- Fixed bug where bank name failed to show on 'Credit Account Details' page
- Improved JavaScript management for acquisition forms


### 1.2.3

- Add currency symbol to the amount field(s)
- Allow subform fields to be removed from forms
- Change 'Vendor' field name to 'Merchant' for better generalizability
- Remove wildcard imports from the package source code
- Update form styles to be more browser compatible
- Impose boolean constraint on boolean/integer database fields
- Use metaclasses for database handler to avoid stacking classmethod and property (deprecated in Python 3.11)


## 1.3.0

- Add a merchant field and tags to bank transactions
- Add an enhanced autocompletion for assigning transaction tags
- Add a settings page for allowing bank names to be changed (and eventually allowing passwords to be updated, among other functionality)
- Leverage SQLAlchemy 2.0 `DeclarativeBase` class and `declared_attr` decorators
- Simplify `Model` base to avoid explicitly defining column attributes
- Update the database backup script to work as part of the package
- Swap the README instructions for the 'About' page (and move the story to a separate page)
- Improve utilization of `pyroject.toml`
- Factor out the database handlers (now found in the Authanor package dependency)


### 1.3.1

- Upgrade jQuery version to 3.7.0
- Use recommended `importlib` method for pytest
- Automatically use the transferring bank as the merchant in bank transfers
- For transfers between accounts at the same bank, do not show 'Withdrawal' or 'Deposit' headers; just mark as 'Transfer'


## 1.4.0

- Add charts showing historical balances to bank account details page
- Show projected balances for bank transactions occurring in the future
- Allow users to remove the welcome block from the homepage
- Make use of `data-*` HTML tag attributes rather than ID parsing
- Prevent JavaScript errors on statement pages when buttons are non-existent
- Clean up transaction table overflow for transaction notes
- Generalize transaction forms using Jinja `super` blocks
- Convert JavaScript files to be named using kebab case
- Use Fuisce in place of Authanor for db/testing interfaces


### 1.4.1

- Use local time for determining projected balances
- Show future credit statement payments as "scheduled" (and improve logic for displaying paid notices)
- Fix incorrect return type in `CreditStatementHandler.infer_statement` method
- Distinguish between inline code and "fenced" code using a Markdown library extension
- Use more `data-*` attributes for processing transaction IDs
- Fix bug where linked transactions did not use jQuery reference


### 1.4.2

- Configure production mode via Gunicorn
- Standardize CLI usage messages
- Make browser usage optional in CLI run script


### 1.4.3

- Reconfigure makefile for smoother installation
- Fix bug where transaction toggling failed on filter updates


### 1.4.4

- Update date-to-timestamp conversion to be timezone invariant
- Fix database initialization for development mode
- Fix bug where credit card number was not displayed in card summary
- Use Beautiful Soup to make tests more robust


### 1.4.5

- Fix bug where a transaction for a new statement was marked as invalid on entry
- Sort bank account displays by account type and last four digits
- Use SQLAlchemy 'selectin' loading mode for commonly loaded relationships
- Give tags a property for identifying their depth in the user's "tag tree"


### 1.4.6

- Bump dependencies (including patching security vulnerability in gunicorn)
- Add a function for acquiring a statement and all of its transactions
- Add a convenience method to the statement handler for getting the preceding statement


### 1.4.7

- Create custom error pages for error responses (400, 404, 500, etc.)
- Render the changelog and show it via the app
- Display bank account type subtotals on the bank account summaries page
- Set the current date as the default for transaction form inputs
- Use the `strict` argument to the built-in `zip` function to strengthen tests
- Refresh the table of transactions after making a payment on a credit card statement
- Use SVG to handle long values in account/statement summary boxes; fixes bugs in page rendering (long value overflow) and hover actions not happening because of conflicting overlap with the sidebar


### 1.4.8

- Set username collection to be case insensitive
- Use Flask/Gunicorn APIs (rather than subprocess CLI calls) to launch the app
- Fix bug in the ordering of balances in the bank account balance charts for transactions on duplicate dates


## 1.5.0

- Add categorical pie charts to credit card statement details
- Provide mobile layouts for the application
- Create a tool for reconciling credit card transactions with information collected from external resources (e.g., CSVs downloaded from a user's online credit card account)


### 1.5.1

- Bump dependencies (including patching security vulnerability in NLTK)
- Style credit transaction submissions as receipts
- Style flash messages according to content
- Return to statement details page after deleting a transaction (rather than returning to the general transactions page)
- Allow users to change their password
- Warn users before form submission if the configuration currently disallows registration
- Fix issues with the application launcher not launching the browser; couple application launch process more tightly with click
- Use type annotations for SQLAlchemy ORM declarative mappings
- Increase the flexibility of the credit activity parser


### 1.5.2

- Use smoothing on charts for up to 100 transactions
- Improve tokenization normalization for credit reconciliation
- Remove statement requiring activity files be located in the `Downloads` directory
- Do not clear the reconciliation info when adding subtransaction fields via POST request
- Incorporate support for enhanced database handler selection subsets
- Bump dependencies (including support for recent SQLAlchemy versions)


### 1.6.0

- Enable additional transactions to be loaded on bank/credit transactions tables
- Create a script to take application screenshots (e.g., for the 'About' page)
- Remove Python version requirement (allow Python versions after 3.10)
- Use Jinja recursive loops for transaction tag tree structures in templates
- Refactor to include ruff-based linting checks
- Set 'Credit payments' to be a default tag for all users
- Protect globally defined tags from user deletion
- Hide transaction tags when the Escape key is pressed
- Ensure that the 'Record Transfer' functionality only ever adds one input box
- Update dependencies (including using ruff in place of _Black_ and _isort_)
- Update JavaScript libraries (jQuery, Chartist)


### 1.6.1

- Allow pie chart labels to overflow the SVG container
- Define JavaScript elements in header (deferring execution when logical)
- Bump dependencies


<a name="bottom" id="bottom"></a>
