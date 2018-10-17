# pylint: disable=missing-docstring

from __future__ import print_function

import os

from PIL import Image
from PIL import ImageFont
from PIL import ImageSequence
from threading import Thread, Event
from time import sleep
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import viewport

from errors import BeerLogError


class LumaDevice(object):
  """Wrapper around a luma device."""

  def __init__(self):
    self._luma_device = None

  def Loop(self, main_queue):
    Thread(target=self._Loop, args=(main_queue,)).start()

  def _Loop(self, main_queue):
    while True:
      main_queue.put(self.GetEvent())
      sleep(0.05)

  def GetDevice(self):
    return self._luma_device

  def GetEvent(self):
    """Returns an event for the main queue.

     Polled by the main's Loop() in beerlog.py

     Returns:
       UIEvent: the event.
     """
    raise NotImplementedError('Please implement GetEvent')

  def Setup(self, **kwargs):
    """Sets up the device"""
    pass


class LumaDisplay(object):
  MENU_ITEMS = ['un', 'deux', 'trois', 'douze']

  MENU_TEXT_X = 2
  MENU_TEXT_HEIGHT = 10

  def _MakeFont(self, font_file):
    font_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
    font_dir = os.path.abspath(font_dir)
    font_path = os.path.join(font_dir, font_file)
    return ImageFont.truetype(font_path, 10)

  def __init__(self, events_queue=None):
    self._main_events_queue = events_queue
    self.luma_device = None
    self._is_in_menu = False
    self._menu_index = 0
#    self._text_font = self._MakeFont('pixelmix.ttf')
    self._text_font = ImageFont.load_default()
    if not self._main_events_queue:
      raise BeerLogError('Display needs a main_events_queue')

  def Setup(self):
    is_rpi = False
    try:
      with open('/sys/firmware/devicetree/base/model', 'r') as model:
        is_rpi = model.read().startswith('Raspberry Pi')
    except IOError:
      pass

    if is_rpi:
      from gui import sh1106
      device = sh1106.WaveShareOLEDHat()
    else:
      print('Is not a RPI, running PyGame')
      from gui import emulator
      device = emulator.Emulator()

    device.Setup()
    device.Loop(self._main_events_queue)
    self.luma_device = device.GetDevice()

  def DrawLog(self, text_list):
    """Draws a list of text strings"""
    with canvas(self.luma_device) as drawer:
      for line_num in range(len(text_list)):
        text_geometry = ( self.MENU_TEXT_X, line_num * self.MENU_TEXT_HEIGHT )
        drawer.text(
          text_geometry, text_list[line_num],
          font=self._text_font, fill='white')

  def _DrawMenuItem(self, drawer, number):
    """Draws a Menu item.

    Args:
      drawer(luma.core.render.canvas): the canvas
      number(int): the position of the menu item.
    """
    selected = self._menu_index == number
    rectangle_geometry = (
      self.MENU_TEXT_X,
      number * self.MENU_TEXT_HEIGHT,
      self.luma_device.width,
      ((number + 1) * self.MENU_TEXT_HEIGHT)
    )
    text_geometry = (
      self.MENU_TEXT_X,
      number * self.MENU_TEXT_HEIGHT
    )
    if selected:
      drawer.rectangle(
        rectangle_geometry, outline='white', fill='white')
      drawer.text(
        text_geometry,
        self.MENU_ITEMS[number],
        font=self._text_font, fill='black'
      )
    else:
      drawer.text(
        text_geometry,
        self.MENU_ITEMS[number],
        font=self._text_font, fill='white')

  def DrawMenu(self):
    """Draws the Menu."""
    self._is_in_menu = True
    with canvas(self.luma_device) as drawer:
      drawer.rectangle(
        self.luma_device.bounding_box, outline="white", fill="black")
      for i in range(len(self.MENU_ITEMS)):
        self._DrawMenuItem(drawer, i)

  def MenuDown(self):
    if not self._is_in_menu:
      return
    self._menu_index = ((self._menu_index + 1) % len(self.MENU_ITEMS))
    self.DrawMenu()

  def MenuUp(self):
    self._menu_index = ((self._menu_index - 1) % len(self.MENU_ITEMS))
    if not self._is_in_menu:
      return
    self.DrawMenu()

  def MenuRight(self):
    pass

  def DrawImage(self, img_path):
    pixel_art = Image.open(img_path).convert(self.luma_device.mode)
    w, h = pixel_art.size
    virtual = viewport(self.luma_device, width=w, height=h)
    virtual.display(pixel_art)

  def _DisplayAnim(self, killswitch, path_to_gif):
    regulator = framerate_regulator(fps=10)
    gif = Image.open(path_to_gif)
    size = [min(*self.luma_device.size)] * 2
    position = (
      (self.luma_device.width - size[0]) // 2,
      self.luma_device.height - size[1]
    )
    for frame in ImageSequence.Iterator(gif):
      if killswitch.isSet():
        return
      with regulator:
        background = Image.new('RGB', self.luma_device.size, 'white')
        background.paste(frame.resize(size, resample=Image.LANCZOS), position)
        self.luma_device.display(background.convert(self.luma_device.mode))



# vim: tabstop=2 shiftwidth=2 expandtab
