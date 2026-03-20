# FinTrackr: Personal finances and budgeting app

![Schema diagram](img/schema.png)

*Schema diagram made at [QuickDataBaseDiagrams.com](https://app.quickdatabasediagrams.com), using SQL_to_EDL.py in this repo (so inconsistency with actual db schema is possible!)*

## Inputs

Users provide csvs of transactions (e.g. downloaded credit card statements from your bank).

FinTrackr will then classify each transaction (expense or income) by category (groceries, eating out, etc) and whether the expense is recurring, and on what frequency. Initially classification will be manual, but v2 will use an ML model (classical or LLM, TBD).

Security: the database runs locally, nothing leaves your machine.

## Example usage

Currently the only interface is running scripts in a terminal. 

These scripts do additional input handling (e.g. of csv formats) that the methods they call do not.

Because I'm not passing around a FinDB object, I can't use mocking to test these; and 
I can't use a testing instance of the db because I'm loading the db name from a config ... 
I may change those design decisions.

### Log transactions in the db

To log a list of transactions (amounts on dates, with text description provided by bank) into the db from a csv:

in the terminal, run

``` 
python ./src/fintrackr/load_transactions.py <account_name> <filepath> <username> <pw>
```

where:
- `<account_name>` is the name of an account in the db which had these transactions. 
In the db schema, this is the `name` field of the `data_sources` table.

- `<filepath>` is the full path to a csv with columns `Date` and `Balance`

- `<username>` and `<pw>` to connect to the db (see below for how to set up).

*TODO this is not ideal - a lot of duplicated code between load_transactions and load_balances.*

### Log account balances in the db

To log a list of account balances (amounts on dates) into the db from a csv:

in the terminal, run

``` 
python ./src/fintrackr/load_balances.py <account_name> <filepath> <username> <pw>
```

where:
- `<account_name>` is the name of an account in the db for which to record balances. 
In the db schema, this is the `name` field of the `data_sources` table.

- `<filepath>` is the full path to a csv with columns `Date` and `Balance`

- `<username>` and `<pw>` to connect to the db (see below for how to set up).

To log a single balance directly, use the `add_balance` method of the `FinDB` class.

### Plot account balances

In the terminal, run

``` 
python ./src/fintrackr/plot_accnt_balances.py <account_name> <start_date> <end_date> <username> <pw>
```

where:
- `<account_name>` is the name of an account in the db for which transactions (and, optionally, balances)
are recorded. In the db schema, this is the `name` field of the `data_sources` table.

- Account balances will be plotted between `<start_date>` and `<end_date>`. Balances logged in the db will be plotted,
as well as balances calculated as a result of all logged transactions on that account, between the specified dates.

- `<username>` and `<pw>` to connect to the db (see below for how to set up).


## Getting started

Install PostgreSQL (TODO add more install instructions).

Run (TODO add testing coverage for CLI version of init_db and other scripts)

```
python ./src/fintrackr/init_db.py <database admin password>
```

from the command line. A bunch of `CREATE` statements should print. This creates the Fintrackr database with owner name `fintrackr_admin` and the login password for `fintrackr_admin` that you specify. `fintrackr_admin` can create the database and create users. Admin name and db name are specified in the `config.yml` file.

Add new users with:

```
python ./src/fintrackr/add_user.py <new user name> <new user password> <db admin password>
```

Users are associated with data they add to the database. They can modify all tables but can't create users/roles; therefore the db owner's password must be passed so the admin can create the new user.

## Dev

This package uses `uv` for package and virtual environment management, based on the very helpful tutorials at [Sebastia Agramunt Puig's blog](https://agramunt.me/posts/python-virtual-environments-with-uv/).

Create the environment with `uv venv .venv` and then run `uv sync --all-extras` (to get developer extras).

Activate with `source .venv/bin/activate`.

Add dependencies with `uv add <package1> <package2>`. If you get an error that looks like:

```
No solution found when resolving dependencies:
  ╰─▶ Because there are no versions of unittest and your project depends on unittest, we can conclude that your project's requirements are
      unsatisfiable.
```
you already have the package (e.g. it's a package that comes with all python installs). I love `uv` but its error messages can be quite unhelpful.

Use `pytest` to run the tests. (For quick debugging: Add `-s` or `--capture=no` to print print statements to console.)

Quick manual testing/debugging setup using the tools in `testing_utils.py`:

```
import fintrackr.testing_utils as utils
params = utils.config_params()
FinDB = utils.set_up_test_DB(params=params)
```

When done, run in the Terminal:

```
dropdb test_fin_db
dropuser test_user
dropuser test_admin
```

To regenerate the schema diagram, run `python src/fintrackr/SQL_to_EDL.py src/fintrackr/schema.sql`. A file `schema_EDL.txt` will appear in `src/fintrackr`.

## TODO 
- Automatically infer transactions to ignore (e.g. credit card payments from checking account, if have both lists of transactions and can compare)?
- Infer, or at least check, recurring charges and their frequencies
- Have a "MANUAL" category that requires manual intervention - e.g. Amazon transactions can't be categorized just from credit card data.