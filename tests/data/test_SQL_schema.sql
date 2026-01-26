CREATE TABLE order(
        id SERIAL PRIMARY KEY,
        customer_id integer REFERENCES customer(id),
        total_amount money,
        order_status_id integer REFERENCES orderstatus(id)
);

CREATE TABLE customer(
    id SERIAL PRIMARY KEY,
    name text,
    address text
);

CREATE TABLE order_status(
    id SERIAL PRIMARY KEY,
    status string
)