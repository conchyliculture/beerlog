"""Module for a WaveShare 1.3" OLED Hat"""

from __future__ import print_function

from luma.core.interface.serial import i2c, spi
from luma.oled.device import sh1106

import RPi.GPIO as GPIO

from beerlog import constants
from beerlog import events
from beerlog.gui import base as gui_base


class WaveShareOLEDHat(gui_base.BaseGUI):
  """Implements a GUI with a WaveShare 1.3" OLED Hat"""

  # How do we connect to the OLED hat
  CONNECTION = 'spi'

  # How long to wait, in ms before accepting a new event of the same type
  BOUNCE_MS = 100

  RST_PIN = 25
  CS_PIN = 8
  DC_PIN = 24

  _BUTTON_DICT = {
      # KEY_UP_PIN
      6: constants.EVENTTYPES.KEYDOWN, # Yes.
      # KEY_DOWN_PIN
      19: constants.EVENTTYPES.KEYUP,
      # KEY_LEFT_PIN
      5: constants.EVENTTYPES.KEYRIGHT,
      # KEY_RIGHT_PIN
      26: constants.EVENTTYPES.KEYLEFT,
      # KEY_PRESS_PIN
      13: constants.EVENTTYPES.KEYPRESS,
      # KEY1_PIN
      21: constants.EVENTTYPES.KEYMENU1,
      # KEY2_PIN
      20: constants.EVENTTYPES.KEYMENU2,
      # KEY3_PIN
      16: constants.EVENTTYPES.KEYMENU3,
  }

  def __init__(self, queue):
    super().__init__(queue)
    self._last_event = None
    self._serial = None

  def _SetupOneGPIO(self, channel):
    """Sets one GPIO pin.

    Args:
      channel(int): the Pin number to set.
    """
    GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(channel, GPIO.RISING, callback=self._AddEvent)

  def _SetupGPIO(self):
    """Sets all GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    for channel in self._BUTTON_DICT:
      self._SetupOneGPIO(channel)

  def _AddEvent(self, channel):
    """Adds a new events.UIEvent to the Queue.

    Args:
      channel(int): the pin that was detected.
    """

    event_type = self._BUTTON_DICT.get(channel, None)
    if event_type:
      new_event = events.UIEvent(event_type)
      if self._last_event:
        delta = new_event.timestamp - self._last_event.timestamp
        delta_ms = delta.total_seconds() * 1000
        if delta_ms > self.BOUNCE_MS:
          self.queue.put(new_event)
      else:
        self.queue.put(new_event)
      self._last_event = new_event

  def Setup(self):
    """Sets up the device.

    Raises:
      Exception: if we didn't specify the connection parameter correctly.
    """
    if self.CONNECTION == 'spi':
      self._serial = spi(
          device=0, port=0, bus_speed_hz=8000000,
          transfer_size=4096,
          gpio_DC=self.DC_PIN,
          gpio_RST=self.RST_PIN)
    elif self.CONNECTION == 'i2c':
      GPIO.setup(self.RST_PIN, GPIO.OUT)
      GPIO.output(self.RST_PIN, GPIO.HIGH)
      self._serial = i2c(port=1, address=0x3c)
    else:
      raise Exception('Need "spi" or "i2c" as connection type')

    self._SetupGPIO()

    self._device = sh1106(self._serial, rotate=0)

# vim: tabstop=2 shiftwidth=2 expandtab
