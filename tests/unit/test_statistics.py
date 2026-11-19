import unittest

from mini_rdbms.optimizer.statistics import TableStatistics


class StatisticsTest(unittest.TestCase):
    def test_counts_rows_and_distinct_values(self) -> None:
        statistics = TableStatistics.from_rows(
            [{"id": 1, "kind": "a"}, {"id": 2, "kind": "a"}]
        )
        self.assertEqual(statistics.row_count, 2)
        self.assertEqual(statistics.distinct_values["kind"], 1)
        self.assertEqual(statistics.equality_selectivity("kind"), 1.0)


if __name__ == "__main__":
    unittest.main()
