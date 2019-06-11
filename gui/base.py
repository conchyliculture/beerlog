"""Base module for a BeerLog GUI"""

from datetime import datetime
from gui import constants


class LumaDevice(object):
  """Wrapper around a luma device."""

  def __init__(self, queue):
    self._device = None
    self.queue = queue

  def GetDevice(self):
    """TODO"""
    return self._device

  def Setup(self, **kwargs):
    """Sets up the device"""
    pass


class BaseEvent(object):
  """TODO"""

  def __init__(self, event_type):
    self.timestamp = datetime.now()
    self.type = event_type


class UIEvent(BaseEvent):
  """TODO"""

  def __str__(self):
    return 'UIEvent type:{0:s} [{1!s}]'.format(
        constants.EVENTTYPES[self.type], self.timestamp)

# vim: tabstop=2 shiftwidth=2 expandtab
