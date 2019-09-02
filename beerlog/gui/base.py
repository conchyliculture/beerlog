"""Module for GUI base classes."""

class BaseGUI():
  """Base class for a GUI object. To be implemented by each class for each
     hardware displays."""

  def __init__(self, queue):
    """initializes a BaseGUI object.

    Args:
      queue(Queue): the shared events queue.
    """
    self.queue = queue
    self._device = None

  def GetDevice(self):
    """Returns the underlying luma device (for drawing)."""
    return self._device

  def Setup(self):
    """Sets up the device."""

  def Terminate(self):
    """Kill any remaining processes used by this class"""
