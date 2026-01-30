/* Naming conventions:

tables: plural, lower case, words separated by underscores
primary key: always "id"
foreign keys: x_id, using singular for x

Copyright (c) 2025, 2026 Stephanie Johnson

*/

CREATE TYPE recurrance AS ENUM(
    'irregular', 'monthly', 'annual'
);

CREATE TABLE balances(
    id SERIAL PRIMARY KEY,
    accnt_name text NOT NULL REFERENCES data_sources(id),
    date date NOT NULL,
    amount money NOT NULL
);

CREATE TABLE data_sources(
    id SERIAL PRIMARY KEY,
    name text UNIQUE NOT NULL /* e.g., "credit card", "primary checking" */
);

CREATE TABLE data_load_metadata(
    id SERIAL PRIMARY KEY,
    date_added date NOT NULL,
    username text NOT NULL,
    source text UNIQUE NOT NULL, /* filename */
    data_source_id integer REFERENCES data_sources(id)
);

/* this table preserves the original data */
CREATE TABLE transactions(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount money NOT NULL,
    description text, /* e.g merchant name on cc transaction */
    metadatum_id integer NOT NULL REFERENCES data_load_metadata(id)
);

CREATE TABLE categorizations(
    id SERIAL PRIMARY KEY,
    username text NOT NULL,
    name text /* if a user wants more than one categorization scheme */ 
);

CREATE TABLE categories(
    id SERIAL PRIMARY KEY,
    label text NOT NULL, /* e.g. "groceries" */
    frequency recurrance DEFAULT 'irregular',
    categorization_id integer NOT NULL REFERENCES categorizations(id),
    other text /* optional additional super-category (e.g. "discretionary") */
);

CREATE TABLE transactions_categories_xref(
    id SERIAL PRIMARY KEY,
    transaction_id integer NOT NULL REFERENCES transactions(id),
    category_id integer NOT NULL REFERENCES categories(id)
);