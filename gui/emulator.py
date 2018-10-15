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
      pygame.NOEVENT: constants.NOEVENT,
      pygame.K_UP: constants.KEYUP,
      pygame.K_DOWN: constants.KEYDOWN
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
    return new_event


# vim: tabstop=2 shiftwidth=2 expandtab
