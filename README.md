# Monopyly

This is a package designed to help manage personal finances. 
The current functionality is fairly limited, with only the ability to track credit card history.
Eventually the app will provide a full set of features including purchase history, bank deposits and withdrawals, and investment profiles. 

The app is designed to be run at a small scale. 
Information is stored in a local SQLite database and accessed using a frontend served by Flask. 
While the development version is hosted on the builtin Flask server, a more robust solution will be adopted if the app moves online. Despite its small scale, the app can support multiple users on any given instance.


## Installation

The _Monopyly_ app is hosted on the [Python Package Index (PyPI)] for easy installation. 
To install the app, simply run

```
pip install monopyly
```

The package requires a recent version of Python (3.7+). 
