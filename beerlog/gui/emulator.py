"""Module for a PyGame emulator"""

from __future__ import print_function

from luma.emulator import device
import pygame
import pygame.key
from beerlog import constants
from beerlog import events

class Emulator():
  """Implements a GUI with luma emulator"""

  EVENT_DICT = {
      pygame.NOEVENT: constants.EVENTTYPES.NOEVENT,
      pygame.K_UP: constants.EVENTTYPES.KEYUP,
      pygame.K_DOWN: constants.EVENTTYPES.KEYDOWN
  }

  def __init__(self, queue):
    self._emulator = None
    self._last_event = None
    self.queue = queue

  def Setup(self): # pylint: disable=arguments-differ
    """Sets up the device."""
    self._emulator = device.pygame()

  def GetEvent(self):
    """TODO"""
    pygame_event = pygame.event.poll()
    if pygame_event.type == pygame.KEYDOWN:
      new_event_type = self.EVENT_DICT.get(pygame_event.key, None)
      if new_event_type:
        return UIEvent(new_event_type)
   # else:
      #logging.debug('Unknown PyGame Event: {0!s}'.format(pygame_event))
    return None

  def GetDevice(self):
    """TODO"""
    return self._emulator

# vim: tabstop=2 shiftwidth=2 expandtab
