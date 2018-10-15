# pylint: disable=missing-docstring

from __future__ import print_function

<<<<<<< HEAD
from time import sleep
from PIL import ImageFont
from luma.core.render import canvas as LumaCanvas
from gui import constants
=======
import sys
from PIL import ImageFont

from luma.core.render import canvas as LumaCanvas
from luma.emulator import device

import pygame
import pygame.key
>>>>>>> 272bdd96eb847d33a0111980b5772255f3efe478


class Display(object):

  MENU_ITEMS = ['un', 'deux', 'trois', 'douze']

  MENU_TEXT_X = 2
  MENU_TEXT_HEIGHT = 10

  def __init__(self, luma_device):
    self._menu_index = 0
    self._text_font = ImageFont.load_default()

    self.luma_device = luma_device

  def _DrawMenuItem(self, drawer, number):
    selected = self._menu_index == number
    rectangle_geometry = (
        self.MENU_TEXT_X,
        number * self.MENU_TEXT_HEIGHT,
        self.luma_device.width,
        ((number+1) * self.MENU_TEXT_HEIGHT)
        )
    text_geometry = (
        self.MENU_TEXT_X,
        number*self.MENU_TEXT_HEIGHT
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
    with LumaCanvas(self.luma_device) as drawer:
      drawer.rectangle(
          self.luma_device.bounding_box, outline="white", fill="black")
      for i in range(len(self.MENU_ITEMS)):
        self._DrawMenuItem(drawer, i)

  def MenuDown(self):
    self._menu_index = ((self._menu_index + 1)%len(self.MENU_ITEMS))
    self.DrawMenu()

  def MenuUp(self):
    self._menu_index = ((self._menu_index - 1)%len(self.MENU_ITEMS))
    self.DrawMenu()

  def MenuRight(self):
    pass


if __name__ == '__main__':
  is_rpi = False
  try:
    with open('/sys/firmware/devicetree/base/model', 'r') as model:
      is_rpi = model.read().startswith('Raspberry Pi')
  except IOError:
    pass

  if is_rpi:
    from gui import sh1106
    g = sh1106.WaveShareOLEDHat()
  else:
    print('Is not a RPI, running PyGame')
    from gui import emulator
    g = emulator.Emulator()
  g.Setup()
  m = Display(g.GetDevice())
  m.DrawMenu()

  while True:
    event = g.GetEvent()
    if event:
      if event.type == constants.KEYUP:
        m.MenuUp()
      elif event.type == constants.KEYDOWN:
        m.MenuDown()
      elif event.type == constants.KEYRIGHT:
        m.MenuRight()
    sleep(0.02)

# vim: tabstop=2 shiftwidth=2 expandtab
