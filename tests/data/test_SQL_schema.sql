CREATE TYPE recurrance AS ENUM(
    'irregular', 'monthly', 'annual'
);

CREATE TABLE order(
        id SERIAL PRIMARY KEY,
        customer_id integer REFERENCES customer(id),
        total_amount money,
        order_status_id integer REFERENCES orderstatus(id)
);

CREATE TABLE customer(
    id SERIAL PRIMARY KEY,
    name text NOT NULL,
    address text UNIQUE NOT NULL
);

CREATE TABLE orderstatus(
    id SERIAL PRIMARY KEY,
    status string
);