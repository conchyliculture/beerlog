"""Module for GUI base classes."""

from multiprocessing import Queue

from luma.oled.device import sh1106
from luma.emulator.device import pygame

class BaseGUI():
  """Base class for a GUI object. To be implemented by each class for each
     hardware displays."""

  def __init__(self, queue: Queue):
    """Initializes a BaseGUI object.
  
    Args:
      queue(Queue): the shared events queue.
    """
    self.queue: Queue = queue
    self._device: sh1106 | pygame

  def GetDevice(self) -> sh1106 | pygame:
    """Returns the underlying luma device (for drawing)."""
    return self._device

  def Setup(self) -> None:
    """Sets up the device."""

  def Terminate(self) -> None:
    """Kill any remaining processes used by this class"""
