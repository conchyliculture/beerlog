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
  <script src="beer.js"></script>
  <script src="chart.js"></script>
</head>
<body>
  <div id="total">
  </div>
  <div style="width:100%; height:100%">
    <canvas id="myChart"></canvas>
  </div>
  <script>update_graph("/data", drawChart);</script>
</body></html> """

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
    db = beerlogdb.BeerLogDB(SOURCEDB)
    db.LoadTagsDB(TAGS_FILE)

    first_scan = db.GetEarliestTimestamp()
    last_scan = db.GetLatestTimestamp()
    delta = last_scan - first_scan
    total_hours = int((delta.total_seconds() / 3600) + 2)
    fields = []
    datasets = {} # {'alcoolique': ['L cummulés']}
    for hour in range(total_hours):
      timestamp = (first_scan + datetime.timedelta(seconds=hour * 3600))
      timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
      fields.append(timestamp.astimezone().strftime('%Y%m%d %Hh%M'))
      for alcoolique in db.GetAllCharacterNames():
        cl = db.GetAmountFromName(alcoolique, at=timestamp)
        if alcoolique in datasets:
          datasets[alcoolique].append(cl)
        else:
          datasets[alcoolique] = [cl]

    total = 0
    totals = {} # {'alcoolique': total }
    for alcoolique in db.GetAllCharacterNames():
      cl = db.GetAmountFromName(alcoolique, at=last_scan)
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
            'drinkers': db.GetAllCharacterNames(),
            'total': total}}
        ).encode()


print('Server listening on port {0:d}...'.format(PORT))
httpd = socketserver.TCPServer(('', PORT), Handler)
try:
  httpd.serve_forever()
except KeyboardInterrupt:
  pass
print('Shutting Down')
httpd.server_close()
