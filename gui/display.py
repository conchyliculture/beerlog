# pylint: disable=missing-docstring

from __future__ import print_function

import time
#from threading import Timer
from transitions import Machine

from luma.core.render import canvas as LumaCanvas
from luma.core.virtual import viewport as LumaViewport
from PIL import Image
from PIL import ImageFont

from gui.constants import Enum
from errors import BeerLogError


class LumaDisplay(object):

  MENU_TEXT_X = 2
  MENU_TEXT_HEIGHT = 10

  STATES = Enum(
      ['SCORE', 'STATS', 'SCANNED', 'ERROR'])

  def __init__(self, events_queue=None):
    self._events_queue = events_queue
    self.luma_device = None
    self._menu_index = 0
    self._text_font = ImageFont.load_default()

    if not self._events_queue:
      raise BeerLogError('Display needs an events_queue')

    self._timedout = False
    self.machine = Machine(
        model=self, states=list(self.STATES), initial=self.STATES.SCORE)

    # Transitions
    # (trigger, source, destination)
    self.machine.add_transition('back', '*', self.STATES.SCORE)
    self.machine.add_transition('stats', self.STATES.SCORE, self.STATES.STATS)
    self.machine.add_transition('scan', '*', self.STATES.SCANNED)
    self.machine.add_transition('error', '*', self.STATES.ERROR)
    self.machine.add_transition(
        'update', '*', self.STATES.SCORE, conditions=['HasTimedout'])

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

  def Splash(self):
    splash = Image.open('pics/splash.png').convert(self.luma_device.mode)
    w, h = splash.size
    virtual = LumaViewport(self.luma_device, width=w, height=h)
    virtual.display(splash)
    time.sleep(2)

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
#          font=self._text_font, fill='black'
#          )
#    else:
#      drawer.text(
#          text_geometry,
#          self.MENU_ITEMS[number],
#          font=self._text_font, fill='white')
#
#  def DrawMenu(self):
#    with LumaCanvas(self.luma_device) as drawer:
#      drawer.rectangle(
#          self.luma_device.bounding_box, outline="white", fill="black")
#      for i in range(len(self.MENU_ITEMS)):
#        self._DrawMenuItem(drawer, i)

  def DrawWho(self, who):
    with LumaCanvas(self.luma_device) as drawer:
      drawer.text((0, 0), who, font=self._text_font, fill="white")

#  def MenuDown(self):
#    self._menu_index = ((self._menu_index + 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()
#
#  def MenuUp(self):
#    self._menu_index = ((self._menu_index - 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()

  def MenuRight(self):
    pass

  def HasTimedout(self):
    """TODO"""
    if self._timedout:
      self._timedout = False
      return True
    return False


# vim: tabstop=2 shiftwidth=2 expandtab
