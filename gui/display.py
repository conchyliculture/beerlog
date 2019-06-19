"""TODO"""
from __future__ import print_function

import time
from transitions import Machine

from luma.core.render import canvas as LumaCanvas
from PIL import Image
from PIL import ImageFont

from errors import BeerLogError


class LumaDisplay(object):
  """TODO"""

  MENU_TEXT_X = 2
  MENU_TEXT_HEIGHT = 10

  STATES = ['SPLASH', 'SCORE', 'STATS', 'SCANNED', 'ERROR']

  def __init__(self, events_queue=None, database=None):
    self._events_queue = events_queue
    self._database = database
    self.luma_device = None
    self._font = ImageFont.load_default()

    self._last_scanned = None

    if not self._events_queue:
      raise BeerLogError('Display needs an events_queue')

    if not self._database:
      raise BeerLogError('Display needs a DB object')

    self.machine = Machine(
        states=list(self.STATES), initial='SPLASH', send_event=True)

    # Used to set our attributes from the Machine object
    self.machine._SetEnv = self._SetEnv
    # Transitions
    # (trigger, source, destination)
    self.machine.add_transition('back', '*', 'SCORE')
    self.machine.add_transition('stats', 'SCORE', 'STATS')
    self.machine.add_transition('scan', '*', 'SCANNED', before='_SetEnv')
    self.machine.add_transition('error', '*', 'ERROR')

  def _SetEnv(self, event):
    """Helper method to change some of our attributes on transiton changes.

    Args:
      event(transitions.EventData): the event.
    """
    self._last_scanned = event.kwargs.get('who', None)

  def Update(self):
    """TODO"""
    if self.machine.state == 'SPLASH':
      self.Splash('assets/pics/splash_small.png')
    elif self.machine.state == 'ERROR':
      self.ShowError('ERROR')
    elif self.machine.state == 'SCORE':
      self.ShowScores()
    elif self.machine.state == 'SCANNED':
      self.ShowScanned()

  def ShowScanned(self):
    """Draws the screen showing the last scanned tag."""
    with LumaCanvas(self.luma_device) as drawer:
      drawer.text((10, 10), self._last_scanned, font=self._font, fill="white")

  def ShowScores(self):
    """Draws the Scoreboard screen."""
    scoreboard = self._database.GetScoreBoard()
    with LumaCanvas(self.luma_device) as drawer:
      char_w, char_h = drawer.textsize(' ', font=self._font)
      max_text_width = self.luma_device.width / char_w
      max_name_width = max_text_width-12
      # ie: '  Name      Cnt Last'
      header = '  '+('{:<'+str(max_name_width)+'}').format('Name')+' Cnt Last'
      drawer.text((2, 0), header, font=self._font, fill='white')
      for i, row in enumerate(scoreboard[0:4], start=1):
        # ie: '1.Fox        12 12h'
        #     '2.Dog        10  5m'
        text = str(i)+'.'
        text += ('{0:<'+str(max_name_width)+'}').format(row.character)
        text += ' {0:>3d}'.format(row.count)
        text += ' 12h'
        drawer.text((2, i*char_h), text, font=self._font, fill='white')

  def Setup(self):
    is_rpi = False
    try:
      with open('/sys/firmware/devicetree/base/model', 'r') as model:
        is_rpi = model.read().startswith('Raspberry Pi')
    except IOError:
      pass

    if is_rpi:
      from gui import sh1106
      device = sh1106.WaveShareOLEDHat(self._events_queue)
    else:
      raise Exception('Is not a RPI, bailing out ')
#      from gui import emulator
#      device = emulator.Emulator(self._events_queue)

    device.Setup()
    self.luma_device = device.GetDevice()

  def Splash(self, logo_path):
    """Displays the splash screen

    Args:
      logo_path(str): the relative path to the image.
    """
    background = Image.new(self.luma_device.mode, self.luma_device.size)
    splash = Image.open(logo_path).convert(self.luma_device.mode)
    posn = ((self.luma_device.width - splash.width) // 2, 0)
    background.paste(splash, posn)
    self.luma_device.display(background)
    time.sleep(2)

  def ShowError(self, error):
    """TODO"""
    self.DrawText(error)

  def DrawText(self, text, font=None, x=0, y=0, fill='white'):
    """TODO"""
    with LumaCanvas(self.luma_device) as drawer:
#      drawer.text((0, 0), who, font=self._font, fill="white")
      drawer.text((x, y), text, font=(font or self._font), fill=fill)

#  def _DrawMenuItem(self, drawer, number):
#    selected = self._menu_index == number
#    rectangle_geometry = (
#        self.MENU_TEXT_X,
#        number * self.MENU_TEXT_HEIGHT,
#        self.luma_device.width,
#        ((number+1) * self.MENU_TEXT_HEIGHT)
#        )
#    text_geometry = (
#        self.MENU_TEXT_X,
#        number*self.MENU_TEXT_HEIGHT
#        )
#    if selected:
#      drawer.rectangle(
#          rectangle_geometry, outline='white', fill='white')
#      drawer.text(
#          text_geometry,
#          self.MENU_ITEMS[number],
#          font=self._font, fill='black'
#          )
#    else:
#      drawer.text(
#          text_geometry,
#          self.MENU_ITEMS[number],
#          font=self._font, fill='white')
#
#  def DrawMenu(self):
#    with LumaCanvas(self.luma_device) as drawer:
#      drawer.rectangle(
#          self.luma_device.bounding_box, outline="white", fill="black")
#      for i in range(len(self.MENU_ITEMS)):
#        self._DrawMenuItem(drawer, i)
#
#  def MenuDown(self):
#    self._menu_index = ((self._menu_index + 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()
#
#  def MenuUp(self):
#    self._menu_index = ((self._menu_index - 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()

# vim: tabstop=2 shiftwidth=2 expandtab
