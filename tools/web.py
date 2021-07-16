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

    # Formating for Charts.js
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
            'total': total/100.0}}
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
