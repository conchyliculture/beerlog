"""Tests for the beerlogdb module"""

from __future__ import unicode_literals

import datetime
import json
import os
import tempfile
import unittest

from beerlog import beerlogdb
from beerlog import errors

# pylint: disable=protected-access

class BeerLogDBTests(unittest.TestCase):
  """Tests for the BeerLogDB class."""

  DB_PATH = ':memory:'

  def setUp(self):
    self.db = beerlogdb.BeerLogDB(self.DB_PATH)
    self.db.known_tags_list = {
        '0x0': {'name': 'toto', 'glass': 33},
        '0x1': {'name': 'toto', 'glass': 45},
        '0x2': {'name': 'tutu', 'glass': 50},
        '0x3': {'name': 'tata', 'glass': 40},
        '0x4': {'name': 'titi', 'glass': 40}
    }

  def tearDown(self):
    if self.DB_PATH != ':memory:':
      os.remove(self.DB_PATH)

  def testAddEntry(self):
    """Tests the AddEntry() method."""
    self.db.AddEntry('0x0')
    self.db.AddEntry('0x0')
    self.assertEqual(self.db.CountAll(), 2)

  def testGetNameFromHexID(self):
    """Tests the CharacterFromHexID() method."""
    result = self.db.GetNameFromHexID('0x0')
    self.assertEqual(result, 'toto')

    result = self.db.GetNameFromHexID('0x1')
    self.assertEqual(result, 'toto')

  def testGetScoreBoard(self):
    """Tests the GetScoreBoard method."""
    self.db.AddEntry('0x0')
    self.db.AddEntry('0x0')
    self.db.AddEntry('0x0')
    self.db.AddEntry('0x1')
    self.db.AddEntry('0x1')
    self.db.AddEntry('0x4')
    self.db.AddEntry('0x2')
    self.db.AddEntry('0x1')
    self.db.AddEntry('0x2')
    self.db.AddEntry('0x3')

    expected = [
        ('toto', 3 * 33 + 3 * 45, None),
        ('tutu', 2 * 50, None),
        ('titi', 1 * 40, None),# Same amount, but oldest first
        ('tata', 1 * 40, None)
    ]
    results = [
        (t.character_name, t.total, t.pic)
        for t in self.db.GetScoreBoard().execute()]
    self.assertEqual(expected, results)

  def testGetCharacters(self):
    """Test tags name/hexid operations."""
    self.db.AddEntry('0x0', 'pic2')
    self.db.AddEntry('0x2', 'pic2')
    self.assertEqual(['toto', 'tutu'], self.db.GetAllCharacterNames())

  def testGetAmount(self):
    """Tests for counting total amount drunk per character"""
    self.db.AddEntry('0x0', time=datetime.datetime(2019, 1, 1, 15, 00))
    self.db.AddEntry('0x0', time=datetime.datetime(2019, 1, 1, 16, 00))
    self.db.AddEntry('0x1', time=datetime.datetime(2019, 1, 1, 17, 00))
    self.db.AddEntry('0x2', time=datetime.datetime(2019, 1, 1, 14, 00))
    self.db.AddEntry('0x2', time=datetime.datetime(2019, 1, 1, 16, 30))

    self.assertEqual(
        datetime.datetime(2019, 1, 1, 14, 0), self.db.GetEarliestTimestamp())
    self.assertEqual(
        datetime.datetime(2019, 1, 1, 17, 0), self.db.GetLatestTimestamp())

    # 3 scans: 2 with 33 & 1 with 45
    self.assertEqual(2 * 33 + 1 * 45, self.db.GetAmountFromHexID('0x0'))

    # Date too old, getting nothing
    self.assertEqual(0, self.db.GetAmountFromHexID(
        '0x0', at=datetime.datetime(2018, 1, 1, 16, 30)))

    # One scan
    self.assertEqual(1 * 50, self.db.GetAmountFromHexID(
        '0x2', at=datetime.datetime(2019, 1, 1, 15, 30)))

  def testLoadTags(self):
    """Test loading the name/hexid json file."""

    with tempfile.NamedTemporaryFile(mode='w+') as temp:
      temp.write(json.dumps({
          '0x0':{'name': 'Kikoo', 'glass': '30'},
          '0x2':{'name': 'name', 'realname': 'realname', 'glass': '45'}}))
      temp.flush()
      self.db.LoadTagsDB(temp.name)
      l = self.db.known_tags_list
      self.assertEqual(2, len(l))

      self.assertEqual('Kikoo', self.db.GetNameFromHexID('0x0'))
      self.assertEqual('realname', self.db.GetNameFromHexID('0x2'))

      with self.assertRaises(errors.BeerLogError):
        self.assertEqual(None, self.db.GetNameFromHexID('0x1'))

      self.assertEqual(self.db.GetNameFromHexID('0x0'), 'Kikoo')
      self.assertEqual(self.db.GetNameFromHexID('0x2'), 'realname')


if __name__ == "__main__":
  unittest.main()
