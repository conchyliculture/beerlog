"""Tests for display.py"""

import multiprocessing
import os
import unittest

from beerlog import beerlogdb
from beerlog.gui import achievements
from beerlog.gui import display

# pylint: disable=protected-access


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
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    a= d.GetAchievements('toto')
    self.assertEqual(len(a), 1)
    self.assertIsInstance(a[0], achievements.FirstBeerAchievement)
    self.assertEqual(a[0].message, 'First beer, enjoy the game toto!')

    self.db.AddEntry('0x2', 'pic')
    self.db.AddEntry('0x3', 'pic')
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    self.db.AddEntry('0x3', 'pic')
    self.db.AddEntry('0x3', 'pic')
    # 'tata' beats 'tutu'
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    a = d.GetAchievements('tata')
    self.assertEqual(a[0].message, 'YOU HAVE TAKEN THE LEAD !!!')

    self.db.AddEntry('0x0', 'pic')
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    a = d.GetAchievements('toto')
    self.assertEqual(a[0].message, 'Congrats on taking rank 2!')

    self.db.AddEntry('0x0', 'pic')
    self.db.AddEntry('0x0', 'pic')
    # Toto takes lead and gets more than 1L
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    a = d.GetAchievements('toto')
    self.assertEqual(a[0].message, 'YOU HAVE TAKEN THE LEAD !!!')
    self.assertEqual(
        a[1].message, 'Congrats on passing 1L toto!')

    # Go just over 5L
    for _ in range(12):
      self.db.AddEntry('0x0', 'pic')
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    a = d.GetAchievements('toto')
    self.assertEqual(
        a[0].message, 'Congrats on passing 5L toto!')

    self.db.AddEntry('0x5', 'pic')
    a = d.GetAchievements('tyty')
    d._scoreboard.UpdateData(self.db.GetScoreBoard())
    self.assertEqual(len(a), 2)
    self.assertEqual(
        a[0].message, 'First beer, enjoy the game tyty!')
    self.assertEqual(
        a[1].message, 'Congrats on passing 1L tyty!')
