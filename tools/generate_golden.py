"""Tool to generate a set of golden images for tests"""
import multiprocessing

from beerlog import beerlogdb
from beerlog.gui import achievements
from beerlog.gui import display


class FakeLumaDevice():
  """Fake LumaDevice to provide proper sizes"""
  def __init__(self):
    self.width = 128
    self.height = 64
    self.size = (self.width, self.height)


def Generate(achievement, destination):
  """Generate a golden image for an achievement"""
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
  image_data = d._DrawAchievement(achievement)  # pylint: disable=protected-access
  image_data.save(destination)
  print('wrote '+destination)

a_arr = [
        [achievements.FirstBeerAchievement('toto'), 'first.ppm'],
        [achievements.SelfVolumeAchievement(12, 'toto'), 'selfvol12.ppm'],
        [achievements.BeatSomeoneAchievement(1), 'newrank1.ppm'],
        [achievements.BeatSomeoneAchievement(2), 'newrank2.ppm'],
        [achievements.BeatSomeoneAchievement(3), 'newrank3.ppm']
        ]
for a, name in a_arr:
  Generate(a, name)
