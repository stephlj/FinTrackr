import unittest
import matplotlib.pyplot as plt

from datetime import date

import fintrackr.plot_accnt_balances as plot
from fintrackr.utils import Transaction

class TestPlotAccntBalances(unittest.TestCase):
    # The main function in plot_accnt_balances doesn't have testing coverage because it requires db access

    @classmethod
    def setUpClass(cls):
        # TODO probably should make these numbers make sense together (balances and transactions)
        cls.bals = [Transaction(date=date(year=2025,month=9,day=10),amount=5000.00),
                 Transaction(date=date(year=2025,month=9,day=2),amount=10000.00),
                 Transaction(date=date(year=2024,month=2,day=2),amount=2500.00),
                 Transaction(date=date(year=2025,month=8,day=10),amount=25000.02)
                 ]

        cls.trans = [Transaction(date=date(year=2023, month=10, day=5),amount=-200.50),
                 Transaction(date=date(year=2024,month=1,day=1), amount=-250.00),
                 Transaction(date=date(year=2024,month=1,day=1), amount=50.00),
                 Transaction(date=date(year=2024,month=10,day=1), amount=-550.05),
                 Transaction(date=date(year=2025,month=9,day=10), amount=-250.00),
                 Transaction(date=date(year=2025,month=9,day=10), amount=-250.00),
                 Transaction(date=date(year=2025,month=11,day=10), amount=-500.00)
                 ]

    def test_relative_bal_by_date(self):
        # Check relative to zero (which will be earlist transaction date, but EOD)
        rel_bals_1 = plot.relative_bal_by_date(references=[], transactions=self.trans)

        self.assertEqual(rel_bals_1, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=200.50),
                            Transaction(date=date(year=2023, month=10, day=5), amount=0.00), # EOD first transaction date is zero
                            Transaction(date=date(year=2024,month=1,day=1), amount=-250.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=-250.00+50.00),
                            Transaction(date=date(year=2024,month=10,day=1), amount=-250.00+50.00-550.05),
                            Transaction(date=date(year=2025,month=9,day=10), amount=-250.00+50.00-550.05-250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=-250.00+50.00-550.05-250.00-250.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=-250.00+50.00-550.05-250.00-250.00-500.00)
                            ]
                         )
        
        # Check relative to a single date in the middle
        rel_bals_2 = plot.relative_bal_by_date(references = [self.bals[-1]], transactions = self.trans)

        self.assertEqual(rel_bals_2, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=25000.02+200.50+250.00-50.00+550.05),
                            Transaction(date=date(year=2023, month=10, day=5), amount=25000.02+250.00-50.00+550.05),
                            Transaction(date=date(year=2024,month=1,day=1), amount=25000.02-50.00+550.05),
                            Transaction(date=date(year=2024,month=1,day=1), amount=25000.02+550.05),
                            Transaction(date=date(year=2024,month=10,day=1), amount=25000.02),
                            Transaction(date=date(year=2025,month=9,day=10), amount=25000.02-250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=25000.02-250.00-250.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=25000.02-250.00-250.00-500.000)
                            ]
                         )

        # Check relative to a single date at one end
        rel_bals_3 = plot.relative_bal_by_date(references=[self.bals[0]], transactions=self.trans[0:-1])
        self.assertEqual(rel_bals_3, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00+200.50), # This is the additional element - balance at start of day 10/5/23, before first deduction
                            Transaction(date=date(year=2023,month=10,day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00), # After the first transaction (same day as first element)
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05-50.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05),
                            Transaction(date=date(year=2024,month=10,day=1), amount=5000.00+250.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00) # This is the balance after the last transaction on 9/10, by definition
                            ] 
                         )
        
        # Check relative to a single date later than the latest transaction
        rel_bals_4 = plot.relative_bal_by_date(references=[Transaction(date=date(year=2026,month=1,day=1), amount=5000.00)], transactions=self.trans)
        self.assertEqual(rel_bals_4, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=55000.00+500.00+250.00+250.00+550.05-50.00+250.00+200.50),
                            Transaction(date=date(year=2023,month=10,day=5), amount=55000.00+500.00+250.00+250.00+550.05-50.00+250.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=55000.00+500.00+250.00+250.00+550.05-50.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=55000.00+500.00+250.00+250.00+550.05),
                            Transaction(date=date(year=2024,month=10,day=1), amount=55000.00+500.00+250.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=55000.00+500.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=55000.00+500.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=55000.00)# This is still the balance after the last transaction
                            ] 
                         )
        
        # Check relative to a single date at other end
        rel_bals_5 = plot.relative_bal_by_date(references=[Transaction(date=date(year=2023, month=10, day=5), amount=2500.00)], transactions=self.trans)
        self.assertEqual(rel_bals_5, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=2500.00+200.50),
                            Transaction(date=date(year=2023, month=10, day=5), amount=2500.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=2500.00-250.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=2500.00-250.00+50.00),
                            Transaction(date=date(year=2024,month=10,day=1), amount=2500.00-250.00+50.00-550.05),
                            Transaction(date=date(year=2025,month=9,day=10), amount=2500.00-250.00+50.00-550.05-250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=2500.00-250.00+50.00-550.05-250.00-250.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=2500.00-250.00+50.00-550.05-250.00-250.00-500.00)
                            ]
                         )
        
        # Check relative to a single date earlier than the earliest transaction
        rel_bals_6 = plot.relative_bal_by_date(references=[Transaction(date=date(year=2023, month=10, day=4),amount=2500.00)], transactions=self.trans)
        self.assertEqual(rel_bals_6, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=2500.00-200.50),
                            Transaction(date=date(year=2024,month=1,day=1), amount=2500.00-200.50-250.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=2500.00-200.50-250.00+50.00),
                            Transaction(date=date(year=2024,month=10,day=1), amount=2500.00-200.50-250.00+50.00-550.05),
                            Transaction(date=date(year=2025,month=9,day=10), amount=2500.00-200.50-250.00+50.00-550.05-250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=2500.00-200.50-250.00+50.00-550.05-250.00-250.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=2500.00-200.50-250.00+50.00-550.05-250.00-250.00-500.00)
                            ]
                         )

        # Check relative to the most recent date in a list
        rel_bals_7 = plot.relative_bal_by_date(references=self.bals,transactions=self.trans)

        self.assertEqual(rel_bals_7, 
                        [Transaction(date=date(year=2023, month=10, day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00+200.50), 
                            Transaction(date=date(year=2023,month=10,day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00), 
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05-50.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05),
                            Transaction(date=date(year=2024,month=10,day=1), amount=5000.00+250.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=5000.00-500.00)
                            ] 
                         )
        
        # What happens if there are no transactions or balances in the date range?
        rel_bals_8 = plot.relative_bal_by_date(references=[], transactions=[])

        self.assertEqual(rel_bals_8, [])

    def test_plot_balances(self):
        # Just a smoke test (does it run)

        calc_bals = [Transaction(date=date(year=2023, month=10, day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00+200.50), 
                            Transaction(date=date(year=2023,month=10,day=5), amount=5000.00+250.00+250.00+550.05-50.00+250.00), 
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05-50.00),
                            Transaction(date=date(year=2024,month=1,day=1), amount=5000.00+250.00+250.00+550.05),
                            Transaction(date=date(year=2024,month=10,day=1), amount=5000.00+250.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00+250.00),
                            Transaction(date=date(year=2025,month=9,day=10), amount=5000.00),
                            Transaction(date=date(year=2025,month=11,day=10), amount=5000.00-500.00)
                        ]

        plot.plot_balances(all_balances=self.bals, calculated_balances=calc_bals)

        plt.close('all') # may not need this, may get handled by pytest/unittest

    