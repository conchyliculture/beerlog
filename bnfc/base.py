"""BeerLog main script"""

from __future__ import print_function

import binascii
import logging
import multiprocessing
import time

import nfc

from errors import BeerLogError
from gui import constants
from gui.base import BaseEvent


class NFCEvent(BaseEvent):
  """Event for a NFC tag."""

  def __init__(self, uid=None):
    super(NFCEvent, self).__init__(constants.NFCSCANNED)
    self.uid = uid


class NFC215(object):
  """Handles read operations on NFC215 tags."""
  BULK_READ_PAGE_COUNT = 4
  PAGE_SIZE = 4
  TAG_FILE_SIZE = 532

  @staticmethod
  def ReadUIDFromTag(tag):
    """Reads UID from a tag.

    Args:
      tag(nfc.tag.tt2_nxp.NTAG215): the input data read from the tag.
    Returns:
      uid(str): the tag uid in form 0x0580000000050002.
    """
    uid = None
    if tag.product == 'NXP NTAG215':
      bytes_array = tag.read(21)[0:8]
      uid = '0x{0}'.format(binascii.hexlify(bytes_array))
    else:
      logging.debug('Unknown tag product: {0:s}'.format(tag.product))
    return uid

  @staticmethod
  def ReadAllPages(tag):
    """Displays all pages from tag

    Args:
      tag(nfc.tag.tt2_nxp.NTAG215): the input data read from the tag.
    """
    pages = []
    for i in range(0, (NFC215.TAG_FILE_SIZE/NFC215.PAGE_SIZE), 4):
      page = tag.read(i)
      print('{0!s}:{1!s}'.format(i, binascii.hexlify(page).upper()))
      pages.append(binascii.hexlify(page).upper())
    print(''.join(pages))


class BeerNFC(object):
  """BeerNFC class.

  Attributes:
    args(argparse.NameSpace): Parsed arguments.
    clf(nfc.clf.ContactlessFrontend): the NFC Frontend.
  """

  SCAN_TIMEOUT_MS = 3*1000 # 3sec

  def __init__(self, events_queue=None, should_beep=True):
    """Initializes a BeerNFS object.

    Args:
      events_queue(Queue.Queue): the common events queue.
      should_beep(bool): whether to beep when a tag is scanned.

    Raises:
      BeerLogError: if arguments are invalid.
    """
    self._events_queue = events_queue
    self._path = None
    self._should_beep = should_beep

    if not self._events_queue:
      raise BeerLogError('Need an events queue')

    self.clf = None
    self._last_event = None
#    self.db = None
#    self.known_tags_list = None
#    self._capture_command = None
#    self._database_path = None
#    self._known_tags = None
    self._last_read_uid = None
    self.process = None
#    self._last_taken_picture = None
#    self._picture_dir = None
    self._should_beep = None

  def OpenNFC(self, path=None):
    """Inits the NFC reader.

    Args:
      path(str): the option path to the device.

    Raises:
      BeerLogError: when we couldn't open the device.
    """
    try:
      self.clf = nfc.ContactlessFrontend(path=path)
    except IOError as e:
      raise BeerLogError(
          (
              'Could not load NFC reader (path: {0}) with error: {1!s}\n'
              'Try removing some modules (hint: rmmod pn533_usb ; rmmod pn533'
              '; rmmod nfc'
          ).format(path, e))

    self.process = multiprocessing.Process(target=self._DoNFC)

  def _DoNFC(self):
    """TODO"""
    while True:
      uid = self.ScanNFC()
      if not uid:
        continue
      event = NFCEvent(uid=uid)
      self._AddToQueue(event)
      self._last_read_uid = None
      time.sleep(0.1)

  def _AddToQueue(self, event):
    """TODO"""
    if event:
      if self._last_event:
        delta = event.timestamp - self._last_event.timestamp
        delta_ms = delta.total_seconds() * 1000
        if delta_ms > self.SCAN_TIMEOUT_MS:
          self._events_queue.put(event)
      else:
        self._events_queue.put(event)
      self._last_event = event

  def ReadTag(self, tag):
    """Reads a tag from the NFC reader.

    Args:
      tag(nfc.tag): the tag object to read.

    Returns:
      bytearray: True if the read operation was successful,
        or None if it wasn't.
    """
    if isinstance(tag, nfc.tag.tt2.Type2Tag):
      self._last_read_uid = NFC215.ReadUIDFromTag(tag)
      return self._should_beep
    return False


  def ScanNFC(self):
    """Sets the NFC reader into scanning mode. Takes a picture if required.

    Returns:
      str: the uid in the tag.
    Raises:
      BeerLogError: if we couldn't read a character from the tag.
    """

    after5s = lambda: time.time() - started > 1
    started = time.time()
    success = self.clf.connect(
        rdwr={'on-connect': self.ReadTag},
        terminate=after5s
    )

    if not success:
      logging.debug('Could not read NFC tag, or we timedout')
#      raise BeerLogError('Could not read NFC tag')

#    if not self._last_read_uid:
#      raise BeerLogError('Unknown NFC tag')

    return self._last_read_uid

# vim: tabstop=2 shiftwidth=2 expandtab
