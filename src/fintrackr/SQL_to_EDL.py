import os, sys
import re

def convert_to_EDL(schema_file_path: str) -> str:
    """
    Convert the SQL in a schema file to the EDL used for generating schema diagram
    at https://app.quickdatabasediagrams.com.

    Given this SQL:

    CREATE TABLE order(
        id SERIAL PRIMARY KEY,
        customer_id integer REFERENCES customer(id),
        total_amount money,
        order_status_id integer REFERENCES orderstatus(id)
    );

    this is the equivalent EDL (probably caps don't matter?):

    Order
    -
    OrderID PK int
    CustomerID int FK >- Customer.CustomerID
    TotalAmount money
    OrderStatusID int FK >- OrderStatus.OrderStatusID
    
    Parameters
    __________
    schema_file_path: str
        File path to SQL schema    
    
    Return
    ______
    str, path to file with EDL equivalent
    """
    
    output_file_path = ""

    if not os.path.isfile(schema_file_path):
        # Laziness, not bothering with a logger for this
        print(f"convert_to_EDL: {schema_file_path} not a path to a file that exists")
        return output_file_path
    if not os.path.splitext(schema_file_path)[1] == ".sql":
        print(f"convert_to_EDL: {schema_file_path} not a sql file")
        return output_file_path
    
    # read file

    # take only the CREATE TABLEs

    # create output file


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise TypeError("SQL_to_EDL.py takes exactly one input arg (path to SQL file)")
    
    output_file_path = convert_to_EDL(schema_file_path=sys.argv[1])