"""Saves constants used for event handling"""


class Enum(tuple):
  """Helper class to define an enum in python."""
  __getattr__ = tuple.index


EVENTTYPES = Enum(
    ['NOEVENT', 'KEYUP', 'KEYDOWN', 'KEYLEFT', 'KEYRIGHT', 'KEYENTER',
     'KEYBACK', 'KEYPRESS', 'KEYMENU1', 'KEYMENU2', 'KEYMENU3', 'NFCSCANNED',
     'ESCAPE', 'ERROR'])

DEFAULT_GLASS_SIZE = 50
SCAN_RATE_LIMIT = 2 * 60 # 2 minutes
