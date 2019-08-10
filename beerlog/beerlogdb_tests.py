"""Tests for the beerlogdb module"""

from __future__ import unicode_literals

import json
import tempfile
import unittest

from peewee import DoesNotExist

import beerlogdb

# pylint: disable=protected-access

class BeerLogDBTests(unittest.TestCase):
  """Tests for the BeerLogDB class."""

  DB_PATH = ':memory:'

  def testAddEntry(self):
    """Tests the AddEntry() method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.AddEntry('char1', 'pic1')
    db.AddEntry('char1', 'pic1')
    self.assertEqual(db.CountAll(), 2)

  def testGetCharacterFromHexID(self):
    """Tests the CharacterFromHexID() method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.AddEntry('charX', 'picX')
    with self.assertRaises(DoesNotExist):
      db.GetCharacterFromHexID('non-ex')

    result = db.GetCharacterFromHexID('charX')
    self.assertEqual(result.glass, 50)

  def testGetScoreBoard(self):
    """Tests the GetScoreBoard method."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
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
    expected = [(7, char_a, 5, u'pic6'), (8, char_b, 3, u'pic2')]
    results = [
        (t.id, t.character, t.count, t.pic)
        for t in db.GetScoreBoard().execute()]
    self.assertEqual(expected, results)

    db = beerlogdb.BeerLogDB(self.DB_PATH)
    # Same amount, most recent first
    db.AddEntry('a', 'pic2')
    db.AddEntry('b', 'pic2')
    char_a = db.GetCharacterFromHexID('a')
    char_b = db.GetCharacterFromHexID('b')
    expected = [(2, char_b, 1, u'pic2'), (1, char_a, 1, u'pic2')]
    results = [
        (t.id, t.character, t.count, t.pic)
        for t in db.GetScoreBoard().execute()]
    self.assertEqual(expected, results)

  def testTags(self):
    """Test tags name/hexid operations."""
    db = beerlogdb.BeerLogDB(self.DB_PATH)
    db.AddEntry('0x0', '')
    db.AddEntry('0x2', '')

    with tempfile.NamedTemporaryFile(mode='w+') as temp:
      temp.write(json.dumps({
          '0x0':{'name': 'Kikoo'},
          '0x2':{'name': 'name', 'realname': 'realname'}}))
      temp.flush()
      db.LoadTagsDB(temp.name)
      l = db.known_tags_list
      self.assertEqual(2, len(l))

      self.assertEqual('Kikoo', db.GetNameFromHexID('0x0'))
      self.assertEqual('realname', db.GetNameFromHexID('0x2'))

      self.assertEqual(None, db.GetNameFromHexID('0x1'))

      self.assertEqual(db.GetCharacterFromHexID('0x0').name, 'Kikoo')
      self.assertEqual(db.GetCharacterFromHexID('0x2').name, 'realname')
