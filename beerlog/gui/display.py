"""TODO"""
from __future__ import print_function

from datetime import datetime
import os
import time
from transitions import Machine

from luma.core.render import canvas as LumaCanvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import terminal
import PIL

from beerlog import errors


def GetShortAmountOfBeer(amount):
  """Returns a shortened string for an volume in cL."""
  if amount >= 999.5:
    return 'DED'
  if amount >= 99.5:
    return '{0:>3d}'.format(int(round(amount)))
  return '{0:3.2g}'.format(amount)


def GetShortLastBeer(last, now=None):
  """Returns a shortened string for the last scan."""
  if not now:
    now = datetime.now()
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

class ScoreBoard():
  """Implements a sliding window with a selector over the score board."""

  def __init__(self, scoreboard):
    self._board = scoreboard
    self._max_lines = 0

    self.index = None
    self._window_low = 0
    self._window_high = len(self._board)

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
    window = self._board[self._window_low:self._window_high]
    return enumerate(window, start=self._window_low+1)

  def IncrementIndex(self):
    """Increments the index. Moves the window bounds if necessary."""
    if self.index is None:
      self.index = 0
    if self.index < len(self._board):
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
  """TODO"""

  STATES = ['SPLASH', 'SCORE', 'STATS', 'SCANNED', 'ERROR']

  DEFAULT_SPLASH_PIC = 'assets/pics/splash_small.png'
  DEFAULT_SCAN_GIF = 'assets/gif/beer_scanned.gif'

  # TODO: remove the default None here
  def __init__(self, events_queue=None, database=None):
    self._events_queue = events_queue
    self._database = database
    if not self._events_queue:
      raise errors.BeerLogError('Display needs an events_queue')
    if not self._database:
      raise errors.BeerLogError('Display needs a DB object')

    # Internal stuff
    self.luma_device = None
    self.machine = None
    self._last_scanned = None
    self._last_scanned_character = None
    self._last_error = None

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

    self._scoreboard = ScoreBoard(self._database.GetScoreBoard())

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
    self.machine.add_transition('stats', 'SCORE', 'STATS')
    self.machine.add_transition('scan', '*', 'SCANNED', before='SetEnv')
    self.machine.add_transition('error', '*', 'ERROR', before='SetEnv')
    # TODO: check devie "mode" ?
    self.machine.add_transition(
        'up', 'SCORE', 'SCORE', after='DecrementScoreIndex')
    self.machine.add_transition(
        'down', 'SCORE', 'SCORE', after='IncrementScoreIndex')
    self.machine.add_transition('up', 'SPLASH', 'SCORE')
    self.machine.add_transition('down', 'SPLASH', 'SCORE')

    self.machine.add_transition('up', 'ERROR', 'SCORE')
    self.machine.add_transition('down', 'ERROR', 'SCORE')
    self.machine.add_transition('left', 'ERROR', 'SCORE')
    self.machine.add_transition('right', 'ERROR', 'SCORE')

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
    self._last_scanned = event.kwargs.get('who', None)
    self._last_scanned_character = event.kwargs.get('character', None)
    self._last_error = event.kwargs.get('error', None)
    self._scoreboard = ScoreBoard(self._database.GetScoreBoard())

  def Update(self):
    """TODO"""
    if self.machine.state == 'SPLASH':
      self.ShowSplash()
    elif self.machine.state == 'ERROR':
      self.ShowError()
    elif self.machine.state == 'SCORE':
      self.ShowScores()
    elif self.machine.state == 'SCANNED':
      self.ShowScanned()

  def ShowScanned(self):
    """Draws the screen showing the last scanned tag."""
    regulator = framerate_regulator(fps=30)
    beer = PIL.Image.open(self._scanned_gif_path)
    size = [min(*self.luma_device.size)] * 2
    posn = (
        (self.luma_device.width - size[0]) // 2,
        self.luma_device.height - size[1]
    )
    msg = 'Cheers ' + self._last_scanned + '!'
    if self._last_scanned_character:
      msg += ' {0:s}L'.format(
          GetShortAmountOfBeer(
              self._last_scanned_character.GetAmountDrunk() / 100.0))

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
      max_name_width = max_text_width-12
      self._scoreboard.SetMaxLines(int(self.luma_device.height / char_h))
      # ie: '  Name      L Last'
      header = '  '+('{:<'+str(max_name_width)+'}').format('Name')+'   L Last'
      drawer.text((2, 0), header, font=self._font, fill='white')
      score_enumerated = self._scoreboard.GetRows()
      draw_row = 0
      for scoreboard_position, row in score_enumerated:
        draw_row += 1
        # ie: '1.Fox        12  12h'
        #     '2.Dog        10   5m'
        text = str(scoreboard_position)+'.'
        text += ' '.join([
            ('{0:<'+str(max_name_width)+'}').format(row.character.name),
            GetShortAmountOfBeer(row.amount / 100.0),
            GetShortLastBeer(row.last)])
        if self._scoreboard.index == scoreboard_position:
          rectangle_geometry = (
              2,
              draw_row * char_h,
              self.luma_device.width,
              ((draw_row+1) * char_h)
              )
          drawer.rectangle(
              rectangle_geometry, outline='white', fill='white')
          drawer.text((2, draw_row*char_h), text, font=self._font, fill='black')
        else:
          drawer.text((2, draw_row*char_h), text, font=self._font, fill='white')

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
    term = terminal(self.luma_device, self._font)
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
