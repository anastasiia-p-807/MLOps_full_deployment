import unittest

import pandas as pd

from apps.evidently.drift_job import calculate_drift


class DriftTests(unittest.TestCase):
    def test_identical_data_has_no_drift(self):
        reference = pd.DataFrame({"first": range(100), "second": range(100)})
        _, share = calculate_drift(reference, reference.copy())
        self.assertEqual(share, 0.0)

    def test_shifted_column_is_detected(self):
        reference = pd.DataFrame({"first": range(100), "second": range(100)})
        current = reference.copy()
        current["first"] += 1000
        _, share = calculate_drift(reference, current)
        self.assertEqual(share, 0.5)

    def test_mismatched_columns_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_drift(pd.DataFrame({"first": [1]}), pd.DataFrame({"second": [1]}))


if __name__ == "__main__":
    unittest.main()
