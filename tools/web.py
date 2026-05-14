"""Serves the beerlog data in a website"""

import argparse
import datetime
import os
import sys
import http.server
import json
import socketserver

from beerlog import beerlogdb

socketserver.TCPServer.allow_reuse_address = True

DEFAULT_DB = os.path.join('beerlog.sqlite')
DEFAULT_TAGS_FILE = os.path.join('known_tags.json')
DEFAULT_PORT = 8000

MAX_HOURS = 30 * 24  # 1 month

class Handler(http.server.BaseHTTPRequestHandler):
  """Implements a simple HTTP server."""

  DB = None
  TEMPLATE_HTML = """
<html>
<head>
  <title>Beer</title>
  <link rel="icon" href="data:;base64,=">
  <script src="beer.js"></script>
  <script src="chart.js"></script>
</head>
<body>
  <div id="total">
  </div>
  <div style="width:80%; height:50%">
    <canvas id="myChart"></canvas>
  </div>
  <script>update_graph("/data", drawChart);</script>
</body></html> """

  def __init__(self, *args, **kwargs):
    self._db: beerlogdb.BeerLogDB
    self._characters: list[str]
    self._Setup()
    super().__init__(*args, **kwargs)
    self.options: argparse.Namespace

  def _Setup(self):
    """Initiates some useful objects"""
    assert self.options is not None, 'options should be set before calling _Setup'
    self._db = beerlogdb.BeerLogDB(self.options.database)
    self._db.LoadTagsDB(self.options.known_tags)
    self._characters = self._db.GetAllCharacterNames()

  def do_GET(self): #pylint: disable=invalid-name
    """Handles all GET requests."""
    if self.path == '/':
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(self.TEMPLATE_HTML.format().encode())
    elif self.path == '/chart.js':
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      with open(os.path.join('assets', 'web', 'chart.js'), 'rb') as js:
        self.wfile.write(js.read())
    elif self.path == '/beer.js':
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      with open(os.path.join('assets', 'web', 'beer.js'), 'rb') as js:
        self.wfile.write(js.read())
    elif self.path == '/data':
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(self.GetData())
    else:
      self.send_error(404, 'error')

  def GetData(self):
    """Builds a dict to use with Chart.js."""
    first_scan = self._db.GetEarliestTimestamp()
    last_scan = self._db.GetLatestTimestamp()
    delta = last_scan - first_scan
    total_hours = int((delta.total_seconds() / 3600) + 2)
    if total_hours > MAX_HOURS:
      msg = (
              'We calculated there are {0:d} hours between {1!s} and {2!s}, '
              'which is more than the expected max number of hours in a month'
              ': {3:d}'
              ).format(total_hours, first_scan, last_scan, MAX_HOURS)
      raise Exception(msg)
    fields = [] # This is the X axis
    datasets = {} # {'alcoolique': ['L cummulés']}
    for hour in range(total_hours):
      timestamp = (first_scan + datetime.timedelta(seconds=hour * 3600))
      timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
      fields.append(timestamp.astimezone().strftime('%Y%m%d %Hh%M'))
      for alcoolique in self._characters:
        cl = self._db.GetAmountFromName(alcoolique, at=timestamp)
        if alcoolique in datasets:
          datasets[alcoolique].append(cl)
        else:
          datasets[alcoolique] = [cl]

    total = 0
    # 'totals' is unused for now, can be used later to display the scores
    totals = {} # {'alcoolique': total }
    for alcoolique in self._db.GetAllCharacterNames():
      cl = self._db.GetAmountFromName(alcoolique, at=last_scan)
      total += cl
      totals[alcoolique] = cl

    totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)

    total_by_hour = [
        sum(datasets[name][hour] for name in self._characters)
        for hour in range(total_hours)
    ]
    if len(total_by_hour) == 1:
      window = 1
      peak_3hr = total_by_hour[0]
      peak_start = 0
    else:
      window = min(2, len(total_by_hour) - 1)
      peak_3hr = 0
      peak_start = 0
      for hour in range(len(total_by_hour) - window - 1):
        consumed = total_by_hour[hour + window] - total_by_hour[hour]
        if consumed > peak_3hr:
          peak_3hr = consumed
          peak_start = hour
    peak_3hr_per_hour = peak_3hr / 100.0 / float(window)
    peak_start = max(0, min(peak_start, len(fields) - 1)) if fields else 0
    peak_label = fields[peak_start] if fields else ''

    peak_by_character = []
    for alcoolique in self._characters:
      char_values = datasets[alcoolique]
      if len(char_values) == 1:
        char_window = 1
        char_peak = char_values[0]
        char_start = 0
      else:
        char_window = window
        char_peak = 0
        char_start = 0
        for hour in range(len(char_values) - char_window - 1):
          consumed = char_values[hour + char_window] - char_values[hour]
          if consumed > char_peak:
            char_peak = consumed
            char_start = hour
      peak_by_character.append({
          'name': alcoolique,
          'avg': char_peak / 100.0 / float(char_window),
          'start_index': char_start,
          'label': fields[char_start] if fields else '',
          'window_length': char_window})
    peak_by_character.sort(key=lambda item: item['avg'], reverse=True)

    # Formating for Charts.js
    speed_by_hour = [0]
    for hour in range(1, len(total_by_hour)):
      speed_by_hour.append(total_by_hour[hour] - total_by_hour[hour - 1])

    output_datasets = [] # [{'label': 'alcoolique', 'data': ['L cummulés']}]
    for k, v in sorted(datasets.items(), key=lambda x: x[1][-1], reverse=True):
      output_datasets.append({
          'label': k,
          'data':v
          })
    output_datasets.append({
        'label': 'Total cumulative',
        'data': total_by_hour,
        'order': 0
    })
    output_datasets.append({
        'label': 'Total speed',
        'data': speed_by_hour,
        'order': 1
    })
    return json.dumps(
        {'data':{
            'labels':fields,
            'datasets':output_datasets,
            'drinkers': self._db.GetAllCharacterNames(),
            'total': total/100.0,
            'peak_3hr_avg': peak_3hr_per_hour,
            'peak_3hr_window_length': window,
            'peak_3hr_start_index': peak_start,
            'peak_3hr_label': peak_label,
            'peak_by_character': peak_by_character}}
        ).encode()

def ParseArguments() -> argparse.Namespace:
  """Parses arguments.

  Returns:
    argparse.NameSpace: the parsed arguments.
  """

  parser = argparse.ArgumentParser(description='BeerLog')
  parser.add_argument(
      '--database', dest='database', action='store',
      default=DEFAULT_DB,
      help='the path to the sqlite file')
  parser.add_argument(
      '--known_tags', dest='known_tags', action='store',
      default=DEFAULT_TAGS_FILE,
      help='the known tags file to use to use')
  parser.add_argument(
      '--port', dest='port', action='store',
      default=DEFAULT_PORT, type=int,
      help='port to listen at')

  parsed_args = parser.parse_args()

  if not os.path.isfile(parsed_args.database):
    print('Could not find a sqlite file at {0!s}'.format(parsed_args.database))
    sys.exit(1)
  if not os.path.isfile(parsed_args.known_tags):
    print('Could not find a known tags JSON file at {0!s}'.format(
        parsed_args.known_tags))
    sys.exit(1)

  return parser.parse_args()


# This is necessary to be able to pass parameters to the Handler class
# used in socketserver.TCPServer
def MakeHandlerClassFromArgv(init_args: argparse.Namespace):
  """Generates a class that inherits from Handler, with the proper attributes"""
  class CustomHandler(Handler):
    """Wrapper around Handler that sets the required attributes"""
    def __init__(self, *args, **kwargs):
      self.options = init_args
      super().__init__(*args, **kwargs)

  return CustomHandler


app_args = ParseArguments()

HandlerClass =  MakeHandlerClassFromArgv(app_args)

print('Server listening on port {0:d}...'.format(app_args.port))
httpd = socketserver.TCPServer(('', app_args.port), HandlerClass)
try:
  httpd.serve_forever()
except KeyboardInterrupt:
  pass
print('Shutting Down')
httpd.server_close()
