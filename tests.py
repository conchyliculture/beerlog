"""Tests for beerlog modules"""

from __future__ import print_function

import unittest

from beerlogdb import BeerLogDB

class TestBeerLogDB(unittest.TestCase):
  """Tests for beerlogdb module."""

  def testDB(self):
    """Simple test case."""
    db = BeerLogDB(':memory:')

    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    entry = db.GetEntryById(saved_entry.id)
    self.assertEqual('pute', entry.character)
    self.assertEqual('race.jpg', entry.pic)

    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    self.assertEqual(3, db.CountAll())

if __name__ == '__main__':
  unittest.main()

# vim: tabstop=2 shiftwidth=2 expandtab
