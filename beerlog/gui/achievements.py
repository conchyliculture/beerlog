"""Module for managing achievements."""

import textwrap

DEFAULT_ACHIEVEMENT_FRAME = 'assets/pics/achievement.png'

class BaseAchievement():
  """Base class for an Achievement."""

  def __init__(self, message, big_message, emoji='👍'):
    """Initializes a BaseAchievement.

    Args:
      message(str): the message to display (max 40 characters).
      big_message(str): an additional 'title' (max 10 characters).
      emoji(str): an emoji to display.
    """
    self.message = message
    self.big_message = big_message
    self.emoji = emoji

  def Splitted(self, length=14):
    """Splits self.message into strings of max length."""
    return textwrap.wrap(self.message, length)


class SelfVolumeAchievement(BaseAchievement):
  """Class for a 'number of L drunk' achievement."""

  def __init__(self, amount, name):
    m = 'Congrats on passing {0:d}L {1:s}!'.format(amount, name)
    b = '{0:d} PINTS !'.format(amount * 2)
    e = '🍺'
    super().__init__(m, b, e)

class BeatSomeoneAchievement(BaseAchievement):
  """Class for an achievement when someone takes over someone else."""

  def __init__(self, position):
    m = 'Congrats on taking rank {0:d}!'.format(position)
    b = '{0:d} TO GO !'.format(position - 1)
    e = '🍺'
    if position == 1:
      m = 'YOU HAVE TAKEN THE LEAD !!!'
      b = 'WATCH OUT'
      e = '🥇'
    elif position == 2:
      e = '🥈'
    elif position == 3:
      e = '🥉'
    super().__init__(m, b, e)

class FirstBeerAchievement(BaseAchievement):
  """First beer of the game."""

  def __init__(self, name):
    super().__init__(
        'First beer, enjoy the game {0:s}!'.format(name),
        'FIRST BEER', emoji='1️')
