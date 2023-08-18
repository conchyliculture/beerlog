"""Set of helper methods."""

import datetime

def GetShortLastBeer(last, now=None):
  """Returns a shortened string for the delta between now and last scan.

  Args:
    last(datetime.datetime): timestamp of the last scan.
    now(datetime.datetime): an optional time reference.
      The current datetime if None.
  Returns:
    str: the time delta since the last scan and now.
  """
  if not now:
    now = datetime.datetime.now()
  if type(last) == str:
      last = datetime.datetime.strptime(last, '%Y-%m-%d %H:%M')
  delta = now - last
  seconds = int(delta.total_seconds())
  if seconds == 0:
    return '  0s'
  periods = [
      ('yr', 60*60*24*365),
      ('mo', 60*60*24*30),
      ('d', 60*60*24),
      ('h', 60*60),
      ('m', 60),
      ('s', 1)
  ]
  result = ''
  for period_name, period_seconds in periods:
    if seconds >= period_seconds:
      period_value, seconds = divmod(seconds, period_seconds)
      result += '{0:d}{1:s}'.format(period_value, period_name)
      if period_name not in ['h', 'm']:
        break
      if len(result) >= 4:
        break
  if result == '':
    result = 'Unk?'
  return '{0: >4}'.format(result[0:4])

def GetShortAmountOfBeer(amount):
  """Returns a shortened string for an volume in Litre

  Args:
    amount(float): quantity, in L.
  Returns:
    str: the human readable string.
  """
  if amount >= 999.5:
    return 'DEAD'
  if amount >= 99.5:
    return '{0:>4d}'.format(int(round(amount)))
  return '{0:4.3g}'.format(amount)
