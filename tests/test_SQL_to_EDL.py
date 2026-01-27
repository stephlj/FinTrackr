import unittest
import os

from fintrackr.SQL_to_EDL import convert_to_EDL

class TestEDLConverter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sql_file_path = os.path.join(os.getcwd(),"tests","data","test_SQL_schema.sql")
        cls.correct_output_path = os.path.join(os.getcwd(),"tests","data","test_EDL.txt")
        cls.new_output_path = os.path.splitext(cls.sql_file_path)[0]+"_EDL.txt"
    
    @classmethod
    def tearDownClass(cls):
        if os.path.isfile(cls.new_output_path):
            os.remove(cls.new_output_path)

    def test_SQL_to_EDL(self):
        
        converted_path = convert_to_EDL(self.sql_file_path)

        with open(converted_path, "r") as f1:
            converted_lines = list(f1)

        with open(self.correct_output_path, "r") as f2:
            correct_lines = list(f2)

        combined = set(converted_lines) | set(correct_lines)

        self.AssertEqual(len(combined), 0, "Converted SQL and ground truth EDL do not match")