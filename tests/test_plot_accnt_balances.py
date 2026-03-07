import unittest
import matplotlib.pyplot as plt

from datetime import date

import fintrackr.plot_accnt_balances as plot

class TestPlotAccntBalances(unittest.TestCase):
    # The main function in plot_accnt_balances doesn't have testing coverage because it requires db access

    @classmethod
    def setUpClass(cls):
        # TODO probably should make these numbers make sense together (balances and transactions)
        cls.bals = [(date(year=2025,month=9,day=10),5000.00),
                 (date(year=2025,month=9,day=2),10000.00),
                 (date(year=2024,month=2,day=2),2500.00),
                 (date(year=2025,month=8,day=10),25000.02)
                 ]

        cls.trans = [(date(year=2023, month=10, day=5),-200.50),
                 (date(year=2024,month=1,day=1), -250.00),
                 (date(year=2024,month=1,day=1), 50.00),
                 (date(year=2024,month=10,day=1), -550.05),
                 (date(year=2025,month=9,day=10), -250.00),
                 (date(year=2025,month=9,day=10), -250.00),
                 (date(year=2025,month=11,day=10), -500.00)]

    def test_relative_bal_by_date(self):
        # Check relative to zero (which will be earlist transaction date, but EOD)
        rel_bals_1 = plot.relative_bal_by_date(rel_to=[], transactions=self.trans)

        self.assertEqual(rel_bals_1, 
                        [(date(year=2023, month=10, day=5), 200.50),
                            (date(year=2023, month=10, day=5), 0.00), # EOD first transaction date is zero
                            (date(year=2024,month=1,day=1), -250.00),
                            (date(year=2024,month=1,day=1), -250.00+50.00),
                            (date(year=2024,month=10,day=1), -250.00+50.00-550.05),
                            (date(year=2025,month=9,day=10), -250.00+50.00-550.05-250.00),
                            (date(year=2025,month=9,day=10), -250.00+50.00-550.05-250.00-250.00),
                            (date(year=2025,month=11,day=10), -250.00+50.00-550.05-250.00-250.00-500.00)]
                         )
        
        # Check relative to a single date in the middle
        rel_bals_2 = plot.relative_bal_by_date(rel_to = [self.bals[-1]], transactions = self.trans)

        self.assertEqual(rel_bals_2, 
                        [(date(year=2023, month=10, day=5), 25000.02+200.50+250.00-50.00+550.05),
                            (date(year=2023, month=10, day=5), 25000.02+250.00-50.00+550.05),
                            (date(year=2024,month=1,day=1), 25000.02-50.00+550.05),
                            (date(year=2024,month=1,day=1), 25000.02+550.05),
                            (date(year=2024,month=10,day=1), 25000.02),
                            (date(year=2025,month=9,day=10), 25000.02-250.00),
                            (date(year=2025,month=9,day=10), 25000.02-250.00-250.00),
                            (date(year=2025,month=11,day=10), 25000.02-250.00-250.00-500.000)]
                         )

        # Check relative to a single date at one end
        rel_bals_3 = plot.relative_bal_by_date(rel_to=[self.bals[0]], transactions=self.trans[0:-1])
        self.assertEqual(rel_bals_3, 
                        [(date(year=2023, month=10, day=5), 5000.00+250.00+250.00+550.05-50.00+250.00+200.50), # This is the additional element - balance at start of day 10/5/23, before first deduction
                            (date(year=2023,month=10,day=5), 5000.00+250.00+250.00+550.05-50.00+250.00), # After the first transaction (same day as first element)
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05-50.00),
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05),
                            (date(year=2024,month=10,day=1), 5000.00+250.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00)] # This is the balance after the last transaction on 9/10, by definition
                         )
        
        # Check relative to a single date later than the latest transaction
        rel_bals_4 = plot.relative_bal_by_date(rel_to=[(date(year=2026,month=1,day=1), 5000.00)], transactions=self.trans)
        self.assertEqual(rel_bals_4, 
                        [(date(year=2023, month=10, day=5), 5000.00+500.00+250.00+250.00+550.05-50.00+250.00+200.50),
                            (date(year=2023,month=10,day=5), 5000.00+500.00+250.00+250.00+550.05-50.00+250.00),
                            (date(year=2024,month=1,day=1), 5000.00+500.00+250.00+250.00+550.05-50.00),
                            (date(year=2024,month=1,day=1), 5000.00+500.00+250.00+250.00+550.05),
                            (date(year=2024,month=10,day=1), 5000.00+500.00+250.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00+500.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00+500.00),
                            (date(year=2025,month=11,day=10), 5000.00)] # This is still the balance after the last transaction
                         )
        
        # Check relative to a single date at other end
        rel_bals_5 = plot.relative_bal_by_date(rel_to=[(date(year=2023, month=10, day=5),2500.00)], transactions=self.trans)
        self.assertEqual(rel_bals_5, 
                        [(date(year=2023, month=10, day=5), 2500.00+200.50),
                         (date(year=2023, month=10, day=5), 2500.00),
                            (date(year=2024,month=1,day=1), 2500.00-250.00),
                            (date(year=2024,month=1,day=1), 2500.00-250.00+50.00),
                            (date(year=2024,month=10,day=1), 2500.00-250.00+50.00-550.05),
                            (date(year=2025,month=9,day=10), 2500.00-250.00+50.00-550.05-250.00),
                            (date(year=2025,month=9,day=10), 2500.00-250.00+50.00-550.05-250.00-250.00),
                            (date(year=2025,month=11,day=10), 2500.00-250.00+50.00-550.05-250.00-250.00-500.00)]
                         )
        
        # Check relative to a single date earlier than the earliest transaction
        rel_bals_6 = plot.relative_bal_by_date(rel_to=[(date(year=2023, month=10, day=4),2500.00)], transactions=self.trans)
        self.assertEqual(rel_bals_6, 
                        [(date(year=2023, month=10, day=5), 2500.00-200.50),
                            (date(year=2024,month=1,day=1), 2500.00-200.50-250.00),
                            (date(year=2024,month=1,day=1), 2500.00-200.50-250.00+50.00),
                            (date(year=2024,month=10,day=1), 2500.00-200.50-250.00+50.00-550.05),
                            (date(year=2025,month=9,day=10), 2500.00-200.50-250.00+50.00-550.05-250.00),
                            (date(year=2025,month=9,day=10), 2500.00-200.50-250.00+50.00-550.05-250.00-250.00),
                            (date(year=2025,month=11,day=10), 2500.00-200.50-250.00+50.00-550.05-250.00-250.00-500.00)]
                         )

        # Check relative to the most recent date in a list
        rel_bals_7 = plot.relative_bal_by_date(rel_to=self.bals,transactions=self.trans)

        self.assertEqual(rel_bals_7, 
                        [(date(year=2023, month=10, day=5), 5000.00+250.00+250.00+550.05-50.00+250.00+200.50), 
                            (date(year=2023,month=10,day=5), 5000.00+250.00+250.00+550.05-50.00+250.00), 
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05-50.00),
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05),
                            (date(year=2024,month=10,day=1), 5000.00+250.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00),
                            (date(year=2025,month=11,day=10), 5000.00-500.00)] 
                         )
        
        # What happens if there are no transactions or balances in the date range?
        rel_bals_8 = plot.relative_bal_by_date(rel_to=[], transactions=[])

        self.assertEqual(rel_bals_8, [])

    def test_plot_balances(self):
        # Just a smoke test (does it run)

        calc_bals = [(date(year=2023, month=10, day=5), 5000.00+250.00+250.00+550.05-50.00+250.00+200.50), 
                            (date(year=2023,month=10,day=5), 5000.00+250.00+250.00+550.05-50.00+250.00), 
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05-50.00),
                            (date(year=2024,month=1,day=1), 5000.00+250.00+250.00+550.05),
                            (date(year=2024,month=10,day=1), 5000.00+250.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00+250.00),
                            (date(year=2025,month=9,day=10), 5000.00),
                            (date(year=2025,month=11,day=10), 5000.00-500.00)]

        plot.plot_balances(all_balances=self.bals, calculated_balances=calc_bals)

        plt.close('all') # may not need this, may get handled by pytest/unittest

    