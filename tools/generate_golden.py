import multiprocessing
import os
import tempfile
import unittest

from beerlog import beerlogdb
from beerlog.gui import achievements
from beerlog.gui import display


class FakeLumaDevice():
  """TODO"""
  def __init__(self):
    self.width = 128
    self.height = 64
    self.size = (self.width, self.height)


def generate(achievement, destination):
  """TODO"""
  db = beerlogdb.BeerLogDB(':memory:')
  db.known_tags_list = {
      '0x0': {'name': 'toto', 'glass': 33},
      '0x1': {'name': 'toto', 'glass': 45},
      '0x2': {'name': 'tutu', 'glass': 50},
      '0x3': {'name': 'tata', 'glass': 40},
      '0x4': {'name': 'titi', 'glass': 40},
      '0x5': {'name': 'tyty', 'glass': 100}
  }
  events_queue = multiprocessing.Queue()
  d = display.LumaDisplay(
      events_queue=events_queue, database=db)
  d.luma_device = FakeLumaDevice()
  d._ShowAchievement(achievement, picture=destination)
  print('wrote '+destination)

a_arr = [
        [achievements.FirstBeerAchievement('toto'), 'first.jpg'],
        [achievements.SelfVolumeAchievement(12, 'toto'), 'selfvol12.jpg'],
        [achievements.BeatSomeoneAchievement(2), 'newrank2.jpg']
        ]
for a, name in a_arr:
  generate(a, name)