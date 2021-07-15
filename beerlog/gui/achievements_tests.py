"""Tests for display.py"""

import filecmp
import multiprocessing
import os
import tempfile
import unittest

from beerlog import beerlogdb
from beerlog.gui import achievements
from beerlog.gui import display

# pylint: disable=protected-access

class FakeLumaDevice():
  """TODO"""
  def __init__(self):
    self.width = 128
    self.height = 64
    self.size = (self.width, self.height)


class AchievementsTests(unittest.TestCase):
  """TODO"""

  DB_PATH = ':memory:'

  def _LoadGolden(self, name):
    """TODO"""
    return os.path.join('assets/golden', name)

  def setUp(self):
    self.db = beerlogdb.BeerLogDB(self.DB_PATH)
    self.db.known_tags_list = {
        '0x0': {'name': 'toto', 'glass': 33},
        '0x1': {'name': 'toto', 'glass': 45},
        '0x2': {'name': 'tutu', 'glass': 50},
        '0x3': {'name': 'tata', 'glass': 40},
        '0x4': {'name': 'titi', 'glass': 40},
        '0x5': {'name': 'tyty', 'glass': 100}
    }

  def testFirstAchievement(self):
    """TODO"""
    achievement = achievements.FirstBeerAchievement('toto')
    events_queue = multiprocessing.Queue()
    d = display.LumaDisplay(
        events_queue=events_queue, database=self.db)
    d.luma_device = FakeLumaDevice()

    self.assertEqual(achievement.emoji, '1️')
    self.assertEqual(achievement.message, 'First beer, enjoy the game toto!')
    self.assertEqual(achievement.big_message, 'FIRST BEER')

    with tempfile.NamedTemporaryFile(suffix='.jpg') as temp:
      d._ShowAchievement(achievement, picture=temp.name)
      self.assertTrue(filecmp.cmp(self._LoadGolden('first.jpg'), temp.name))
