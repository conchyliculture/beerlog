"""Tests for beerlog modules"""

from __future__ import print_function

import json
import tempfile
import unittest

from beerlog import BeerLog
from beerlogdb import BeerLogDB

# pylint: disable=protected-access

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

class TestBeerLog(unittest.TestCase):
  """Tests for beerlog module."""

  def testBeerLog(self):
    """Simple test case."""
    bl_object = BeerLog()

    with tempfile.NamedTemporaryFile() as temp:
      temp.write(json.dumps({'0x0':{'name': 'Kikoo'}}))
      temp.flush()
      bl_object._known_tags = temp.name
      bl_object.LoadTagsDB()
      l = bl_object.known_tags_list
      self.assertEqual(1, len(l))

      self.assertEqual('Kikoo', bl_object.GetNameFromTag('0x0'))

      self.assertEqual(None, bl_object.GetNameFromTag('0x1'))


if __name__ == '__main__':
  unittest.main()

# vim: tabstop=2 shiftwidth=2 expandtab
