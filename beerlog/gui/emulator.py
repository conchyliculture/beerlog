"""Module for a PyGame emulator"""

from __future__ import print_function

import logging
import multiprocessing

try:
  import gi
except Exception as import_error:
  raise Exception('Consider running from a virtualenv built with --system-site-packages') from import_error

try:
  gi.require_version('Gtk', '3.0')
  from gi.repository import Gtk
except:
  raise Exception('Need at least version 3.0 pf pygtk')

from luma.emulator import device

from beerlog import constants
from beerlog import events
from beerlog.bnfc import base as nfc_base
from beerlog.gui import base as gui_base


class Emulator(gui_base.BaseGUI):
  """Implements a GUI with luma emulator"""

  _BUTTON_DICT = {
      'DOWN': constants.EVENTTYPES.KEYDOWN,
      'UP': constants.EVENTTYPES.KEYUP,
      'RIGHT': constants.EVENTTYPES.KEYRIGHT,
      'LEFT': constants.EVENTTYPES.KEYLEFT,
      'CLICK': constants.EVENTTYPES.KEYPRESS,
      'Menu 1': constants.EVENTTYPES.KEYMENU1,
      'Menu 2': constants.EVENTTYPES.KEYMENU2,
      'Menu 3': constants.EVENTTYPES.KEYMENU3,
  }

  def __init__(self, queue):
    super().__init__(queue)
    self.uuid_entry = None
    self.process = None

  def Setup(self):
    """Sets up the device."""
    self._device = device.pygame()
    self.process = multiprocessing.Process(target=self._SetupUI, daemon=True)
    self.process.start()

  def _SetupUI(self):
    """TODO"""

    win = Gtk.Window(title='BeerLog UI')
    outer_container_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # Build a fake WaveShare OLED Hat with a cross & 3 menu buttons
    fake_hat_box = Gtk.Box(spacing=20)

    menu_button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    button_menu1 = Gtk.Button(label='Menu 1')
    button_menu1.connect('clicked', self._OnUIButtonClicked)
    menu_button_box.pack_start(button_menu1, True, True, 0)
    button_menu2 = Gtk.Button(label='Menu 2')
    button_menu2.connect('clicked', self._OnUIButtonClicked)
    menu_button_box.pack_start(button_menu2, True, True, 0)
    button_menu3 = Gtk.Button(label='Menu 3')
    button_menu3.connect('clicked', self._OnUIButtonClicked)
    menu_button_box.pack_start(button_menu3, True, True, 0)

    joystick_grid = Gtk.Grid()
    button_up = Gtk.Button(label='UP')
    button_up.connect('clicked', self._OnUIButtonClicked)
    button_left = Gtk.Button(label='LEFT')
    button_left.connect('clicked', self._OnUIButtonClicked)
    button_click = Gtk.Button(label='CLICK')
    button_click.connect('clicked', self._OnUIButtonClicked)
    button_right = Gtk.Button(label='RIGHT')
    button_right.connect('clicked', self._OnUIButtonClicked)
    button_down = Gtk.Button(label='DOWN')
    button_down.connect('clicked', self._OnUIButtonClicked)
    joystick_grid.attach(button_click, 1, 1, 1, 1)
    joystick_grid.attach_next_to(
        button_right, button_click, Gtk.PositionType.RIGHT, 1, 1)
    joystick_grid.attach_next_to(
        button_left, button_click, Gtk.PositionType.LEFT, 1, 1)
    joystick_grid.attach_next_to(
        button_up, button_click, Gtk.PositionType.TOP, 1, 1)
    joystick_grid.attach_next_to(
        button_down, button_click, Gtk.PositionType.BOTTOM, 1, 1)

    fake_hat_box.add(menu_button_box)
    fake_hat_box.add(joystick_grid)

    # Add a box to trigger fake scans
    fake_scan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    self.uuid_entry = Gtk.Entry()
    self.uuid_entry.set_text('0x0580000000050002')
    scan_button = Gtk.Button(label='Scan TAG')
    scan_button.connect('clicked', self._OnScanButtonClicked)

    fake_scan_box.pack_start(self.uuid_entry, True, True, 0)
    fake_scan_box.pack_start(scan_button, True, True, 0)

    outer_container_box.add(fake_hat_box)
    outer_container_box.add(fake_scan_box)

    win.add(outer_container_box)

    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()

  def _OnUIButtonClicked(self, button):
    """Handle button clicks.

    Args:
      button(GtkButton): the pressed button.
    """
    label = button.get_label()
    event_type = self._BUTTON_DICT.get(label, None)
    if event_type:
      new_event = events.UIEvent(event_type)
      self.queue.put(new_event)
    else:
      logging.warning(
          'Not implemented button: {0:s} (check self._BUTTON_DICT'.format(
              label))

  def _OnScanButtonClicked(self, _):
    """Handle clicking the Scan button."""
    event = nfc_base.NFCEvent(uid=self.uuid_entry.get_text())
    self.queue.put(event)

  def Terminate(self):
    self.process.kill()

# vim: tabstop=2 shiftwidth=2 expandtab
