"""TODO"""


class Enum(tuple): __getattr__ = tuple.index


EVENTTYPES = Enum(
  ['NOEVENT', 'KEYUP', 'KEYDOWN', 'KEYLEFT', 'KEYRIGHT', 'KEYENTER', 'KEYBACK',
   'NFCSCANNED'])
