"""Module for a PyGame emulator"""

from __future__ import print_function

import pygame
import pygame.key
from luma.emulator import device

from events import UIEvent
from gui.display import LumaDevice


class Emulator(LumaDevice):
  """Implements a GUI with luma emulator"""

  EVENT_DICT = {
    # Defines association between pygame event type and UIEvents types.
    pygame.NOEVENT: UIEvent.TYPES.NOEVENT,
    pygame.K_UP: UIEvent.TYPES.KEYUP,
    pygame.K_DOWN: UIEvent.TYPES.KEYDOWN
  }

  def Setup(self):  # pylint: disable=arguments-differ
    """Sets up the device."""
    self._luma_device = device.pygame()

  def GetEvent(self):
    """Returns an event for the main queue.

     Polled by the main's Loop() in beerlog.py

     Returns:
       UIEvent: the event.
     """
    pygame_event = pygame.event.poll()
    if pygame_event.type == pygame.KEYDOWN:
      new_event_type = self.EVENT_DICT.get(pygame_event.key, None)
      if new_event_type:
        return UIEvent(new_event_type)

# vim: tabstop=2 shiftwidth=2 expandtab
