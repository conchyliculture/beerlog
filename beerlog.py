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
from beernfc import BeerNFC
from errors import BeerLogError
from events import UIEvent
from gui.display import LumaDisplay


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
    self._known_tags = None
    self.dblog = []
    self._dblog_index = 0
    self._last_taken_picture = None
    self._picture_dir = None
    self._should_beep = None

  def InitNFC(self, path=None):
    """Initializes the NFC reader.

    Args:
      path(str): the option path to the device.
    """
    self.nfc_reader = BeerNFC(
      events_queue=self._events_queue, should_beep=self._should_beep)
    self.nfc_reader.OpenNFC(path=path)
    self.nfc_reader.process.start()

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

    args = parser.parse_args()

    self._capture_command = args.capture_command
    self._database_path = args.database
    self._known_tags = args.known_tags
    self._picture_dir = args.picture_dir
    self._should_beep = args.should_beep

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
    for entry in self.db.GetAllLog():
      self.dblog.insert(0, self._EntryToText(entry))

  def Main(self):
    """Runs the script."""
    self.ParseArguments()
    self.InitDB()
    self.LoadTagsDB()
    self.InitNFC(path="usb")
    time.sleep(1)

    if not self.nfc_reader.process.is_alive():
      logging.error('Error loading NFC reader')
      raise BeerLogError('We fail')

    logging.debug('Finished loading NFC')
    self.InitUI()
    logging.debug('Finished loading UI')
    self.Loop()

  def _DrawLastLog(self, num=6):
    self.ui.DrawLog(self.dblog[self._dblog_index:num+self._dblog_index])

  def InitUI(self):
    """Initialises the user interface."""
    # Only GUI for now
    self.ui = LumaDisplay(events_queue=self._events_queue)
    self.ui.Setup()
    self._DrawLastLog()

  def Loop(self):
    """Main loop"""
    while True:
      if not self.nfc_reader.process.is_alive():
        logging.error('NFC Reader process has terminated. Exiting')
        raise BeerLogError('We fail')
      event = self._events_queue.get()
      if event:
        self._HandleEvent(event)
      time.sleep(0.05)

  def _HandleEvent(self, event):
    """Handles incoming BaseEvent.

    Args:
      event(BaseEvent): the event to process
    """
    if event.type == UIEvent.TYPES.NFCSCANNED:
      who = self.GetNameFromTag(event.uid)
      #self._last_taken_picture = self.TakePicture(self._capture_command)
      entry = self.db.AddEntry(character=who, pic=None)
      self.dblog.insert(0, self._EntryToText(entry))
      self._DrawLastLog()
    elif event.type == UIEvent.TYPES.KEYDOWN:
      #self.ui.MenuDown()
      pass
    elif event.type == UIEvent.TYPES.KEYUP:
      #self.ui.MenuUp()
      pass

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

    file_path = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S.jpg')
    cmd = '{0} "{1}"'.format(
      command, os.path.join(self._picture_dir, file_path))
    logging.debug('Running {0}'.format(cmd))
    subprocess.call('{0} "{1}"'.format(cmd, file_path), shell=True)
    return file_path

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

  @staticmethod
  def _EntryToText(entry):
    return '{0:s} - {1:s}'.format(
        entry.character.rjust(6)[0:10], entry.timestamp.strftime('%H:%M:%S'))
    pass


if __name__ == '__main__':
  m = BeerLog()
  m.Main()

# vim: tabstop=2 shiftwidth=2 expandtab
