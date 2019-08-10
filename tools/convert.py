import re
import sys


class Amiibo:
  """Amiibo"""

  PIC_URL = "https://raw.githubusercontent.com/N3evin/AmiiboAPI/master/images/icon_%08x-%08x.png"

  def __init__(self, info):
    self.hexid = None
    match = re.search(r'^0x[a-f0-9]{16}$', info, flags=re.I)
    if match:
      self.hexid = match.group(0)
    else:
      raise Exception('Unknown form {0:s}'.format(info))

  def __str__(self):
    h, t = self.GetHeadTail()
    return """HexID: {0!s}
 Head: {1!s}
 Tail: {2!s}
  URL: {3:s}""".format(self.hexid, h, t, self.GetPicURL())

  def GetHeadTail(self):
    i = int(self.hexid, 16)
    head = (i & 0xFFFFFFFF00000000) >> 32
    tail = (i & 0x00000000FFFFFFFF)
    return (head, tail)

  def GetPicURL(self):
    head, tail = self.GetHeadTail()
    return self.PIC_URL%(head, tail) 



a =  Amiibo(sys.argv[1])
print(a)
