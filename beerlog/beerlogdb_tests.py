"""Tests for the beerlogdb module"""

from __future__ import unicode_literals

import datetime
import json
import tempfile
import unittest

from beerlog import beerlogdb

# pylint: disable=protected-access

class BeerLogDBTests(unittest.TestCase):
  """Tests for the BeerLogDB class."""

  DB_PATH = ':memory:'

  def testAddEntry(self):
    """Tests the AddEntry() method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        'char1': {'name': 'toto', 'glass': 33},
        }
    db.AddEntry('char1', 'pic1')
    db.AddEntry('char1', 'pic1')
    self.assertEqual(db.CountAll(), 2)

  def testGetCharacterFromHexID(self):
    """Tests the CharacterFromHexID() method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        'charX': {'name': 'toto', 'glass': 33},
        'charY': {'name': 'toto', 'glass': 45}
        }
    db.AddEntry('charX', 'picX')
    self.assertEqual(db.GetCharacterFromHexID('non-ex'), None)

    result = db.GetCharacterFromHexID('charX')
    self.assertEqual(result.glass, 33)

  def testGetScoreBoard(self):
    """Tests the GetScoreBoard method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        'a': {'name': 'toto', 'glass': 33},
        'b': {'name': 'toto', 'glass': 45}
        }
    db.AddEntry('a', 'pic1')
    db.AddEntry('a', 'pic2')
    db.AddEntry('a', 'pic3')
    db.AddEntry('a', 'pic4')
    db.AddEntry('b', 'pic1')
    db.AddEntry('b', 'pic2')
    db.AddEntry('a', 'pic6')
    db.AddEntry('b', 'pic2')

    char_a = db.GetCharacterFromHexID('a')
    char_b = db.GetCharacterFromHexID('b')
    expected = [(7, char_a, 5 * 33, u'pic6'), (8, char_b, 3 * 45, u'pic2')]
    results = [
        (t.id, t.character, t.amount, t.pic)
        for t in db.GetScoreBoard().execute()]
    self.assertEqual(expected, results)

    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        'a': {'name': 'toto', 'glass': 33},
        'b': {'name': 'toto', 'glass': 45}
        }
    # Same amount, most recent first
    db.AddEntry('a', 'pic2')
    db.AddEntry('b', 'pic2')
    char_a = db.GetCharacterFromHexID('a')
    char_b = db.GetCharacterFromHexID('b')
    expected = [(2, char_b, 1 * 45, u'pic2'), (1, char_a, 1 * 33, u'pic2')]
    results = [
        (t.id, t.character, t.amount, t.pic)
        for t in db.GetScoreBoard().execute()]
    self.assertEqual(expected, results)

  def testGetCharacters(self):
    """Test tags name/hexid operations."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        '0x0': {'name': 'toto', 'glass': 33},
        '0x2': {'name': 'tutu', 'glass': 45}
        }
    db.AddEntry('0x0', 'pic2')
    db.AddEntry('0x2', 'pic2')

    char_a = db.GetCharacterFromHexID('0x0')
    char_b = db.GetCharacterFromHexID('0x2')
    self.assertEqual(
        [char_a, char_b],
        [t for t in db.GetAllCharacters().execute()])

  def testGetAmount(self):
    """Tests for counting total amount drunk per character"""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        '0x0': {'name': 'toto', 'glass': 33},
        '0x2': {'name': 'toto', 'glass': 45}
        }
    db.AddEntry('0x0', '', time=datetime.datetime(2019, 1, 1, 15, 00))
    db.AddEntry('0x0', '', time=datetime.datetime(2019, 1, 1, 16, 00))
    db.AddEntry('0x0', '', time=datetime.datetime(2019, 1, 1, 17, 00))
    db.AddEntry('0x2', '', time=datetime.datetime(2019, 1, 1, 14, 00))
    db.AddEntry('0x2', '', time=datetime.datetime(2019, 1, 1, 16, 30))

    self.assertEqual(
        datetime.datetime(2019, 1, 1, 14, 0), db.GetEarliestTimestamp())
    self.assertEqual(
        datetime.datetime(2019, 1, 1, 17, 0), db.GetLatestTimestamp())

    # 3 scans
    self.assertEqual(3*12, db.GetAmountFromHexID('0x0', 12))

    self.assertEqual(0, db.GetAmountFromHexID(
        '0x0', 12, at=datetime.datetime(2018, 1, 1, 16, 30)))
    self.assertEqual(2*12, db.GetAmountFromHexID(
        '0x0', 12, at=datetime.datetime(2019, 1, 1, 16, 30)))




  def testTags(self):
    """Test tags name/hexid operations."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.known_tags_list = {
        '0x0': {'name': 'toto', 'glass': 33},
        '0x2': {'name': 'toto', 'glass': 45}
        }
    db.AddEntry('0x0', '')
    db.AddEntry('0x2', '')

    with tempfile.NamedTemporaryFile(mode='w+') as temp:
      temp.write(json.dumps({
          '0x0':{'name': 'Kikoo', 'glass': '30'},
          '0x2':{'name': 'name', 'realname': 'realname', 'glass': '45'}}))
      temp.flush()
      db.LoadTagsDB(temp.name)
      l = db.known_tags_list
      self.assertEqual(2, len(l))

      self.assertEqual('Kikoo', db.GetNameFromHexID('0x0'))
      self.assertEqual('realname', db.GetNameFromHexID('0x2'))

      self.assertEqual(None, db.GetNameFromHexID('0x1'))

      self.assertEqual(db.GetCharacterFromHexID('0x0').name, 'Kikoo')
      self.assertEqual(db.GetCharacterFromHexID('0x2').name, 'realname')
