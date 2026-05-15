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

DEFAULT_DB = os.path.join("beerlog.sqlite")
DEFAULT_TAGS_FILE = os.path.join("known_tags.json")
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
    assert self.options is not None, "options should be set before calling _Setup"
    self._db = beerlogdb.BeerLogDB(self.options.database)
    self._db.LoadTagsDB(self.options.known_tags)
    self._characters = self._db.GetAllCharacterNames()
    self._all_data = self._db.GetAllData()

  def do_GET(self):  # pylint: disable=invalid-name
    """Handles all GET requests."""
    if self.path == "/":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(self.TEMPLATE_HTML.format().encode())
    elif self.path == "/chart.js":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      with open(os.path.join("assets", "web", "chart.js"), "rb") as js:
        self.wfile.write(js.read())
    elif self.path == "/beer.js":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      with open(os.path.join("assets", "web", "beer.js"), "rb") as js:
        self.wfile.write(js.read())
    elif self.path == "/data":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(self.GetData())
    else:
      self.send_error(404, "error")

  def _GetAmountFromName(self, name, at=None):
    """Gets the amount of beer consumed by a character at a specific time.

    Args:
      name(str): the realname of the character.
      at(datetime): the time to get the amount at. If None, gets the latest amount.

    Returns:
      int: the amount of beer consumed in cl.
    """
    total = 0
    if at is None:
      at = datetime.datetime.now()
    for entry in reversed(self._all_data):
      if entry.character_name.lower() == name.lower() and entry.timestamp <= at:
        total += entry.amount

    return total

  def _GetAmountInWindow(self, start, end, name=None):
    """Gets the amount of beer consumed by a character in a specific time window.

    Args:
      start(datetime): the start of the time window.
      end(datetime): the end of the time window.
      name(str): the realname of the character. If None, gets the total amount for all characters.
    """
    total = 0
    for entry in self._all_data:
      if entry.timestamp >= start and entry.timestamp <= end:
        if name is None or entry.character_name.lower() == name.lower():
          total += entry.amount

    return total

  def GetData(self):
    """Builds a dict to use with Chart.js."""
    first_scan = self._db.GetEarliestTimestamp().replace(minute=0, second=0, microsecond=0)
    last_scan = self._db.GetLatestTimestamp().replace(
      minute=0, second=0, microsecond=0
    ) + datetime.timedelta(hours=1)
    delta = last_scan - first_scan
    total_hours = int((delta.total_seconds() / 3600))
    if total_hours > MAX_HOURS:
      msg = (
        "We calculated there are {0:d} hours between {1!s} and {2!s}, "
        "which is more than the expected max number of hours in a month"
        ": {3:d}"
      ).format(total_hours, first_scan, last_scan, MAX_HOURS)
      raise Exception(msg)
    fields = []  # This is the X axis
    datasets = {}  # {'alcoolique': ['L cummulés']}

    total_drunk = self._GetAmountInWindow(start=first_scan, end=last_scan)

    for hour in range(total_hours + 1):
      timestamp = first_scan + datetime.timedelta(seconds=hour * 3600)
      fields.append(timestamp.strftime("%a %Hh%M"))
      for alcoolique in self._characters:
        cl = self._GetAmountFromName(alcoolique, at=timestamp)
        if alcoolique in datasets:
          datasets[alcoolique].append(cl)
        else:
          datasets[alcoolique] = [cl]

    total_by_hour = [
      sum(datasets[name][hour] for name in self._characters) for hour in range(total_hours)
    ]
    window_size = 2
    peaks_window = {"total": {"amount": 0, "start": None}}

    speed_by_hour = []

    if total_hours > window_size:
      for hour in range(total_hours + 1):
        total_l_per_hour = (
          self._GetAmountInWindow(
            start=first_scan + datetime.timedelta(seconds=(hour - (window_size / 2)) * 3600),
            end=first_scan + datetime.timedelta(seconds=(hour + (window_size / 2)) * 3600),
          )
          / window_size
        )
        speed_by_hour.append(total_l_per_hour / 100.0)
        if total_l_per_hour / 100 > peaks_window["total"]["amount"]:
          peaks_window["total"] = {
            "amount": total_l_per_hour / 100,
            "time": str(first_scan + datetime.timedelta(seconds=hour * 3600)),
          }
        for alcoolique in self._characters:
          consumed_char = self._GetAmountInWindow(
            start=first_scan + datetime.timedelta(seconds=(hour - (window_size / 2)) * 3600),
            end=first_scan + datetime.timedelta(seconds=(hour + (window_size / 2)) * 3600),
            name=alcoolique,
          )
          if (
            alcoolique not in peaks_window
            or consumed_char / 100 > peaks_window[alcoolique]["amount"]
          ):
            peaks_window[alcoolique] = {
              "amount": consumed_char / 100,
              "time": str(first_scan + datetime.timedelta(seconds=hour * 3600)),
            }

    peak_by_character = [[c, p] for c, p in peaks_window.items() if c != "total"]
    peak_by_character.sort(key=lambda x: x[1]["amount"], reverse=True)

    # Formating for Charts.js

    output_datasets = []  # [{'label': 'alcoolique', 'data': ['L cummulés']}]
    for k, v in sorted(datasets.items(), key=lambda x: x[1][-1], reverse=True):
      output_datasets.append({"label": k, "data": v})
    output_datasets.append({"label": "Total cumulative", "data": total_by_hour, "order": 0})
    output_datasets.append({"label": "Total speed", "data": speed_by_hour, "order": 1})
    return json.dumps(
      {
        "data": {
          "labels": fields,
          "datasets": output_datasets,
          "drinkers": self._characters,
          "total": total_drunk / 100.0,
          "peak_total": peaks_window["total"],
          "peak_by_character": peak_by_character,
        }
      }
    ).encode()


def ParseArguments() -> argparse.Namespace:
  """Parses arguments.

  Returns:
    argparse.NameSpace: the parsed arguments.
  """

  parser = argparse.ArgumentParser(description="BeerLog")
  parser.add_argument(
    "--database",
    dest="database",
    action="store",
    default=DEFAULT_DB,
    help="the path to the sqlite file",
  )
  parser.add_argument(
    "--known_tags",
    dest="known_tags",
    action="store",
    default=DEFAULT_TAGS_FILE,
    help="the known tags file to use to use",
  )
  parser.add_argument(
    "--port", dest="port", action="store", default=DEFAULT_PORT, type=int, help="port to listen at"
  )

  parsed_args = parser.parse_args()

  if not os.path.isfile(parsed_args.database):
    print("Could not find a sqlite file at {0!s}".format(parsed_args.database))
    sys.exit(1)
  if not os.path.isfile(parsed_args.known_tags):
    print("Could not find a known tags JSON file at {0!s}".format(parsed_args.known_tags))
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

HandlerClass = MakeHandlerClassFromArgv(app_args)

print("Server listening on port {0:d}...".format(app_args.port))
httpd = socketserver.TCPServer(("", app_args.port), HandlerClass)
try:
  httpd.serve_forever()
except KeyboardInterrupt:
  pass
print("Shutting Down")
httpd.server_close()
