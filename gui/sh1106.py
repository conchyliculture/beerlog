"""Module for a WaveShare 1.3" OLED Hat"""

from __future__ import print_function

from Queue import Queue

from luma.core.interface.serial import i2c, spi
from luma.oled.device import sh1106
import RPi.GPIO as GPIO

from gui import constants
from gui.base import BaseEvent
from gui.base import BeerGUI


class WaveShareOLEDHat(BeerGUI):
  """Implements a GUI with a WaveShare 1.3" OLED Hat"""

  RST_PIN = 25
  CS_PIN = 8
  DC_PIN = 24
  KEY_UP_PIN = 6
  KEY_DOWN_PIN = 19
  KEY_LEFT_PIN = 5
  KEY_RIGHT_PIN = 26
  KEY_PRESS_PIN = 13
  KEY1_PIN = 21
  KEY2_PIN = 20
  KEY3_PIN = 16

  def __init__(self):
    super(WaveShareOLEDHat, self).__init__()
    self._serial = None
    self._events_queue = Queue()

  def _SetupOneGPIO(self, channel):
    """TODO"""
    GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(channel, GPIO.RISING, callback=self._AddEvent)

  def _SetupGPIO(self):
    """TODO"""
    #init GPIO
    GPIO.setmode(GPIO.BCM)
    for channel in [
        self.KEY_UP_PIN,
        self.KEY_DOWN_PIN,
        self.KEY_LEFT_PIN,
        self.KEY_RIGHT_PIN,
        self.KEY_PRESS_PIN,
        self.KEY1_PIN,
        self.KEY2_PIN,
        self.KEY3_PIN]:
      self._SetupOneGPIO(channel)

  def _AddEvent(self, channel):
    new_event = None
    print('got event {0!s}'.format(channel))
    if channel == self.KEY_UP_PIN:
      new_event = BaseEvent(constants.KEYUP)
    elif channel == self.KEY_DOWN_PIN:
      new_event = BaseEvent(constants.KEYDOWN)
    elif channel == self.KEY_RIGHT_PIN:
      new_event = BaseEvent(constants.KEYRIGHT)
    elif channel == self.KEY_LEFT_PIN:
      new_event = BaseEvent(constants.KEYLEFT)
    self._events_queue.put(new_event)

  def Setup(self, connection='spi'):
    """Sets up the device.

    Args:
      connection(str): how do we connect to the WaveShare Hat.
    Raises:
      Exception: if we didn't specify the connection parameter correctly.
    """
    if connection == 'spi':
      self._serial = spi(
          device=0, port=0, bus_speed_hz=8000000,
          transfer_size=4096,
          gpio_DC=self.DC_PIN,
          gpio_RST=self.RST_PIN)
    elif connection == 'i2c':
      GPIO.setup(self.RST_PIN, GPIO.OUT)
      GPIO.output(self.RST_PIN, GPIO.HIGH)
      self._serial = i2c(port=1, address=0x3c)
    else:
      raise Exception('Need "spi" or "i2c" as connection type')

    self._SetupGPIO()

    self.device = sh1106(self._serial, rotate=0) #sh1106


  def GetEvent(self):
    return self._events_queue.get()



# vim: tabstop=2 shiftwidth=2 expandtab
