"""TODO"""
from __future__ import print_function

import os
from transitions import Machine

from luma.core.render import canvas as LumaCanvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import terminal
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageSequence

from errors import BeerLogError


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
      raise BeerLogError('Display needs an events_queue')
    if not self._database:
      raise BeerLogError('Display needs a DB object')

    self.luma_device = None
    self._font = ImageFont.load_default()

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

    self._last_scanned = None
    self._last_error = None

    self._selected_menu_index = None

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
    self.machine.add_transition(
        'up', 'SCORE', 'SCORE', after='IncrementScoreIndex')
    self.machine.add_transition(
        'down', 'SCORE', 'SCORE', after='DecrementScoreIndex')
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
    if self._selected_menu_index is None:
      self._selected_menu_index = 1
    else:
      self._selected_menu_index += 1

  def _DecrementScoreIndex(self, _unused_event):
    """Helper method to decrement current score board index.

    Args:
      _unused_event(transitions.EventData): the event.
    """
    if self._selected_menu_index is None:
      self._selected_menu_index = 1
    else:
      self._selected_menu_index += 1

  def _SetEnv(self, event):
    """Helper method to change some of our attributes on transiton changes.

    Args:
      event(transitions.EventData): the event.
    """
    self._last_scanned = event.kwargs.get('who', None)
    self._last_error = event.kwargs.get('error', None)
    self._selected_menu_index = None

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
    beer = Image.open(self._scanned_gif_path)
    size = [min(*self.luma_device.size)] * 2
    posn = (
        (self.luma_device.width - size[0]) // 2,
        self.luma_device.height - size[1]
    )
    msg = 'Cheers ' + self._last_scanned + '!'

    for gif_frame in ImageSequence.Iterator(beer):
      with regulator:
        background = Image.new('RGB', self.luma_device.size, 'black')
        # Add a frame from the animation
        background.paste(gif_frame.resize(size, resample=Image.LANCZOS), posn)

        # Add a text layer over the frame
        text_layer = ImageDraw.Draw(background)
        text_width, text_height = text_layer.textsize(msg)
        text_pos = (
            (self.luma_device.width - text_width) // 2,
            self.luma_device.height - text_height
        )
        text_layer.text(text_pos, msg, (255, 255, 255), font=self._font)

        self.luma_device.display(background.convert(self.luma_device.mode))

  def _IsScoreSelected(self, i, l):
    """TODO"""
    if self._selected_menu_index is None:
      return False
    if (self._selected_menu_index + 1) % l == i - 1:
      return True
    return False

  def ShowScores(self):
    """Draws the Scoreboard screen."""
    scoreboard = self._database.GetScoreBoard()
    with LumaCanvas(self.luma_device) as drawer:
      char_w, char_h = drawer.textsize(' ', font=self._font)
      max_text_width = int(self.luma_device.width / char_w)
      max_name_width = max_text_width-12
      # ie: '  Name      Cnt Last'
      header = '  '+('{:<'+str(max_name_width)+'}').format('Name')+' Cnt Last'
      drawer.text((2, 0), header, font=self._font, fill='white')
      for i, row in enumerate(scoreboard, start=1):
        # ie: '1.Fox        12 12h'
        #     '2.Dog        10  5m'
        text = str(i)+'.'
        text += ('{0:<'+str(max_name_width)+'}').format(row.character)
        text += ' {0:>3d}'.format(row.count)
        text += ' 12h'
        if self._IsScoreSelected(i, len(scoreboard)):
          rectangle_geometry = (
              2,
              i * char_h,
              self.luma_device.width,
              ((i+1) * char_h)
              )
          drawer.rectangle(
              rectangle_geometry, outline='white', fill='white')
          drawer.text((2, i*char_h), text, font=self._font, fill='black')
        else:
          drawer.text((2, i*char_h), text, font=self._font, fill='white')

  def ShowSplash(self):
    """Displays the splash screen."""
    background = Image.new(self.luma_device.mode, self.luma_device.size)
    splash = Image.open(self._splash_pic_path).convert(self.luma_device.mode)
    posn = ((self.luma_device.width - splash.width) // 2, 0)
    background.paste(splash, posn)
    self.luma_device.display(background)

  def ShowError(self):
    """Displays an error message."""
    term = terminal(self.luma_device, self._font)
    print(self._last_error)
    term.println(self._last_error)

  def Setup(self):
    """TODO"""
    is_rpi = False
    try:
      with open('/sys/firmware/devicetree/base/model', 'r') as model:
        is_rpi = model.read().startswith('Raspberry Pi')
    except IOError:
      pass

    if is_rpi:
      from gui import sh1106
      gui_object = sh1106.WaveShareOLEDHat(self._events_queue)
    else:
      raise Exception('Is not a RPI, bailing out ')

    if not gui_object:
      raise Exception('Could not initialize a GUI object')

    gui_object.Setup()
    self.luma_device = gui_object.GetDevice()

  def DrawText(self, text, font=None, x=0, y=0, fill='white'):
    """TODO"""
    with LumaCanvas(self.luma_device) as drawer:
      drawer.text((x, y), text, font=(font or self._font), fill=fill)

#  def _DrawMenuItem(self, drawer, number):
#    selected = self._menu_index == number
#    rectangle_geometry = (
#        self.MENU_TEXT_X,
#        number * self.MENU_TEXT_HEIGHT,
#        self.luma_device.width,
#        ((number+1) * self.MENU_TEXT_HEIGHT)
#        )
#    text_geometry = (
#        self.MENU_TEXT_X,
#        number*self.MENU_TEXT_HEIGHT
#        )
#    if selected:
#      drawer.rectangle(
#          rectangle_geometry, outline='white', fill='white')
#      drawer.text(
#          text_geometry,
#          self.MENU_ITEMS[number],
#          font=self._font, fill='black'
#          )
#    else:
#      drawer.text(
#          text_geometry,
#          self.MENU_ITEMS[number],
#          font=self._font, fill='white')
#
#  def DrawMenu(self):
#    with LumaCanvas(self.luma_device) as drawer:
#      drawer.rectangle(
#          self.luma_device.bounding_box, outline="white", fill="black")
#      for i in range(len(self.MENU_ITEMS)):
#        self._DrawMenuItem(drawer, i)
#
#  def MenuDown(self):
#    self._menu_index = ((self._menu_index + 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()
#
#  def MenuUp(self):
#    self._menu_index = ((self._menu_index - 1)%len(self.MENU_ITEMS))
#    self.DrawMenu()

# vim: tabstop=2 shiftwidth=2 expandtab
