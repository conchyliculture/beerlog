"""Module for managing the display."""

from __future__ import print_function

from collections import namedtuple
import datetime
import os
import time
from transitions import Machine

from luma.core.render import canvas as LumaCanvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import terminal
import PIL

from beerlog import errors
from beerlog import system


DataPoint = namedtuple(
    'DataPoint', ['key', 'value', 'unit'], defaults=['', '', ''])

def GetShortAmountOfBeer(amount):
  """Returns a shortened string for an volume in Litre

  Args:
    amount(float): quantity, in L.
  Returns:
    str: the human readable string.
  """
  if amount >= 999.5:
    return 'DEAD'
  if amount >= 99.5:
    return '{0:>4d}'.format(int(round(amount)))
  return '{0:4.3g}'.format(amount)


def GetShortLastBeer(last, now=None):
  """Returns a shortened string for the delta between now and last scan.

  Args:
    last(datetime.datetime): timestamp of the last scan.
    now(datetime.datetime): an optional time reference.
      The current datetime if None.
  Returns:
    str: the time delta since the last scan and now.
  """
  if not now:
    now = datetime.datetime.now()
  delta = now - last
  seconds = int(delta.total_seconds())
  if seconds == 0:
    return '  0s'
  periods = [
      ('yr', 60*60*24*365),
      ('mo', 60*60*24*30),
      ('d', 60*60*24),
      ('h', 60*60),
      ('m', 60),
      ('s', 1)
  ]
  result = ''
  for period_name, period_seconds in periods:
    if seconds >= period_seconds:
      period_value, seconds = divmod(seconds, period_seconds)
      result += '{0:d}{1:s}'.format(period_value, period_name)
      if period_name not in ['h', 'm']:
        break
      if len(result) >= 4:
        break
  if result == '':
    result = 'Unk?'
  return '{0: >4}'.format(result[0:4])


class Scroller():
  """Implements a scroller object."""

  def __init__(self):
    self._array = []
    self._max_lines = 0

    self.index = None
    self._window_low = 0
    self._array_size = 0
    self._window_high = 0

  def UpdateData(self, data):
    """Sets the data for the scoller object.

    Args:
      data(list): the list of rows to display/scroll through.
    """
    self._array = data
    self._array_size = len(self._array)

  def SetMaxLines(self, lines):
    """Sets the width of the window.

    Args:
      lines(int): the number of lines of the window.
    """
    self._max_lines = lines
    self._window_high = self._window_low + lines

  def GetRows(self):
    """Returns the number of rows to display in the window.

    Returns:
      enumerate(peewee rows): the scoreboard window.
    """
    window = self._array[self._window_low:self._window_high]
    return window

  def IncrementIndex(self):
    """Increments the index. Moves the window bounds if necessary."""
    if self.index is None:
      self.index = 0
    elif self.index < self._array_size - 1:
      self.index += 1
      if self.index > self._window_high:
        self._window_low += 1
        self._window_high += 1

  def DecrementIndex(self):
    """Decrements the index. Moves the window bounds if necessary."""
    if self.index is None:
      self.index = 0
    elif self.index > 0:
      if self.index <= self._window_low:
        self._window_low -= 1
        self._window_high -= 1
      self.index -= 1


class LumaDisplay():
  """Class managing the display."""

  STATES = ['SPLASH', 'SCORE', 'STATS', 'SCANNED', 'ERROR', 'MENUGLOBAL']

  DEFAULT_SPLASH_PIC = 'assets/pics/splash_small.png'
  DEFAULT_SCAN_GIF = 'assets/gif/beer_scanned.gif'

  def __init__(self, events_queue, database):
    self._events_queue = events_queue
    self._database = database
    if not self._events_queue:
      raise errors.BeerLogError('Display needs an events_queue')
    if not self._database:
      raise errors.BeerLogError('Display needs a DB object')

    # Internal stuff
    self.luma_device = None
    self.machine = None
    self._last_scanned_name = None
    self._last_error = None
    self._too_soon = False

    # UI related defaults
    self._font = PIL.ImageFont.load_default()
    self._splash_pic_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.realpath(__file__)))),
        self.DEFAULT_SPLASH_PIC)

    self._scanned_gif_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.realpath(__file__)))),
        self.DEFAULT_SCAN_GIF)

    self._scoreboard = Scroller()
    self._global_menu = Scroller()

  def _InitStateMachine(self):
    """Initializes the internal state machine."""
    self.machine = Machine(
        states=list(self.STATES), initial='SPLASH', send_event=True)

    # Used to set our attributes from the Machine object
    self.machine.SetEnv = self._SetEnv
    self.machine.IncrementScoreIndex = self._IncrementScoreIndex
    self.machine.DecrementScoreIndex = self._DecrementScoreIndex
    # Transitions
    # (trigger, source, destination)
    self.machine.add_transition('back', '*', 'SCORE', before='SetEnv')
    self.machine.add_transition('scan', '*', 'SCANNED', before='SetEnv')
    self.machine.add_transition('error', '*', 'ERROR', before='SetEnv')
    # TODO: check device "mode" ?
    self.machine.add_transition(
        'up', 'SCORE', 'SCORE', after='DecrementScoreIndex')
    self.machine.add_transition(
        'down', 'SCORE', 'SCORE', after='IncrementScoreIndex')
    self.machine.add_transition('up', 'SPLASH', 'SCORE')
    self.machine.add_transition('down', 'SPLASH', 'SCORE')

    self.machine.add_transition('menu1', '*', 'MENUGLOBAL')
    self.machine.add_transition(
        'up', 'MENUGLOBAL', 'MENUGLOBAL', after='DecrementScoreIndex')
    self.machine.add_transition(
        'down', 'MENUGLOBAL', 'MENUGLOBAL', after='IncrementScoreIndex')
    self.machine.add_transition('up', 'SPLASH', 'SCORE')
    self.machine.add_transition('down', 'SPLASH', 'SCORE')


    self.machine.add_transition('up', 'ERROR', 'SCORE')
    self.machine.add_transition('down', 'ERROR', 'SCORE')
    self.machine.add_transition('left', 'ERROR', 'SCORE')
    self.machine.add_transition('right', 'ERROR', 'SCORE')

    self.machine.add_transition('menu1', 'MENUGLOBAL', 'SCORE')
    self.machine.add_transition('menu2', '*', 'SCORE')

    self.machine.add_transition('up', '*', '=')
    self.machine.add_transition('down', '*', '=')

  def _IncrementScoreIndex(self, _unused_event):
    """Helper method to increment current score board index.

    Args:
      _unused_event(transitions.EventData): the event.
    """
    self._scoreboard.IncrementIndex()

  def _DecrementScoreIndex(self, _unused_event):
    """Helper method to decrement current score board index.

    Args:
      _unused_event(transitions.EventData): the event.
    """
    self._scoreboard.DecrementIndex()

  def _SetEnv(self, event):
    """Helper method to change some of our attributes on transiton changes.

    Args:
      event(transitions.EventData): the event.
    """
    self._last_scanned_name = event.kwargs.get('who', None)
    self._too_soon = event.kwargs.get('too_soon', False)
    self._last_error = event.kwargs.get('error', None)

  def Update(self):
    """Draws the display depending on the state of the StateMachine."""
    self._scoreboard.UpdateData(self._database.GetScoreBoard())
    self._global_menu.UpdateData(self._GetGlobalMenuRows())
    if self.machine.state == 'SPLASH':
      self.ShowSplash()
    elif self.machine.state == 'ERROR':
      self.ShowError()
    elif self.machine.state == 'SCORE':
      self.ShowScores()
    elif self.machine.state == 'SCANNED':
      if self._too_soon:
        self.ShowScannedTooSoon()
      else:
        self.ShowScanned()
    elif self.machine.state == 'MENUGLOBAL':
      self.ShowMenuGlobal()


  def _GetGlobalMenuRows(self):
    """Builds the information to display in the global menu.

    Returns:
      list(dict): the data to display
    """
    data = []

    total_l = GetShortAmountOfBeer(self._database.GetTotalAmount() / 100.0)
    last_h = datetime.datetime.now() - datetime.timedelta(hours=1)
    l_per_h = GetShortAmountOfBeer(
        self._database.GetTotalAmount(since=last_h) / 100.0)


    now = datetime.datetime.now()
    today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    first_scan_today = self._database.GetEarliestEntry(after=today)

    data.append(DataPoint('WiFi', system.GetWifiStatus()))
    data.append(DataPoint('Total', total_l, 'L'))
    data.append(DataPoint('Last h', l_per_h, 'L/h'))
    data.append(DataPoint('Number of scans', self._database.GetEntriesCount()))
    if first_scan_today:
      data.append(DataPoint('1st today', first_scan_today.character_name))
    return data

  def _DrawTextRow(self, drawer, text, line_num, char_height, selected=False):
    """Helper method to draw a row of text.

    Args:
      drawer(LumaCanvas): the canvas to draw into.
      text(str): the text to display.
      line_num(int): which line number to draw.
      char_height(int): height of a character in pixels.
      selected(bool): whether to draw the line as selected.
    """
    if selected:
      rectangle_geometry = (
          2,
          line_num * char_height,
          self.luma_device.width,
          ((line_num+1) * char_height)
          )
      drawer.rectangle(
          rectangle_geometry, outline='white', fill='white')
      drawer.text(
          (2, line_num*char_height), text, font=self._font, fill='black')
    else:
      drawer.text(
          (2, line_num*char_height), text, font=self._font, fill='white')

  def ShowMenuGlobal(self):
    """Displays the global menu"""
    with LumaCanvas(self.luma_device) as drawer:
      char_w, char_h = drawer.textsize(' ', font=self._font)
      max_text_width = int(self.luma_device.width / char_w)
      self._global_menu.SetMaxLines(int(self.luma_device.height / char_h))
      menu_enumerated = enumerate(self._global_menu.GetRows())
      draw_row = 0
      for menu_position, data_point in menu_enumerated:
        key = data_point.key
        value = str(data_point.value)
        val_len = str(max_text_width - len(key) - 2)
        text_format = '{0:s}: {1:>'+val_len+'s}'
        text = text_format.format(key, value+data_point.unit)

        self._DrawTextRow(
            drawer, text, draw_row, char_h,
            selected=(self._global_menu.index == menu_position))
        draw_row += 1

  def ShowScannedTooSoon(self):
    """Draws the screen showing we're scanning too fast."""
    msg = 'Already scanned\n cheater :3'
    # Add a text layer over the frame
    background = PIL.Image.new('RGB', self.luma_device.size, 'black')
    text_layer = PIL.ImageDraw.Draw(background)
    text_width, text_height = text_layer.textsize(msg)
    text_pos = (
        (self.luma_device.width - text_width) // 2,
        (self.luma_device.height - text_height) // 2
    )
    text_layer.text(text_pos, msg, (255, 255, 255), font=self._font)

    self.luma_device.display(background.convert(self.luma_device.mode))

  def ShowScanned(self):
    """Draws the screen showing the last scanned tag."""
    regulator = framerate_regulator(fps=30)
    beer = PIL.Image.open(self._scanned_gif_path)
    size = [min(*self.luma_device.size)] * 2
    posn = (
        (self.luma_device.width - size[0]) // 2,
        self.luma_device.height - size[1]
    )
    msg = 'Cheers ' + self._last_scanned_name + '!'
    msg += ' {0:s}L'.format(
        GetShortAmountOfBeer(
            self._database.GetAmountFromName(self._last_scanned_name) / 100.0))

    for gif_frame in PIL.ImageSequence.Iterator(beer):
      with regulator:
        background = PIL.Image.new('RGB', self.luma_device.size, 'black')
        # Add a frame from the animation
        background.paste(
            gif_frame.resize(size, resample=PIL.Image.LANCZOS), posn)

        # Add a text layer over the frame
        text_layer = PIL.ImageDraw.Draw(background)
        text_width, text_height = text_layer.textsize(msg)
        text_pos = (
            (self.luma_device.width - text_width) // 2,
            self.luma_device.height - text_height
        )
        text_layer.text(text_pos, msg, (255, 255, 255), font=self._font)

        self.luma_device.display(background.convert(self.luma_device.mode))


  def ShowScores(self):
    """Draws the Scoreboard screen."""
    with LumaCanvas(self.luma_device) as drawer:
      char_w, char_h = drawer.textsize(' ', font=self._font)
      max_text_width = int(self.luma_device.width / char_w)
      max_name_width = max_text_width-13
      self._scoreboard.SetMaxLines(int(self.luma_device.height / char_h))
      # ie: '  Name      L Last'
      header = '  '+('{:<'+str(max_name_width)+'}').format('Name')+'    L Last'
      drawer.text((2, 0), header, font=self._font, fill='white')
      score_enumerated = enumerate(self._scoreboard.GetRows())
      draw_row = 0
      for scoreboard_position, row in score_enumerated:
        draw_row += 1
        # ie: '1.Fox        12  12h'
        #     '2.Dog        10   5m'
        text = '{0:d}.'.format(scoreboard_position+1)
        text += ' '.join([
            ('{0:<'+str(max_name_width)+'}').format(row.character_name),
            GetShortAmountOfBeer(row.total / 100.0),
            GetShortLastBeer(row.last)])
        self._DrawTextRow(
            drawer, text, draw_row, char_h,
            selected=(self._scoreboard.index == scoreboard_position))

  def ShowSplash(self):
    """Displays the splash screen."""
    background = PIL.Image.new(self.luma_device.mode, self.luma_device.size)
    splash = PIL.Image.open(self._splash_pic_path).convert(
        self.luma_device.mode)
    posn = ((self.luma_device.width - splash.width) // 2, 0)
    background.paste(splash, posn)
    self.luma_device.display(background)
    time.sleep(1)
    self.machine.back()
    self.Update()

  def ShowError(self):
    """Displays an error message."""
    term = terminal(self.luma_device, self._font, animate=False)
    print(self._last_error)
    term.println(self._last_error)

  def Setup(self):
    """Initializes the GUI."""
    is_rpi = False
    try:
      with open('/sys/firmware/devicetree/base/model', 'r') as model:
        is_rpi = model.read().startswith('Raspberry Pi')
    except IOError:
      pass

    if is_rpi:
      from beerlog.gui import sh1106
      gui_object = sh1106.WaveShareOLEDHat(self._events_queue)
    else:
      from beerlog.gui import emulator
      gui_object = emulator.Emulator(self._events_queue)

    if not gui_object:
      raise Exception('Could not initialize a GUI object')

    gui_object.Setup()
    self.luma_device = gui_object.GetDevice()

    self._InitStateMachine()

# vim: tabstop=2 shiftwidth=2 expandtab
