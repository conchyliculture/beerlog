"""Module for managing the display."""

from __future__ import print_function

from collections import namedtuple
import datetime
import io
import os
import time
import transitions

from luma.core.render import canvas as LumaCanvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import terminal
import matplotlib.pyplot as plt
import PIL

from beerlog.gui import achievements
from beerlog import errors
from beerlog import system
from beerlog import utils


DataPoint = namedtuple(
    'DataPoint', ['key', 'value', 'unit'], defaults=['', '', ''])

DEFAULT_SCAN_GIF = 'assets/gif/beer_scanned.gif'


class Scroller():
  """Implements a scroller object."""

  def __init__(self):
    self.data = []
    self.old_data = []
    self._max_lines = 0

    self.index = 0
    self.window_low = 0
    self._array_size = 0
    self.window_high = 0

  def UpdateData(self, data):
    """Sets the data for the scoller object.

    Args:
      data(list): the list of rows to display/scroll through.
    """
    self.old_data = self.data
    self.data = data
    self._array_size = len(self.data)

  def SetMaxLines(self, lines):
    """Sets the width of the window.

    Args:
      lines(int): the number of lines of the window.
    """
    self._max_lines = lines
    self.window_high = self.window_low + lines

  def GetRows(self):
    """Returns the number of rows to display in the window.

    Returns:
      enumerate(peewee rows): the scoreboard window.
    """
    window = self.data[self.window_low:self.window_high]
    return window

  def IncrementIndex(self, unused_event):
    """Increments the index. Moves the window bounds if necessary.

    This is called by the transitioning state machine, this is why we
    get an extra 'event' parameter.
    """
    if self.index is None:
      self.index = 0
    elif self.index < self._array_size - 1:
      self.index += 1
      if self.index == self.window_high:
        self.window_low += 1
        self.window_high += 1

  def DecrementIndex(self, unused_event):
    """Decrements the index. Moves the window bounds if necessary.

    This is called by the transitioning state machine, this is why we
    get an extra 'event' parameter.
    """
    if self.index is None:
      self.index = 0
    elif self.index > 0:
      if self.index == self.window_low:
        self.window_low -= 1
        self.window_high -= 1
      self.index -= 1


class LumaDisplay():
  """Class managing the display."""

  STATES = [
      'SPLASH', 'SCORE', 'STATS', 'SCANNED', 'ERROR', 'MENUGLOBAL', 'GRAPH']

  DEFAULT_SPLASH_PIC = 'assets/pics/splash_small.png'

  def __init__(self, events_queue, database):
    """Initializes a Display backed by luma.

    Attributes:
      _events_queue(Queue): the shared queue for events.
      _database(beerlog.BeerlogDB): the application database.
      gui_object(beerlog.gui.base.BaseGUI):
        the GUI object (ie: Oled hat, Emulator, etc).
      luma_device(luma.core.device.device): The luma_device inside the
        gui_object. Used for actual drawing things.
      machine(transitions.Machine): the state machine.
      _last_scanned_name(str): Name of the character who just scanned.

    """
    self._events_queue = events_queue
    self._database = database
    if not self._events_queue:
      raise errors.BeerLogError('Display needs an events_queue')
    if not self._database:
      raise errors.BeerLogError('Display needs a DB object')

    # This is the object for different implementations
    self.gui_object = None
    # This is a pointer to the luma_device, which draws stuff
    self.luma_device = None
    self.machine = None
    self._last_scanned_name = None
    self._last_error = None
    self._too_soon = False
    self._current_character_name = None

    # UI related defaults
    self._font = PIL.ImageFont.load_default()
    self._splash_pic_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.realpath(__file__)))),
        self.DEFAULT_SPLASH_PIC)

    self._scoreboard = Scroller()
    self._global_menu = Scroller()

  def _InitStateMachine(self):
    """Initializes the internal state machine."""
    self.machine = transitions.Machine(
        states=list(self.STATES), initial='SPLASH', send_event=True)

    # Used to set our attributes from the Machine object
    self.machine.SetEnv = self._SetEnv
    self.machine.IncrementScoreIndex = self._scoreboard.IncrementIndex
    self.machine.DecrementScoreIndex = self._scoreboard.DecrementIndex
    self.machine.IncrementGlobalMenuIndex = self._global_menu.IncrementIndex
    self.machine.DecrementGlobalMenuIndex = self._global_menu.DecrementIndex
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
        'up', 'MENUGLOBAL', 'MENUGLOBAL', after='DecrementGlobalMenuIndex')
    self.machine.add_transition(
        'down', 'MENUGLOBAL', 'MENUGLOBAL', after='IncrementGlobalMenuIndex')
    self.machine.add_transition('up', 'SPLASH', 'SCORE')
    self.machine.add_transition('down', 'SPLASH', 'SCORE')


    # Graphs
    self.machine.add_transition('right', 'SCORE', 'GRAPH')
    self.machine.add_transition('right', 'GRAPH', 'GRAPH')
    self.machine.add_transition('left', 'GRAPH', 'SCORE')

    self.machine.add_transition('up', 'ERROR', 'SCORE')
    self.machine.add_transition('down', 'ERROR', 'SCORE')
    self.machine.add_transition('left', 'ERROR', 'SCORE')
    self.machine.add_transition('right', 'ERROR', 'SCORE')

    self.machine.add_transition('menu1', 'MENUGLOBAL', 'SCORE')
    self.machine.add_transition('menu2', '*', 'SCORE')

    self.machine.add_transition('up', '*', '=')
    self.machine.add_transition('down', '*', '=')

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
    elif self.machine.state == 'GRAPH':
      self.ShowGraph()

  def _GetGlobalMenuRows(self):
    """Builds the information to display in the global menu.

    Returns:
      list(DataPoint): the data to display
    """
    data = []

    total_l = utils.GetShortAmountOfBeer(
        self._database.GetTotalAmount() / 100.0)
    last_h = datetime.datetime.now() - datetime.timedelta(hours=1)
    l_per_h = utils.GetShortAmountOfBeer(
        self._database.GetTotalAmount(since=last_h) / 100.0)

    now = datetime.datetime.now()
    today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    first_scan_today = self._database.GetEarliestEntry(after=today)

    data.append(DataPoint('Time', system.GetTime()))
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

  def GetAchievements(self, name):
    """Checks whether a character deserves achievements.

    Args:
        name(str): the character_name.
    Returns:
        list(BaseAchievement): a list of BaseAchievement.
    """
    all_achievements = []

    total_drunk = self._database.GetAmountFromName(name)
    glass = self._database.GetGlassFromName(name)

    prev_total_drunk = total_drunk - glass

    # Achievement for beating someone
    i = 0
    current_spot = 0
    prev_spot = 0
    for e in self._scoreboard.data:
      i += 1
      if e.character_name == name:
        current_spot = i
        break

    i = 0
    for e in self._scoreboard.old_data:
      i += 1
      if e.character_name == name:
        prev_spot = i

    if prev_spot > current_spot:
      all_achievements.append(achievements.BeatSomeoneAchievement(current_spot))

    # Achievement for a big amount of L drunk
    if prev_total_drunk == 0:
      all_achievements.append(achievements.FirstBeerAchievement(name))

    for cool_amount in [1, 5, 10, 15, 20, 25, 30]:
      if total_drunk >= cool_amount*100 > prev_total_drunk:
        all_achievements.append(
            achievements.SelfVolumeAchievement(cool_amount, name))

    return all_achievements

  def _ShowAchievement(self, achievement):
    """Displays an achievement"""
    img_path = os.path.abspath(achievements.DEFAULT_ACHIEVEMENT_FRAME)
    background = PIL.Image.new('RGB', self.luma_device.size, 'black')
    logo = PIL.Image.open(img_path).convert('RGB')
    background.paste(logo)

    text_layer = PIL.ImageDraw.Draw(background)
    _font = PIL.ImageFont.load_default()

    _, text_height = text_layer.textsize(achievement.message)
    split_message = achievement.Splitted()
    text_layer.text(
        (44, 4), split_message[0],
        (255, 255, 255), font=_font)
    text_layer.text(
        (44, 4 + text_height), split_message[1],
        (255, 255, 255), font=_font)
    text_layer.text(
        (44, 4 + text_height*2), split_message[2],
        (255, 255, 255), font=_font)

    _font = PIL.ImageFont.truetype('assets/fonts/pixelmix.ttf', 16)
    text_layer.text(
        (5, 8 + text_height*3), achievement.big_message,
        (255, 255, 255), font=_font)

    _font = PIL.ImageFont.truetype('assets/fonts/NotoEmoji-Regular.ttf', 28)
    text_layer.text((4, 4), achievement.emoji, (255, 255, 255), font=_font)

    regulator = framerate_regulator(fps=5)
    for _ in range(15): # 15 frames at 5fps
      with regulator:
        self.luma_device.display(background.convert(self.luma_device.mode))

  def _ShowDefaultScan(self, name):
    """Show the default scan animation"""
    size = [min(*self.luma_device.size)] * 2
    posn = (
        (self.luma_device.width - size[0]) // 2,
        self.luma_device.height - size[1]
    )
    regulator = framerate_regulator(fps=30)
    image = PIL.Image.open(DEFAULT_SCAN_GIF)

    total_drunk = self._database.GetAmountFromName(name)

    default_msg = 'Cheers ' + name + '!'
    default_msg += ' {0:s}L'.format(
        utils.GetShortAmountOfBeer(total_drunk / 100.0))

    for gif_frame in PIL.ImageSequence.Iterator(image):
      with regulator:
        background = PIL.Image.new('RGB', self.luma_device.size, 'black')
        # Add a frame from the animation
        background.paste(
            gif_frame.resize(size, resample=PIL.Image.LANCZOS), posn)

        # Add a text layer over the frame
        text_layer = PIL.ImageDraw.Draw(background)
        text_width, text_height = text_layer.textsize(default_msg)
        text_pos = (
            (self.luma_device.width - text_width) // 2,
            self.luma_device.height - text_height
        )
        text_layer.text(text_pos, default_msg, (255, 255, 255), font=self._font)

        self.luma_device.display(background.convert(self.luma_device.mode))

  def ShowScanned(self):
    """Draws the screen showing the last scanned tag.

    Will display achievements if relevant."""

    rewards = self.GetAchievements(self._last_scanned_name)
    if not rewards:
      self._ShowDefaultScan(self._last_scanned_name)

    for r in rewards:
      self._ShowAchievement(r)

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
        selected = (self._scoreboard.index ==
                    scoreboard_position + self._scoreboard.window_low)
        if selected:
          self._current_character_name = row.character_name
        draw_row += 1
        # ie: '1.Fox        12  12h'
        #     '2.Dog        10   5m'
        text = '{0:d}.'.format(
            scoreboard_position + 1 + self._scoreboard.window_low)
        text += ' '.join([
            ('{0:<'+str(max_name_width)+'}').format(row.character_name),
            utils.GetShortAmountOfBeer(row.total / 100.0),
            utils.GetShortLastBeer(row.last)])
        self._DrawTextRow(drawer, text, draw_row, char_h, selected=selected)

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

  def ShowGraph(self):
    """Displays a person graph"""
    fig, ax = plt.subplots(figsize=(2, 1), dpi=64, facecolor='black')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.figtext(
        0.5, 0.2, self._current_character_name, color='w', fontsize='large')

    point_data = self._database.GetDataFromName(self._current_character_name)

    ax.plot([e.timestamp for e in point_data], [e.sum for e in point_data], 'w')
    ax.set_frame_on(False)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=fig.dpi, facecolor='black')
    background = PIL.Image.open(buf)
    self.luma_device.display(background.convert(self.luma_device.mode))

    plt.close()

  def Setup(self):
    """Initializes the GUI."""
    is_rpi = False
    try:
      with open('/sys/firmware/devicetree/base/model', 'r') as model:
        is_rpi = model.read().startswith('Raspberry Pi')
    except IOError:
      pass

    if is_rpi:
      from beerlog.gui import sh1106  # pylint: disable=import-outside-toplevel
      self.gui_object = sh1106.WaveShareOLEDHat(self._events_queue)
    else:
      from beerlog.gui import emulator  # pylint: disable=import-outside-toplevel
      self.gui_object = emulator.Emulator(self._events_queue)

    if not self.gui_object:
      raise Exception('Could not initialize a GUI object')

    self.gui_object.Setup()
    self.luma_device = self.gui_object.GetDevice()

    self._InitStateMachine()

  def Terminate(self):
    """Kills the display."""
    self.gui_object.Terminate()

# vim: tabstop=2 shiftwidth=2 expandtab
