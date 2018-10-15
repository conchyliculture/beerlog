"""Base module for a BeerLog GUI"""

class BeerGUI(object):
  """Base class for a BeerLog GUI"""

  def __init__(self):
    self.device = None

  def GetEvent(self):
    """TODO"""
    return None

  def Setup(self, *args, **kwargs):
    """Sets up the device"""
    pass

  def GetDevice(self):
    """Returns the initialized device."""
    if self.device:
      return self.device
    else:
      raise Exception('Device most likely not initialized')

class BaseEvent(object):
  """TODO"""

  def __init__(self, event_type):
    self.type = event_type

# vim: tabstop=2 shiftwidth=2 expandtab
