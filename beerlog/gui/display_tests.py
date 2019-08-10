"""Tests for the beerlog module"""

from __future__ import unicode_literals

from datetime import datetime
import unittest

from beerlog.gui import display


class TestDisplay(unittest.TestCase):
  """Tests for the display module."""

  def testGetShortAmountOfBeer(self):
    """Tests the _GetShortLastBeer() method."""
    self.assertEqual(display.GetShortAmountOfBeer(0), '  0')
    self.assertEqual(display.GetShortAmountOfBeer(1.01), '  1')
    self.assertEqual(display.GetShortAmountOfBeer(1.28), '1.3')
    self.assertEqual(display.GetShortAmountOfBeer(1.88), '1.9')
    self.assertEqual(display.GetShortAmountOfBeer(10.21), ' 10')
    self.assertEqual(display.GetShortAmountOfBeer(10.91), ' 11')
    self.assertEqual(display.GetShortAmountOfBeer(99.11), ' 99')
    self.assertEqual(display.GetShortAmountOfBeer(99.91), '100')
    self.assertEqual(display.GetShortAmountOfBeer(999), '999')
    self.assertEqual(display.GetShortAmountOfBeer(999.5), 'DED')
    self.assertEqual(display.GetShortAmountOfBeer(1000), 'DED')
    self.assertEqual(display.GetShortAmountOfBeer(9999), 'DED')

  def testGetShortLastBeer(self):
    """Tests the _GetShortLastBeer() method."""
    now = datetime(2019, 4, 3, 2, 1, 10)

    last = datetime(2017, 1, 1, 1, 1)
    self.assertEqual(' 2yr', display.GetShortLastBeer(last, now=now))

    last = datetime(2019, 1, 1, 1, 1)
    self.assertEqual(' 3mo', display.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 1, 1, 1)
    self.assertEqual('  2d', display.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 0, 1, 2)
    self.assertEqual('2h8s', display.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 2, 0, 0)
    self.assertEqual('1m10', display.GetShortLastBeer(last, now=now))

    last = datetime(2019, 4, 3, 2, 1, 0)
    self.assertEqual(' 10s', display.GetShortLastBeer(last, now=now))

    last = now
    self.assertEqual('  0s', display.GetShortLastBeer(last, now=now))

    last = datetime(2029, 4, 3, 2, 1)
    self.assertEqual('Unk?', display.GetShortLastBeer(last, now=now))
