"""Run all tests inside the tests folder."""
import unittest
import os
import sys


loader = unittest.TestLoader()
start_dir = os.path.join(os.path.dirname(__file__), 'beerlog')
suite = loader.discover(start_dir, pattern='*_tests.py')

runner = unittest.TextTestRunner()
result = runner.run(suite)
sys.exit(not result.wasSuccessful())
