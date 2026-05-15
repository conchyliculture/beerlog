"""Helper methods for collecting some system data."""

import datetime
import netifaces
import re
import subprocess


def GetWifiStatus():
  """Return a short string with the WiFi status."""
  result = "No WiFi"

  regexp = re.compile(r'^([^ ]+)\s+ESSID:"(.+)"$')

  try:
    output = subprocess.check_output(["/sbin/iwgetid"]).decode("utf-8")
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
  return datetime.datetime.now().strftime("%H:%M:%S")


def GetIpAddress():
  """Return the IP address of the device."""
  gws = netifaces.gateways()
  # Extract the default IPv4 gateway and its interface name
  # Family 2 corresponds to AF_INET (IPv4)
  _, interface_name, *_ = gws["default"][netifaces.AF_INET]

  # Get the IP address assigned to that interface
  addresses = netifaces.ifaddresses(interface_name)
  ip_address = addresses[netifaces.AF_INET][0]["addr"]

  return ip_address
