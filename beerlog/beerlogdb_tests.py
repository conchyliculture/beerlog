"""Tests for the beerlogdb module"""

from __future__ import unicode_literals

import unittest

import beerlogdb

# pylint: disable=protected-access

class BeerLogDBTests(unittest.TestCase):
  """Tests for the BeerLogDB class."""

  def setUp(self):
    self.beerlogdb = beerlogdb.BeerLogDB(':memory:')

  def testAddEntry(self):
    """Tests the AddEntry() method."""
    self.beerlogdb.AddEntry('char1', 'pic1')
    self.beerlogdb.AddEntry('char1', 'pic1')
    self.assertEqual(self.beerlogdb.CountAll(), 2)

  def testGetScoreBoard(self):
    """Tests the GetScoreBoard method."""
    self.beerlogdb.AddEntry('a', 'pic1')
    self.beerlogdb.AddEntry('a', 'pic2')
    self.beerlogdb.AddEntry('a', 'pic3')
    self.beerlogdb.AddEntry('a', 'pic4')
    self.beerlogdb.AddEntry('b', 'pic1')
    self.beerlogdb.AddEntry('b', 'pic2')
    self.beerlogdb.AddEntry('a', 'pic6')
    results = [
        (t.id, t.character, t.count, t.pic)
        for t in self.beerlogdb.GetScoreBoard().execute()]
    expected = [(7, u'a', 5, u'pic6'), (6, u'b', 2, u'pic2')]
    self.assertEqual(expected, results)
