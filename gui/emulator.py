"""Module for a PyGame emulator"""

from __future__ import print_function

import pygame
import pygame.key
from luma.emulator import device
from gui import constants
from gui.base import BaseEvent
from gui.base import BeerGUI


class Emulator(BeerGUI):
  """Implements a GUI with luma emulator"""

  EVENT_DICT = {
      pygame.NOEVENT: constants.EVENTTYPES.NOEVENT,
      pygame.K_UP: constants.EVENTTYPES.KEYUP,
      pygame.K_DOWN: constants.EVENTTYPES.KEYDOWN
  }

  def Setup(self): # pylint: disable=arguments-differ
    """Sets up the device."""
    self.device = device.pygame()

  def GetEvent(self):
    """TODO"""
    event = pygame.event.poll()
    new_event = None
    if event.type == pygame.KEYDOWN:
      new_event = BaseEvent(self.EVENT_DICT.get(event.key, None))
    else:
      raise Exception('lol')
    return new_event


# vim: tabstop=2 shiftwidth=2 expandtab
