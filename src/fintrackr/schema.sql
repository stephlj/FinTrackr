/* Naming conventions:

tables: plural, lower case, words separated by underscores
primary key: always "id"
foreign keys: x_id, using singular for x

*/

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount money NOT NULL,
    source text /* e.g., "main card", "primary checking" */
);

CREATE TABLE incomes(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount float NOT NULL,
    source text /* e.g. "gift", "cap gains" */
);

CREATE TABLE categories(
    id SERIAL PRIMARY KEY,
    category_id integer REFERENCES category_labels(id),
    recurrance_id integer REFERENCES recurrance_labels(id),
);

CREATE TABLE category_labels(
    id SERIAL PRIMARY KEY,
    username text NOT NULL,
    label text NOT NULL /* e.g. "groceries" */
);

CREATE TABLE recurrance_labels(
    id SERIAL PRIMARY KEY,
    username text NOT NULL,
    frequency text DEFAULT "irregular" /* e.g. "annual", "monthly" */
);

CREATE TABLE expenses_categories_xref(
    id SERIAL PRIMARY KEY,
    expense_id integer NOT NULL REFERENCES expenses(id),
    category_id integer NOT NULL REFERENCES categories(id),
);

CREATE TABLE incomes_categories_xref(
    id SERIAL PRIMARY KEY,
    income_id integer NOT NULL REFERENCES incomes(id),
    category_id integer NOT NULL REFERENCES categories(id),
);