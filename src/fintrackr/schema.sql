/* Naming conventions:

tables: plural, lower case, words separated by underscores
primary key: always "id"
foreign keys: x_id, using singular for x

*/

/* using an enum to enforce correctness */
CREATE TYPE category_label AS ENUM(
    "groceries_and_household", "eating_out", "Amazon", 
    "gas_and_fastrack", "always_unexpected", 
    "house_maintenance", "car_maintenance",
    "clothes_etc", "splurges", "pets", "travel"
);
CREATE TYPE frequency AS ENUM(
    "monthly", "annual"
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount float NOT NULL,
    category_id integer REFERENCES categories(id)
);

CREATE TABLE categories(
    id SERIAL PRIMARY KEY,
    label category_label,
    recurrance frequency,
    source text
);

CREATE TABLE incomes(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount float NOT NULL,
    category_id integer REFERENCES categories(id)
);