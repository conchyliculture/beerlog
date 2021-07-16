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


class Handler(http.server.BaseHTTPRequestHandler):
  """Implements a simple HTTP server."""

  DB = None
  TEMPLATE_HTML = """
<html>
<head>
  <title>Beer</title>
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
    self._datasets = None
    self._db = None
    self._characters = None
    self._Setup()
    super().__init__(*args, **kwargs)
    self.options = None

  def _Setup(self):
    """Initiates some useful objects"""
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
      if self.options.lame:
        self.wfile.write(self.GetDataLame())
      else:
        self.wfile.write(self.GetData())
    else:
      self.send_error(404, 'error')


  def GetData(self):
    """Builds a dict to use with Chart.js."""
    first_scan = self._db.GetEarliestTimestamp()
    last_scan = self._db.GetLatestTimestamp()
    delta = last_scan - first_scan
    total_hours = int((delta.total_seconds() / 3600) + 2)
    fields = []
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
    totals = {} # {'alcoolique': total }
    for alcoolique in self._db.GetAllCharacterNames():
      cl = self._db.GetAmountFromName(alcoolique, at=last_scan)
      total += cl
      totals[alcoolique] = cl

    totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)

    output_datasets = [] # [{'label': 'alcoolique', 'data': ['L cummulés']}]
    for k, v in sorted(datasets.items(), key=lambda x: x[1][-1], reverse=True):
      output_datasets.append({
          'label': k,
          'data':v
          })
    return json.dumps(
        {'data':{
            'labels':fields,
            'datasets':output_datasets,
            'drinkers': self._db.GetAllCharacterNames(),
            'total': total}}
        ).encode()

  def GetDataLame(self):
    """Builds a dict to use with Chart.js, but in a lame way.

    This means returning a graph where all scan is a node."""
    data = {}
    for character in self._characters:
      for row in self._db.GetDataFromName(character):
        data[row.timestamp.strftime('%Y-%m-%d %H:%M:%S')] = (character, row.sum)

    # {
    #    time1: (char_1, cummulated),
    #    time2: (char_2, cummulated),
    #    time3: (char_1, cummulated),
    #    ....
    # }

    # First, add a data point before the first scan
    labels = [(
        self._db.GetEarliestTimestamp()-datetime.timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S')]
    datasets = []
    for char in self._characters:
      datasets.append({
            'label': char,
            'data': [0],
            'steppedLine': True,
            'spanGaps': True}) # Draw 'null' values
    for time in sorted(data):
      labels.append(time)
      character, amount = data[time]

      for dataset in datasets:
        if dataset['label'] == character:
          dataset['data'].append(amount)
        else:
          dataset['data'].append(None)

    # We need one last datapoint to draw all the way to the end of times
    labels.append((
        self._db.GetLatestTimestamp()+datetime.timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S'))
    for dataset in datasets:
      i = -1
      # Search for the last non empty entry
      while dataset['data'][i] is None:
        i -= 1
      dataset['data'].append(dataset['data'][i])

    return json.dumps(
        {'data':{
            'labels': labels,
            'datasets': datasets,
            'drinkers': self._characters,
            'total': self._db.GetTotalAmount() / 100.0}}
        ).encode()


def ParseArguments():
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
      '--lame', dest='lame', action='store_true',
      help='uses a lame method for graphs, by plotting NFC scans as nodes')
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


def MakeHandlerClassFromArgv(init_args):
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
