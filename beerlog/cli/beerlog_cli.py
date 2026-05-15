"""BeerLog main script"""

import argparse
import datetime
from collections import defaultdict
import logging
import multiprocessing
import os
import queue
import subprocess
import sys
from threading import Timer
import time
import traceback

from beerlog import beerlogdb
from beerlog.bnfc import base as nfc_base
from beerlog import constants
from beerlog import events
from beerlog.gui import display


class BeerLog:
  """BeerLog main class.

  Attributes:
    nfc_reader(bnfc.base): the BeerNFC object.
  """

  def __init__(self):
    self.nfc_reader: nfc_base.BaseNFC | None = None
    self.ui: display.LumaDisplay
    self.db: beerlogdb.BeerLogDB
    self._database_path: str
    self._events_queue: multiprocessing.Queue = multiprocessing.Queue()
    self._disable_nfc = False
    self._known_tags_path: str = "known_tags.json"
    self._last_scanned_names = defaultdict(lambda: datetime.datetime(2023, 1, 1))
    self._should_beep = True

    self._timers = []

  def InitNFC(self, path=None):
    """Initializes the NFC reader.

    Args:
      path(str): the option path to the device.
    """
    if not self._disable_nfc:
      self.nfc_reader = nfc_base.BeerNFC(
        events_queue=self._events_queue, should_beep=self._should_beep, path=path
      )
      self.nfc_reader.process.start()
      logging.debug("Started NFC {0!s}".format(self.nfc_reader))

  def ParseArguments(self):
    """Parses arguments."""

    parser = argparse.ArgumentParser(description="BeerLog")
    parser.add_argument(
      "--nobeep",
      dest="should_beep",
      action="store_false",
      default=True,
      help="Disable beeping of the NFC reader",
    )
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", help="Debug mode")
    parser.add_argument(
      "--database",
      dest="database",
      action="store",
      default=os.path.join(os.path.dirname(__name__), "beerlog.sqlite"),
      help='the path to the sqlite file, or ":memory:" for a memory db',
    )
    parser.add_argument(
      "--known_tags",
      dest="known_tags",
      action="store",
      default="known_tags.json",
      help="the known tags file to use to use",
    )
    parser.add_argument(
      "--disable_nfc",
      dest="disable_nfc",
      action="store_true",
      help="Disables the NFC reader (useful in emulator mode)",
    )

    args = parser.parse_args()

    self._database_path = args.database
    self._known_tags_path = args.known_tags
    self._should_beep = args.should_beep
    self._disable_nfc = args.disable_nfc

    if args.debug:
      logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
      logging.basicConfig(stream=sys.stdout, level=logging.INFO)

  def InitDB(self):
    """Initializes the BeerLogDB object."""
    self.db = beerlogdb.BeerLogDB(self._database_path)
    self.db.LoadTagsDB(self._known_tags_path)

  def Main(self):
    """Runs the script."""
    try:
      self.ParseArguments()
      self.InitDB()
      self.InitNFC(path="usb")
      self.InitUI()
      self.Loop()
    except Exception as e:  # pylint: disable=broad-except
      logging.error(e)
      print("An error occurred: {0!s}".format(e))
      print(traceback.format_exc())
    finally:
      self.Terminate()

  def Terminate(self):
    """End all processes & threads."""
    # TODO: make sure DB is saved
    self.ResetTimers()
    if self.nfc_reader:
      if self.nfc_reader.process.is_alive():
        self.nfc_reader.process.kill()
    if self.ui:
      self.ui.Terminate()

  def InitUI(self):
    """Initialises the user interface."""
    # Only GUI for now
    self.ui = display.LumaDisplay(events_queue=self._events_queue, database=self.db)
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
      try:
        event = self._events_queue.get(timeout=1)
        try:
          self._HandleEvent(event)
        except Exception as e:  # pylint: disable=broad-except
          logging.error(e)
          err_event = events.ErrorEvent("{0!s}".format(e))
          self.PushEvent(err_event)
      except queue.Empty:
        pass
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
    assert self.db is not None
    assert self.ui is not None
    assert self.ui.machine is not None
    if event.type == constants.EVENTTYPES.NFCSCANNED:
      too_soon = False
      name = self.db.GetNameFromHexID(event.uid)
      delta = constants.SCAN_RATE_LIMIT * 2
      if name in self._last_scanned_names:
        now = datetime.datetime.now()
        delta = now - self._last_scanned_names.get(
          name, datetime.datetime(now.year, now.month, now.day)
        )
        delta = delta.total_seconds()
      self._last_scanned_names[name] = datetime.datetime.now()

      if delta < constants.SCAN_RATE_LIMIT:
        too_soon = True
      else:
        self.db.AddEntry(event.uid)
      self.ui.machine.scan(who=name, too_soon=too_soon)
      self.AddDelayedEvent(events.UIEvent(constants.EVENTTYPES.ESCAPE), 2)
    elif event.type == constants.EVENTTYPES.KEYUP:
      self.ui.machine.up()
    elif event.type == constants.EVENTTYPES.KEYDOWN:
      self.ui.machine.down()
    elif event.type == constants.EVENTTYPES.KEYLEFT:
      self.ui.machine.left()
    elif event.type == constants.EVENTTYPES.KEYRIGHT:
      self.ui.machine.right()
    elif event.type == constants.EVENTTYPES.ESCAPE:
      self.ui.machine.back()
    elif event.type == constants.EVENTTYPES.KEYMENU1:
      self.ui.machine.menu1()
    elif event.type == constants.EVENTTYPES.KEYMENU2:
      self.ui.machine.menu2()
    elif event.type == constants.EVENTTYPES.KEYMENU3:
      too_soon = False
      name = self.ui._current_character_name
      delta = constants.SCAN_RATE_LIMIT * 2
      if name in self._last_scanned_names:
        now = datetime.datetime.now()
        delta = now - self._last_scanned_names.get(
          name, datetime.datetime(now.year, now.month, now.day)
        )
        delta = delta.total_seconds()
      self._last_scanned_names[name] = datetime.datetime.now()

      if delta < constants.SCAN_RATE_LIMIT:
        too_soon = True
      else:
        self.db.AddNameEntry(name)
      self.ui.machine.scan(who=name, too_soon=too_soon)
      self.AddDelayedEvent(events.UIEvent(constants.EVENTTYPES.ESCAPE), 2)
    elif event.type == constants.EVENTTYPES.ERROR:
      self.ui.machine.error(error=str(event))
      self.AddDelayedEvent(events.UIEvent(constants.EVENTTYPES.ESCAPE), 2)
    elif event.type == constants.EVENTTYPES.NOEVENT:
      self.ui.Update()

    self.db.Close()


def Main():
  """Main function"""
  m = BeerLog()
  m.Main()


if __name__ == "__main__":
  Main()
# vim: tabstop=2 shiftwidth=2 expandtab
