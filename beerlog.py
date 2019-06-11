"""BeerLog main script"""

from __future__ import print_function

import argparse
import datetime
import json
import logging
import os
from multiprocessing.queues import SimpleQueue
import subprocess
import sys
import time

from beerlogdb import BeerLogDB
from bnfc.base import BeerNFC
from bnfc.base import FakeNFC
from errors import BeerLogError
from gui.display import LumaDisplay
from gui import constants


class BeerLog(object):
  """BeerLog main class.

  Attributes:
    nfc_reader(bnfc.base): the BeerNFC object.
  """

  def __init__(self):
    self.nfc_reader = None
    self.ui = None
    self.db = None
    self.known_tags_list = None
    self._capture_command = None
    self._database_path = None
    self._events_queue = SimpleQueue()
    self._fake_nfc = False
    self._known_tags = None
    self._last_taken_picture = None
    self._picture_dir = None
    self._should_beep = None

  def InitNFC(self, path=None):
    """Initializes the NFC reader.

    Args:
      path(str): the option path to the device.
    """
    if self._fake_nfc:
      self.nfc_reader = FakeNFC(events_queue=self._events_queue)
    else:
      self.nfc_reader = BeerNFC(
          events_queue=self._events_queue, should_beep=self._should_beep,
          path=path)
    self.nfc_reader.process.start()
    logging.debug('Started NFC {0!s}'.format(self.nfc_reader))

  def ParseArguments(self):
    """Parses arguments.

    Returns:
      argparse.NameSpace: the parsed arguments.
    """

    parser = argparse.ArgumentParser(description='BeerLog')
    parser.add_argument(
        '--nobeep', dest='should_beep', action='store_false',
        default=False, # TODO Change
        help='Disable beeping of the NFC reader')
    parser.add_argument(
        '--capture', dest='capture_command', action='store',
        help=(
            'Picture capture command. Output filename will be appended. '
            'Exemple: "fswebcam -r 1280x720. -S 10"')
    )
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
    parser.add_argument(
        '--dir', dest='picture_dir', action='store',
        default='pics',
        help='Where to store the pictures')
    parser.add_argument(
        '--fake_nfc', dest='fake_nfc', action='store_true',
        help='Uses a fake NFC reader that will sometimes tag things')

    args = parser.parse_args()

    self._capture_command = args.capture_command
    self._database_path = args.database
    self._known_tags = args.known_tags
    self._picture_dir = args.picture_dir
    self._should_beep = args.should_beep
    self._fake_nfc = args.fake_nfc

    if args.debug:
      logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
      logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    if not os.path.isdir(args.picture_dir):
      # TODO more checks
      os.mkdir(args.picture_dir)

  def InitDB(self):
    """Initializes the BeerLogDB object."""
    self.db = BeerLogDB(self._database_path)

  def Main(self):
    """Runs the script."""
    self.ParseArguments()
    self.InitDB()
    self.LoadTagsDB()
    self.InitNFC(path="usb")
    self.InitUI()
    self.Loop()

  def InitUI(self):
    """Initialises the user interface."""
    # Only GUI for now
    self.ui = LumaDisplay(events_queue=self._events_queue)
    self.ui.Setup()
    self.ui.DrawMenu()

  def Loop(self):
    """Main program loop.

    Looks for any new event in the main progrem Queue and processes them.
    """
    while True:
      event = self._events_queue.get()
      if event:
        self._HandleEvent(event)
      time.sleep(0.05)

  def _HandleEvent(self, event):
    """TODO"""
    # TODO : have a UI class of events, and let the ui object deal with them
    if event.type == constants.EVENTTYPES.NFCSCANNED:
      who = self.GetNameFromTag(event.uid)
      self.ui.DrawWho(who)
      logging.debug('Got a scan event from {0}'.format(who))
    # self.db.AddEntry(character=who, pic=self._last_taken_picture)
    #      self._last_taken_picture = self.TakePicture(self._capture_command)
    elif event.type == constants.EVENTTYPES.KEYDOWN:
      self.ui.MenuDown()
    elif event.type == constants.EVENTTYPES.KEYUP:
      self.ui.MenuUp()
    else:
      print('Unknown Event:')
      print(event)

    self.db.Close()

  def LoadTagsDB(self):
    """Loads the external known tags list.

    Raises:
      BeerLogError: if we couldn't load the file.
    """
    try:
      with open(self._known_tags, 'r') as json_file:
        self.known_tags_list = json.load(json_file)
    except IOError as e:
      raise BeerLogError(
          'Could not load known tags file {0} with error {1!s}'.format(
              self._known_tags, e))
    except ValueError as e:
      raise BeerLogError(
          'Known tags file {0} is invalid: {1!s}'.format(
              self._known_tags, e))

  def TakePicture(self, command):
    """Takes a picture.

    Args:
      command(str): command to be run after a filename is appended to it.

    Returns:
      str: the path to the (hopefully created) picture, or None if no command
        was passed.
    """
    if not command:
      return None

    filepath = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S.jpg')
    cmd = '{0} "{1}"'.format(
        command, os.path.join(self._picture_dir, filepath))
    logging.debug('Running {0}'.format(cmd))
    subprocess.call('{0} "{1}"'.format(cmd, filepath), shell=True)

    return filepath

  def GetNameFromTag(self, uid):
    """Returns the corresponding name from a uid

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      str: the corresponding name for that tag uid, or None if no name is found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      return None

    return tag_object.get('name')

  def TagUidToName(self, uid):
    """TODO"""
    return self.known_tags_list.get(uid).get('name')


if __name__ == '__main__':
  m = BeerLog()
  m.Main()

# vim: tabstop=2 shiftwidth=2 expandtab
