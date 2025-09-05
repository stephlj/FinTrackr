
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
    expense_category text REFERENCES categories(id)
);

CREATE TABLE categories(
    id SERIAL PRIMARY KEY,
    category text NOT NULL REFERENCES categories(id),
    label category_label,
    recurrance frequency,
    source text
);

CREATE TABLE incomes(
    id SERIAL PRIMARY KEY,
    posted_date date NOT NULL,
    amount float NOT NULL,
    income_category text REFERENCES categories(id)
);