"""Helper methods for collecting some system data."""

import datetime
import re
import subprocess


def GetWifiStatus():
  """Return a short string with the WiFi status."""
  result = 'No WiFi'

  regexp = re.compile(r'^([^ ]+)\s+ESSID:"(.+)"$')

  try:
    output = subprocess.check_output(['/sbin/iwgetid']).decode('utf-8')
    match = regexp.search(output)
    if match:
      _, essid = match.groups()
      result = essid
  except subprocess.SubprocessError:
    pass
  return result

def GetTime():
  """Return a short string to display time.

  Returns:
    str: the time.
  """
  return datetime.datetime.now().strftime('%H:%M:%S')
