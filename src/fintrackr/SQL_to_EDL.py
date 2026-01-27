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

    type_conversions = {
        "integer":"int", 
        "text": "string"
        }

    if not os.path.isfile(schema_file_path):
        # Laziness, not bothering with a logger for this
        print(f"convert_to_EDL: {schema_file_path} not a path to a file that exists")
        return output_file_path
    if not os.path.splitext(schema_file_path)[1] == ".sql":
        print(f"convert_to_EDL: {schema_file_path} not a sql file")
        return output_file_path
    
    output_file_path = os.path.splitext(schema_file_path)[0]+"_EDL.txt"
    
    with open(schema_file_path, "r") as f:
        sql_lines = list(f)
    
    edl_lines = []

    # take only the CREATE TABLEs
    curr_line_idx = 0
    while curr_line_idx < len(sql_lines):
        if sql_lines[curr_line_idx][:11] == "CREATE TABLE":
            table_name = sql_lines[curr_line_idx][13].upper()+ sql_lines[curr_line_idx][14:-2]
            edl_lines.append(table_name)
            edl_lines.append("-")
            edl_lines.append(table_name+"ID PK int")
            curr_line_idx = curr_line_idx+2
        elif sql_lines[curr_line_idx][-2]=="\n":
            # Skip this line
            curr_line_idx = curr_line_idx+1
        else:
            next_elements = sql_lines[curr_line_idx].split()
            # strip underscores, capitalize next letter
            col_name = next_elements[0]
            new_col_name = re.sub("_",lambda x: col_name[x.start()+1].upper(),col_name)
            # capitalize first letter
            new_col_name = new_col_name[0].upper() + new_col_name[1:]

            col_type = next_elements[1]
            if col_type in type_conversions:
                col_type = type_conversions["col_type"]

            new_line = col_name + " " + col_type

            if len(next_elements) > 2:
                if next_elements[2] != "REFERENCES":
                    raise ValueError(f"Expected REFENCES next, got {next_elements[2]}")
                ref_table_name = next_elements[3].split("(")[0]
                ref_table_name = ref_table_name[0].upper() + ref_table_name[1:]
                ref_piece = " FK >- " + ref_table_name + "." + ref_table_name + "ID"
                new_line = new_line + ref_piece

            edl_lines.append(new_line)

            curr_line_idx = curr_line_idx+1
    
    edl_out = "\n".join(edl_lines)

    with open(output_file_path, "w") as out_f:
        out_f.write(edl_out)

    return output_file_path
    


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise TypeError("SQL_to_EDL.py takes exactly one input arg (path to SQL file)")
    
    output_file_path = convert_to_EDL(schema_file_path=sys.argv[1])