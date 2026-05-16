"""Serves the beerlog data in a website"""

import argparse
import datetime
import html
import os
import sys
import http.server
import json
import socketserver
import urllib.parse

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
  <style>
    body { font-family: sans-serif; padding: 1em; }
    #chart-container { width: 80%; margin-bottom: 1.5em; }
    #peak-speeds { width: 80%; clear: both; }
    #peak-speed-table { width: 100%; border-collapse: collapse; }
    #peak-speed-table th, #peak-speed-table td { border: 1px solid #ccc; padding: 0.4em 0.6em; text-align: left; }
  </style>
  <script src="beer.js"></script>
  <script src="chart.js"></script>
</head>
<body>
  <div id="total">
  </div>
  <div id="page-actions" style="margin-bottom:1em;">
    <a href="/predict"><button type="button">Keg prediction</button></a>
  </div>
  <div id="chart-container" style="min-height:360px; margin-bottom:1.5em;">
    <canvas id="myChart"></canvas>
  </div>
  <div id="peak-speeds">
    <h2>Peak speed by character</h2>
    <table id="peak-speed-table">
      <thead>
        <tr><th>Character</th><th>Peak speed (L/h)</th><th>Peak time</th></tr>
      </thead>
      <tbody id="peak-speed-table-body"></tbody>
    </table>
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
    parsed_path = urllib.parse.urlparse(self.path)
    if parsed_path.path == "/":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(self.TEMPLATE_HTML.encode())
    elif parsed_path.path == "/chart.js":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      with open(os.path.join("assets", "web", "chart.js"), "rb") as js:
        self.wfile.write(js.read())
    elif parsed_path.path == "/beer.js":
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      with open(os.path.join("assets", "web", "beer.js"), "rb") as js:
        self.wfile.write(js.read())
    elif parsed_path.path == "/predict":
      self._HandlePredictRequest()
    elif parsed_path.path == "/data":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(self.GetData())
    else:
      self.send_error(404, "error")

  def _ParseQueryParams(self):
    parsed = urllib.parse.urlparse(self.path)
    return urllib.parse.parse_qs(parsed.query)

  def _HandlePredictRequest(self):
    params = self._ParseQueryParams()
    keg_sizes = params.get("keg_size") or params.get("size")
    if not keg_sizes:
      self._RenderPredictPage()
      return

    try:
      keg_size_cl = float(keg_sizes[0]) * 100.0
      if keg_size_cl <= 0:
        raise ValueError
    except ValueError:
      self._RenderPredictPage(error="keg_size must be a positive number", keg_size=keg_sizes[0])
      return

    prediction = self._db.MakeKegPrediction(keg_size_cl)
    self._RenderPredictPage(prediction=prediction, keg_size=keg_size_cl)

  def _RenderPredictPage(self, prediction=None, keg_size=None, error=None):
    error_html = ""
    if error:
      error_html = '<p style="color:red;">{0}</p>'.format(html.escape(error))

    page = """
<html>
<head>
  <title>Keg prediction</title>
  <style>
    body {{ font-family: sans-serif; padding: 1em; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
    th, td {{ border: 1px solid #ccc; padding: 0.5em 0.75em; text-align: left; }}
    th {{ background: #f8f8f8; }}
    input[type=text] {{ width: 4em; }}
    .content {{ max-width: 800px; }}
  </style>
</head>
<body>
  <div class="content">
    <h1>Keg prediction</h1>
    <form action="/predict" method="get">
      <label for="keg_size">Keg size (liters):</label>
      <input id="keg_size" name="keg_size" type="text" value="{keg_size}" />
      <button type="submit">Predict</button>
    </form>
    {error_html}
""".format(keg_size=int((keg_size or 0) / 100), error_html=error_html)

    if prediction is not None:
      page += f"""
    <h2>Prediction result</h2>
    <table>
      <tbody>
        <tr>
          <th>Keg size (L)</th><td>{prediction["keg_size_cl"] / 100:.2f}</td>
        </tr>
        <tr>
          <th>Estimated left (L)</th><td>{prediction["estimated_left_cl"] / 100:.2f} ({prediction["total_consumed_cl"] / 100:.2f}L consumed and {prediction["pertes_percent"]}% loss)</td>
        </tr>
        <tr>
          <th>Average daily(active) L/h</th><td>{prediction["average_hourly_cl"] / 100:.2f}</td>
        </tr>
        <tr>
          <th>Predicted empty time</th><td>{prediction["predicted_empty_time"]}</td>
        </tr>
        <tr>
          <th>Should open new keg?</th><td><strong>{"Yes" if prediction["should_open_new_keg"] else "No"}</strong> (empty before {datetime.datetime.now().replace(hour=1, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)})</td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    self.wfile.write(page.encode())

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

    total_drunk = self._db.GetAmountInWindow(start=first_scan, end=last_scan)

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
          self._db.GetAmountInWindow(
            start=first_scan + datetime.timedelta(seconds=(hour - (window_size / 2)) * 3600),
            end=first_scan + datetime.timedelta(seconds=(hour + (window_size / 2)) * 3600),
          )
          or 0
        ) / window_size
        speed_by_hour.append(total_l_per_hour / 100.0)
        if total_l_per_hour / 100 > peaks_window["total"]["amount"]:
          peaks_window["total"] = {
            "amount": total_l_per_hour / 100,
            "time": str(first_scan + datetime.timedelta(seconds=hour * 3600)),
          }
        for alcoolique in self._characters:
          consumed_char = self._db.GetAmountInWindow(
            start=first_scan + datetime.timedelta(seconds=(hour - (window_size / 2)) * 3600),
            end=first_scan + datetime.timedelta(seconds=(hour + (window_size / 2)) * 3600),
            name=alcoolique,
          )
          consumed_char_speed = (consumed_char or 0) / window_size / 100.0
          if (
            alcoolique not in peaks_window
            or consumed_char_speed > peaks_window[alcoolique]["amount"]
          ):
            peaks_window[alcoolique] = {
              "amount": consumed_char_speed,
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


if __name__ == "__main__":
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
