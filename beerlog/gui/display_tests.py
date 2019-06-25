"""Tests for the beerlog module"""

from __future__ import unicode_literals

from datetime import datetime
import unittest

from beerlog.gui import display


class TestDisplay(unittest.TestCase):
  """Tests for the display module."""

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

    last = datetime(2029, 4, 3, 2, 1)
    self.assertEqual('Unk?', display.GetShortLastBeer(last, now=now))
