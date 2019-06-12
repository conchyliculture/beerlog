"""Module for a PyGame emulator"""

from __future__ import print_function

import pygame
import pygame.key
from luma.emulator import device
from gui import constants
from gui.base import UIEvent
from gui.base import LumaDevice


class Emulator(LumaDevice):
  """Implements a GUI with luma emulator"""

  EVENT_DICT = {
      pygame.NOEVENT: constants.EVENTTYPES.NOEVENT,
      pygame.K_UP: constants.EVENTTYPES.KEYUP,
      pygame.K_DOWN: constants.EVENTTYPES.KEYDOWN
  }

  def Setup(self): # pylint: disable=arguments-differ
    """Sets up the device."""
    self._device = device.pygame()

  def GetEvent(self):
    """TODO"""
    pygame_event = pygame.event.poll()
    if pygame_event.type == pygame.KEYDOWN:
      new_event_type = self.EVENT_DICT.get(pygame_event.key, None)
      if new_event_type:
        return UIEvent(new_event_type)
   # else:
      #logging.debug('Unknown PyGame Event: {0!s}'.format(pygame_event))

# vim: tabstop=2 shiftwidth=2 expandtab
