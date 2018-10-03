"""BeerLog main script"""

from __future__ import print_function

import argparse
import binascii
import json
import logging
import os
import sys
import time

import nfc

from beerlogdb import BeerLogDB

class BeerLogError(Exception):
  """Custom exception for BeerLog."""
  pass


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


class BeerLog(object):
  """BeerLog main class.

  Attributes:
    args(argparse.NameSpace): Parsed arguments.
    clf(nfc.clf.ContactlessFrontend): the NFC Frontend.
  """

  def __init__(self):
    self.args = None
    self.clf = None
    self.db = None
    self.known_tags_list = None
    self._last_read_uid = None

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

  def ParseArguments(self):
    """Parses arguments.

    Returns:
      argparse.NameSpace: the parsed arguments.
    """

    parser = argparse.ArgumentParser(description='BeerLog')
    parser.add_argument(
        '--nobeep', dest='should_beep', action='store_false',
        default=True,
        help='Disable beeping of the NFC reader')
    parser.add_argument(
        '-d', '--debug', dest='debug', action='store_true',
        help='Debug mode')
    parser.add_argument(
        '--database', dest='database', action='store',
        default=os.path.join(os.path.dirname(__name__), 'beerlog.sqlite'),
        help='the path to the sqlite file, or ":memory:" for a memory db')
    parser.add_argument(
        '--known_tags', dest='known_tags', action='store',
        default='known_tags.json',
        help='the known tags file to use to use')

    args = parser.parse_args()

    if args.debug:
      logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
      logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    self.args = args

  def InitDB(self):
    """Initializes the BeerLogDB object."""
    self.db = BeerLogDB(self.args.database)

  def Main(self):
    """Runs the script."""
    self.ParseArguments()
    self.InitDB()
    self.LoadTagsDB()
    self.OpenNFC(path="usb")
    while True:
      try:
        who = self.ScanNFC()
        print('{0} a bu une biere'.format(who))
      except BeerLogError as _:
        pass
      time.sleep(0.5)

    self.db.Close()

  def LoadTagsDB(self):
    """Loads the external known tags list.

    Raises:
      BeerLogError: if we couldn't load the file.
    """
    try:
      with open(self.args.known_tags, 'r') as json_file:
        self.known_tags_list = json.load(json_file)
    except IOError as e:
      raise BeerLogError(
          'Could not load known tags file {0} with error {1!s}'.format(
              self.args.known_tags, e))
    except ValueError as e:
      raise BeerLogError(
          'Known tags file {0} is invalid: {1!s}'.format(
              self.args.known_tags, e))

  def ReadTag(self, tag):
    """Reads a tag from the NFC reader.

    Args:
      tag(): the tag object to read.

    Returns:
      bytearray: True if the read operation was successful,
        or None if it wasn't.
    """
    if isinstance(tag, nfc.tag.tt2.Type2Tag):
      self._last_read_uid = NFC215.ReadUIDFromTag(tag)
      return self.args.should_beep
    return False

  def GetNameFromTag(self, uid):
    """Returns the corresponding name from a uid

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      str: the corresponding name for that tag uid.
    """
    return self.known_tags_list.get(uid).get('name')

  def ScanNFC(self):
    """Sets the NFC reader into scanning mode.

    Returns:
      str: the name of the character in the tag.
    Raises:
      BeerLogError: if we couldn't read a character from the tag.
    """
    success = self.clf.connect(rdwr={
        'on-connect': self.ReadTag
    })

    if not success:
      raise BeerLogError('Could not read NFC tag')

    if not self._last_read_uid:
      raise BeerLogError('Unknown NFC tag')

    who = self.GetNameFromTag(self._last_read_uid)
    return who


m = BeerLog()
m.Main()

# vim: tabstop=2 shiftwidth=2 expandtab
