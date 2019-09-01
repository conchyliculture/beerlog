"""BeerLog main script"""

from __future__ import print_function

import argparse
import datetime
import logging
import os
from multiprocessing import SimpleQueue
import subprocess
import sys
from threading import Timer
import time

from beerlog import beerlogdb
from beerlog.bnfc import base as nfc_base
from beerlog import constants
from beerlog import events
from beerlog.gui import display


class RepeatTimer(Timer):
  """Timer that keeps on timing."""

  def run(self):
    while not self.finished.wait(self.interval):
      self.function(*self.args, **self.kwargs)

class BeerLog():
  """BeerLog main class.

  Attributes:
    nfc_reader(bnfc.base): the BeerNFC object.
  """

  def __init__(self):
    self.nfc_reader = None
    self.ui = None
    self.db = None
    self._capture_command = None
    self._database_path = None
    self._events_queue = SimpleQueue()
    self._disable_nfc = False
    self._known_tags = None
    self._last_taken_picture = None
    self._last_scanned_names = {}
    self._picture_dir = None
    self._should_beep = None

    self._timers = []
    self._updater = RepeatTimer(1, self.PushEvent, args=(events.NopEvent(),))
    self._updater.start()

  def InitNFC(self, path=None):
    """Initializes the NFC reader.

    Args:
      path(str): the option path to the device.
    """
    if not self._disable_nfc:
      self.nfc_reader = nfc_base.BeerNFC(
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
    parser.add_argument(
        '--disable_nfc', dest='disable_nfc', action='store_true',
        help='Disables the NFC reader (useful in emulator mode)')

    args = parser.parse_args()

    self._capture_command = args.capture_command
    self._database_path = args.database
    self._known_tags = args.known_tags
    self._picture_dir = args.picture_dir
    self._should_beep = args.should_beep
    self._disable_nfc = args.disable_nfc

    if args.debug:
      logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
      logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    if not os.path.isdir(args.picture_dir):
      # TODO more checks
      os.mkdir(args.picture_dir)

  def InitDB(self):
    """Initializes the BeerLogDB object."""
    self.db = beerlogdb.BeerLogDB(self._database_path)
    self.db.LoadTagsDB(self._known_tags)

  def Main(self):
    """Runs the script."""
    self.ParseArguments()
    self.InitDB()
    self.InitNFC(path="usb")
    self.InitUI()
    self.Loop()

  def InitUI(self):
    """Initialises the user interface."""
    # Only GUI for now
    self.ui = display.LumaDisplay(
        events_queue=self._events_queue, database=self.db)
    self.ui.Setup()
    self.ui.Update()

  def PushEvent(self, event):
    """Adds an Event object in the events queue.

    Args:
      event(events.BaseEvent): the event to push.
    """
    self._events_queue.put(event)

  def AddDelayedEvent(self, event, timeout):
    """Adds an Event object in the events queue after a delay.

    Args:
      event(events.BaseEvent): the event to push.
      timeout(int): the number of seconds after which the event will be pushed.
    """
    t = Timer(timeout, self.PushEvent, args=(event,))
    t.start()
    self._timers.append(t)

  def ResetTimers(self):
    """Reset all timers set for timed events, cancelling the BaseEvent delivery
    to the events queue."""
    for timer in self._timers:
      timer.cancel()

  def Loop(self):
    """Main program loop.

    Looks for any new event in the main progrem Queue and processes them.
    """
    while True:
      event = self._events_queue.get()
      if event:
        try:
          self._HandleEvent(event)
        except Exception as e:  #pylint: disable=broad-except
          logging.error(e)
          err_event = events.ErrorEvent('{0!s}'.format(e))
          self.PushEvent(err_event)

      time.sleep(0.05)
      self.ui.Update()

  def _HandleEvent(self, event):
    """Does something with an Event.

    Args:
      event(BaseEvent): the event to handle.
    Raises:
      BeerLogError: if an error is detected when handling the event.
    """
    # TODO : have a UI class of events, and let the ui object deal with them
    self.ResetTimers()
    if event.type == constants.EVENTTYPES.NFCSCANNED:
      too_soon = False
      name = self.db.GetNameFromHexID(event.uid)
      delta = constants.SCAN_RATE_LIMIT * 2
      if name in self._last_scanned_names:
        delta = (datetime.datetime.now() - self._last_scanned_names.get(name))
        delta = delta.total_seconds()
      self._last_scanned_names[name] = datetime.datetime.now()

      if delta < constants.SCAN_RATE_LIMIT:
        too_soon = True
      else:
        self.db.AddEntry(event.uid, self._last_taken_picture)
      self.ui.machine.scan(who=name, too_soon=too_soon)
      self.AddDelayedEvent(events.UIEvent(constants.EVENTTYPES.ESCAPE), 2)
    elif event.type == constants.EVENTTYPES.KEYUP:
      self.ui.machine.up()
    elif event.type == constants.EVENTTYPES.KEYDOWN:
      self.ui.machine.down()
    elif event.type == constants.EVENTTYPES.ESCAPE:
      self.ui.machine.back()
    elif event.type == constants.EVENTTYPES.KEYMENU1:
      self.ui.machine.back()
    elif event.type == constants.EVENTTYPES.ERROR:
      self.ui.machine.error(error=str(event))
    elif event.type == constants.EVENTTYPES.NOEVENT:
      self.ui.Update()
    else:
      err_msg = 'Unknown Event: {0!s}'.format(event)
      print(err_msg)
      self.PushEvent(events.ErrorEvent(err_msg))
      #self.AddDelayedEvent(UIEvent(constants.EVENTTYPES.ESCAPE), 3)

    self.db.Close()

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


def Main():
  """Main function"""
  m = BeerLog()
  m.Main()

if __name__ == '__main__':
  Main()
# vim: tabstop=2 shiftwidth=2 expandtab
