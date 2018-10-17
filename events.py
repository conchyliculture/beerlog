"""Module for beerlog events"""

from datetime import datetime


class Enum(tuple): __getattr__ = tuple.index


class BaseEvent(object):
  """Base Event type for the main process Loop.o

    Attributes:
      timestamp(datetime.datetime): the time when the event was generated.
      type(str): a type for this event.
  """

  def __init__(self, event_type):
    self.timestamp = datetime.now()
    self.type = event_type


class UIEvent(BaseEvent):
  """Subclass of BaseEvent for UI events."""

  TYPES = Enum(
    ['NOEVENT', 'KEYUP', 'KEYDOWN', 'KEYLEFT', 'KEYRIGHT', 'KEYENTER',
     'KEYBACK', 'NFCSCANNED'])

  def __str__(self):
    return 'UIEvent type:{0:s} [{1!s}]'.format(
      self.TYPES[self.type], self.timestamp)

# vim: tabstop=2 shiftwidth=2 expandtab
