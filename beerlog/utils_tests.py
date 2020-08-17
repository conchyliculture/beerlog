"""Tests for the beerlog module"""

from __future__ import unicode_literals

from datetime import datetime
import unittest

from beerlog import utils


class TestUtils(unittest.TestCase):
  """Tests for the utils module."""

  def testGetShortAmountOfBeer(self):
    """Tests the _GetShortLastBeer() method."""
    self.assertEqual(utils.GetShortAmountOfBeer(0), '   0')
    self.assertEqual(utils.GetShortAmountOfBeer(1.01), '1.01')
    self.assertEqual(utils.GetShortAmountOfBeer(1.28), '1.28')
    self.assertEqual(utils.GetShortAmountOfBeer(1.88), '1.88')
    self.assertEqual(utils.GetShortAmountOfBeer(10.21), '10.2')
    self.assertEqual(utils.GetShortAmountOfBeer(10.91), '10.9')
    self.assertEqual(utils.GetShortAmountOfBeer(99.11), '99.1')
    self.assertEqual(utils.GetShortAmountOfBeer(99.91), ' 100')
    self.assertEqual(utils.GetShortAmountOfBeer(999), ' 999')
    self.assertEqual(utils.GetShortAmountOfBeer(999.5), 'DEAD')
    self.assertEqual(utils.GetShortAmountOfBeer(1000), 'DEAD')
    self.assertEqual(utils.GetShortAmountOfBeer(9999), 'DEAD')

  def testGetShortLastBeer(self):
    """Tests the _GetShortLastBeer() method."""
    now = datetime(2019, 4, 3, 2, 1, 10)

    last = datetime(2017, 1, 1, 1, 1)
    self.assertEqual(' 2yr', utils.GetShortLastBeer(last, now=now))

    last = datetime(2019, 1, 1, 1, 1)
    self.assertEqual(' 3mo', utils.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 1, 1, 1)
    self.assertEqual('  2d', utils.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 0, 1, 2)
    self.assertEqual('2h8s', utils.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 2, 0, 0)
    self.assertEqual('1m10', utils.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 2, 1, 0)
    self.assertEqual(' 10s', utils.GetShortLastBeer(last, now=now))

    last = now
    self.assertEqual('  0s', utils.GetShortLastBeer(last, now=now))

    last = datetime(2029, 4, 3, 2, 1)
    self.assertEqual('Unk?', utils.GetShortLastBeer(last, now=now))


if __name__ == "__main__":
  unittest.main()
