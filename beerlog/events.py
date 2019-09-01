"""Module for beerlog events"""

from datetime import datetime

from beerlog import constants


class BaseEvent():
  """Base Event type for the main process Loop.

    Attributes:
      timestamp(datetime.datetime): the time when the event was generated.
      type(str): a type for this event.
  """

  def __init__(self, event_type):
    self.timestamp = datetime.now()
    self.type = event_type

  def __str__(self):
    return self.type

class ErrorEvent(BaseEvent):
  """Event to carry error messages."""

  def __init__(self, message):
    super(ErrorEvent, self).__init__(constants.EVENTTYPES.ERROR)
    self.message = message

  def __str__(self):
    return '{0:s}'.format(self.message)


class NopEvent(BaseEvent):
  """An Event that does nothing."""

  def __init__(self):
    super(NopEvent, self).__init__(constants.EVENTTYPES.NOEVENT)


class UIEvent(BaseEvent):
  """Class for UI related events."""

  def __str__(self):
    return 'UIEvent type:{0:s} [{1!s}]'.format(
        constants.EVENTTYPES[self.type], self.timestamp)

# vim: tabstop=2 shiftwidth=2 expandtab
