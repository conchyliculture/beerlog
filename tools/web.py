"""Serves the beerlog data in a website"""

import datetime
import os
import sys
import http.server
import json
import socketserver

from beerlog import beerlogdb

socketserver.TCPServer.allow_reuse_address = True

SOURCEDB = os.path.join('beerlog.sqlite')
TAGS_FILE = os.path.join('known_tags.json')

if len(sys.argv) == 2:
  SOURCEDB = sys.argv[1]

PORT = 8000

if not os.path.isfile(SOURCEDB):
  print('{0!s} is not a file'.format(SOURCEDB))
  sys.exit(1)

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
  <div style="width:90%; height:80%">
    <canvas id="myChart"></canvas>
  </div>
  <script>update_graph("/data", drawChart);</script>
</body></html> """

  def __init__(self, *args):
    self._characters = None
    self._datasets = None
    self._db = None
    super().__init__(*args)

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

  def _UpdateDatasets(self, character, new_amount):
    # [
    #    {'label': 'alcoolique1', 'data': ['total at tick1', 'total at tick2']}
    #    {'label': 'alcoolique2', 'data': ['total at tick1', 'total at tick2']}
    # ]
    if not self._datasets:
      self._datasets = []
      for char in self._characters:
        self._datasets.append({
            'label': char,
            'data': [0],
            'steppedLine': True,
            'spanGaps': True}) # Draw 'null' values
    for dataset in self._datasets:
      if dataset['label'] == character:
        dataset['data'].append(new_amount)
      else:
        dataset['data'].append(None)

  def _SetUpDB(self):
    if not self._db:
      self._db = beerlogdb.BeerLogDB(SOURCEDB)
      self._db.LoadTagsDB(TAGS_FILE)
      self._characters = self._db.GetAllCharacterNames()

  def GetData(self):
    """Builds a dict to use with Chart.js."""
    self._SetUpDB()

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
    for time in sorted(data):
      labels.append(time)
      character, amount = data[time]
      self._UpdateDatasets(character, amount)

    # We need one last datapoint to draw all the way to the end of times
    labels.append((
        self._db.GetLatestTimestamp()+datetime.timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S'))
    for dataset in self._datasets:
      i = -1
      # Search for the last non empty entry
      while dataset['data'][i] is None:
        i -= 1
      dataset['data'].append(dataset['data'][i])

    return json.dumps(
        {'data':{
            'labels': labels,
            'datasets': self._datasets,
            'drinkers': self._characters,
            'total': self._db.GetTotalAmount() / 100.0}}
        ).encode()


print('Server listening on port {0:d}...'.format(PORT))
httpd = socketserver.TCPServer(('', PORT), Handler)
try:
  httpd.serve_forever()
except KeyboardInterrupt:
  pass
print('Shutting Down')
httpd.server_close()
