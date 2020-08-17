"""Tests for display.py"""

import multiprocessing
import os
import unittest

from beerlog import beerlogdb
from beerlog.gui import display


class DisplayTests(unittest.TestCase):
  """Tests for the Display class."""

  DB_PATH = ':memory:'

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

  def tearDown(self):
    if self.DB_PATH != ':memory:':
      os.remove(self.DB_PATH)

  def testAchievementsLitre(self):
    """Tests for the GetAchievements() method."""

    events_queue = multiprocessing.Queue()
    d = display.LumaDisplay(
        events_queue=events_queue, database=self.db)

    self.db.AddEntry('0x0', 'pic')
    achievements = d.GetAchievements('toto')
    self.assertEqual(achievements[0].message, 'First beer, enjoy the run!')

    # Go just over 5L
    for _ in range(14):
      self.db.AddEntry('0x0', 'pic')

    achievements = d.GetAchievements('toto')
    self.assertEqual(achievements[0].message, 'Cheers toto! 4.95L')

    self.db.AddEntry('0x0', 'pic')
    achievements = d.GetAchievements('toto')
    self.assertEqual(
        achievements[0].message, 'Congrats on the 5L toto, keep it up!')

    self.db.AddEntry('0x5', 'pic')
    achievements = d.GetAchievements('tyty')
    self.assertEqual(len(achievements), 2)
    self.assertEqual(
        achievements[0].message, 'First beer, enjoy the run!')
    self.assertEqual(
        achievements[1].message, 'Congrats on the 1L tyty, keep it up!')
