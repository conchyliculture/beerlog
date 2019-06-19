"""Tests for the beerlog module"""

from __future__ import unicode_literals

import json
import tempfile
import unittest

import beerlog
import beerlogdb

# pylint: disable=protected-access

class TestBeerLogDB(unittest.TestCase):
  """Tests for beerlogdb module."""

  def testDB(self):
    """Simple test case."""
    db = beerlogdb.BeerLogDB(':memory:')

    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    entry = db.GetEntryById(saved_entry.id)
    self.assertEqual('pute', entry.character)
    self.assertEqual('race.jpg', entry.pic)

    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    saved_entry = db.AddEntry(character='pute', pic='race.jpg')
    self.assertEqual(3, db.CountAll())

class BeerLogTests(unittest.TestCase):
  """Tests for the BeerLog class."""

  def testBeerLog(self):
    """Simple test case."""
    bl_object = beerlog.BeerLog()

    with tempfile.NamedTemporaryFile(mode='w+') as temp:
      temp.write(json.dumps({'0x0':{'name': 'Kikoo'}}))
      temp.flush()
      bl_object._known_tags = temp.name
      bl_object.LoadTagsDB()
      l = bl_object.known_tags_list
      self.assertEqual(1, len(l))

      self.assertEqual('Kikoo', bl_object.GetNameFromTag('0x0'))

      self.assertEqual(None, bl_object.GetNameFromTag('0x1'))
