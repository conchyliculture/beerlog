"""Set of helper methods."""

import datetime


SHORT_LAST_BEER_LENGTH = 4
SHORT_AMOUNT_OF_BEER_LENGTH = 4


def GetShortLastBeer(last: datetime.datetime, now: datetime.datetime | None = None) -> str:
  """Returns a shortened string for the delta between now and last scan.

  Args:
    last(datetime.datetime): timestamp of the last scan.
    now(datetime.datetime): an optional time reference.
      The current datetime if None.
  Returns:
    str: the time delta since the last scan and now.
  """
  if now is None:
    now = datetime.datetime.now()
  delta = now - last
  seconds = int(delta.total_seconds())
  if seconds == 0:
    return "  0s"
  periods = [
    ("yr", 60 * 60 * 24 * 365),
    ("mo", 60 * 60 * 24 * 30),
    ("d", 60 * 60 * 24),
    ("h", 60 * 60),
    ("m", 60),
    ("s", 1),
  ]
  result = ""
  for period_name, period_seconds in periods:
    if seconds >= period_seconds:
      period_value, seconds = divmod(seconds, period_seconds)
      result += "{0:d}{1:s}".format(period_value, period_name)
      if period_name not in ["h", "m"]:
        break
      if period_name == "m" and period_value >= 10:
        break
      if len(result) >= 4:
        break
  if result == "":
    result = "Unk?"
  return "{0: >4}".format(result[0:4])


def GetShortAmountOfBeer(amount: float) -> str:
  """Returns a shortened string for an volume in Litre

  Args:
    amount(float): quantity, in L.
  Returns:
    str: the human readable string.
  """
  if amount >= 999.5:
    return "DEAD"
  if amount >= 99.5:
    return "{0:>4d}".format(int(round(amount)))
  return "{0:4.3g}".format(amount)
