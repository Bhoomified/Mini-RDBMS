import unittest

from mini_rdbms import __version__

from mini_rdbms import (
    common,
    parser,
    storage,
    optimizer,
    transactions,
    execution,
    integration,
)


class TestProjectFoundation(unittest.TestCase):

    def test_package_version(self):
        self.assertEqual(__version__, "0.1.0")

    def test_engine_packages_are_importable(self):
        packages = [
            common,
            parser,
            storage,
            optimizer,
            transactions,
            execution,
            integration,
        ]

        self.assertEqual(len(packages), 7)

        for package in packages:
            self.assertIsNotNone(package)


if __name__ == "__main__":
    unittest.main()