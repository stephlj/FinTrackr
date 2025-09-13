/* Naming conventions:

tables: plural, lower case, words separated by underscores
primary key: always "id"
foreign keys: x_id, using singular for x

*/

CREATE TYPE recurrance AS ENUM(
    'irregular', 'monthly', 'annual'
);

CREATE TABLE transactions(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount money NOT NULL,
    source text /* e.g., "main card", "primary checking" */
);

CREATE TABLE categorization(
    id SERIAL PRIMARY KEY,
    username text NOT NULL,
    categorization_name text /* if a user wants more than one categorization scheme */ 
);

CREATE TABLE categories(
    id SERIAL PRIMARY KEY,
    label text NOT NULL, /* e.g. "groceries" */
    frequency recurrance DEFAULT 'irregular',
    categorization_id integer NOT NULL REFERENCES categorization(id),
    other text /* optional additional super-category (e.g. "discretionary") */
);

CREATE TABLE transactions_categories_xref(
    id SERIAL PRIMARY KEY,
    transaction_id integer NOT NULL REFERENCES transactions(id),
    category_id integer NOT NULL REFERENCES categories(id)
);