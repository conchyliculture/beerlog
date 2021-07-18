"""Tests for display.py"""

import multiprocessing
import os
import tempfile
import unittest

import PIL

from beerlog import beerlogdb
from beerlog.gui import achievements
from beerlog.gui import display as beerlog_display

# pylint: disable=protected-access

class FakeLumaDevice():
  """Fake LumaDevice to provide proper sizes"""
  def __init__(self):
    self.width = 128
    self.height = 64
    self.size = (self.width, self.height)


class AchievementsTests(unittest.TestCase):
  """Tests for the Achivements generation"""

  DB_PATH = ':memory:'

  def CheckAgainstGolden(self, display, achievement, golden_path):
    """Makes sure the image matches"""
    with tempfile.NamedTemporaryFile(suffix='.jpg') as temp:
      display._ShowAchievement(achievement, picture=temp.name)
      try:
        self.assertTrue(self.ComparePictures(golden_path, temp.name), (
            'Result picture for {0:s} doesn\'t match "{1:s}"\n'
            'You can generate new golden images using tools/generate_golden.py'
            ).format(achievement.__class__.__name__, golden_path))
      except AssertionError as e:
        (out_f, out_p) = tempfile.mkstemp(suffix='.jpg')
        os.write(out_f, temp.read())
        os.close(out_f)
        print('Test failed, saving screenshot as '+out_p)
        raise e

  def ComparePictures(self, res, expected):
    """Return True if both pictures are the same"""
    result = PIL.Image.open(res)
    golden = PIL.Image.open(expected)
    return PIL.ImageChops.difference(result, golden).getbbox() is None

  def setUp(self):
    self.db = beerlogdb.BeerLogDB(self.DB_PATH)

  def testFirstAchievement(self):
    """Tests achievement display against golden images"""
    achievement = achievements.FirstBeerAchievement('toto')
    events_queue = multiprocessing.Queue()
    d = beerlog_display.LumaDisplay(
        events_queue=events_queue, database=self.db)
    d.luma_device = FakeLumaDevice()

    self.assertEqual(achievement.emoji, '\N{white heavy check mark}')
    self.assertEqual(achievement.message, 'First beer! Have fun toto!')
    self.assertEqual(achievement.big_message, 'FIRST BEER')
    golden_path = 'assets/golden/first.jpg'
    self.CheckAgainstGolden(d, achievement, golden_path)

  def testSelfVolumeAchievement(self):
    """Tests achievement display against golden images"""
    achievement = achievements.SelfVolumeAchievement(12, 'toto')
    events_queue = multiprocessing.Queue()
    d = beerlog_display.LumaDisplay(
        events_queue=events_queue, database=self.db)
    d.luma_device = FakeLumaDevice()

    self.assertEqual(achievement.emoji, '\N{beer mug}')
    self.assertEqual(achievement.message, 'Congrats on passing 12L toto!')
    self.assertEqual(achievement.big_message, '24 PINTS !')
    golden_path = 'assets/golden/selfvol12.jpg'
    self.CheckAgainstGolden(d, achievement, golden_path)

  def testBeatSomeoneAchievement(self):
    """Tests achievement display against golden images"""
    events_queue = multiprocessing.Queue()
    d = beerlog_display.LumaDisplay(
        events_queue=events_queue, database=self.db)
    d.luma_device = FakeLumaDevice()

    achievement = achievements.BeatSomeoneAchievement(1)
    self.assertEqual(achievement.emoji, '\N{first place medal}')
    self.assertEqual(achievement.message, 'YOU HAVE TAKEN THE LEAD !!!')
    self.assertEqual(achievement.big_message, 'WATCH OUT!')
    golden_path = 'assets/golden/newrank1.jpg'
    self.CheckAgainstGolden(d, achievement, golden_path)

    achievement = achievements.BeatSomeoneAchievement(2)
    self.assertEqual(achievement.emoji, '\N{second place medal}')
    self.assertEqual(achievement.message, 'Congrats on taking rank 2!')
    self.assertEqual(achievement.big_message, '1 TO GO!')
    golden_path = 'assets/golden/newrank2.jpg'
    self.CheckAgainstGolden(d, achievement, golden_path)

    achievement = achievements.BeatSomeoneAchievement(3)
    self.assertEqual(achievement.emoji, '\N{third place medal}')
    self.assertEqual(achievement.message, 'Congrats on taking rank 3!')
    self.assertEqual(achievement.big_message, '2 TO GO!')
    golden_path = 'assets/golden/newrank3.jpg'
    self.CheckAgainstGolden(d, achievement, golden_path)
