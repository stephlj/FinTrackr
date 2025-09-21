/* Naming conventions:

tables: plural, lower case, words separated by underscores
primary key: always "id"
foreign keys: x_id, using singular for x

*/

CREATE TYPE recurrance AS ENUM(
    'irregular', 'monthly', 'annual'
);

/* this table preserves the original data */
CREATE TABLE transactions(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount money NOT NULL,
    description text, /* e.g merchant name on cc transaction */
    metadatum_id integer NOT NULL REFERENCES data_load_metadata(id)
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

CREATE TABLE data_load_metadata(
    id SERIAL PRIMARY KEY,
    date_added date NOT NULL,
    username text NOT NULL,
    source text UNIQUE NOT NULL, /* filename */
    source_alias integer REFERENCES data_sources(id)
);

CREATE TABLE data_sources(
    id SERIAL PRIMARY KEY,
    source_name text NOT NULL /* e.g., "main card", "primary checking" */
)