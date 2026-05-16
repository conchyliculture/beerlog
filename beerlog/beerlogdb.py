"""Wrapper module for a database."""

from __future__ import print_function

import datetime
import json

import peewee

from beerlog import errors
from beerlog import constants


database_proxy = peewee.Proxy()


# pylint: disable=no-init
class BeerModel(peewee.Model):
  """Model for the database."""

  id = None

  class Meta:
    """Sets Metadata for the database."""

    database = database_proxy


class Entry(BeerModel):
  """class for one Entry in the BeerLog database."""

  character_name = peewee.CharField()
  amount = peewee.IntegerField(default=constants.DEFAULT_GLASS_SIZE)
  timestamp = peewee.DateTimeField(default=datetime.datetime.now)
  pic = peewee.CharField(null=True)


class BeerLogDB:
  """Wrapper for the database."""

  def __init__(self, database_path: str):
    self.database_path = database_path
    sqlite_db = peewee.SqliteDatabase(self.database_path)
    database_proxy.initialize(sqlite_db)

    sqlite_db.create_tables([Entry], safe=True)

    self.known_tags_list = {}
    self.cutoff_hour = 6  # We don't expect a scan after 6am
    self.pertes_percent = 7

  def Connect(self):
    """Connects to the database."""
    database_proxy.connect()

  def Close(self):
    """Closes the database."""
    database_proxy.close()

  def GetHexFromName(self, name):
    """Returns the hex id for a specific realname.

    Args:
        name(str): the realname

    Returns:
        str: the hexid
    """
    for hexid, data in self.known_tags_list.items():
      if "realname" in data:
        if data["realname"].lower() == name.lower():
          return hexid
    return None

  def AddNameEntry(self, character_name, pic=None, time=None):
    character_hexid = self.GetHexFromName(character_name)
    if not character_hexid:
      raise errors.BeerLogError(f"cannot find realname {character_name}")
    self.AddEntry(character_hexid, pic=pic, time=time)

  def AddEntry(self, character_hexid, pic=None, time=None):
    """Inserts an entry in the database.

    Args:
      character_hexid(str): the hexid of the character in the tag.
      pic(str): the path to a picture.
      time(datetime): the optional time to set when adding the Entry.

    Returns:
      Entry: the Entry that was stored in the database.
    """
    amount = self.GetGlassFromHexID(character_hexid)
    character_name = self.GetNameFromHexID(character_hexid)
    if time:
      entry = Entry.create(character_name=character_name, amount=amount, timestamp=time, pic=pic)
    else:
      entry = Entry.create(
        character_name=character_name, amount=amount, timestamp=datetime.datetime.now(), pic=pic
      )
    return entry

  def GetAllData(self):
    """Returns all the data in the database.

    Returns:
      list[Entry]: a list of all the Entry in the database.
    """
    return list(Entry.select().order_by(Entry.timestamp.asc()).execute())

  def GetAllCharacterNames(self) -> list[str]:
    """Gets all active characters."""
    query = Entry.select(Entry.character_name).distinct()
    return [entry.character_name for entry in query.execute()]

  def GetEntriesCount(self):
    """Returns the number of entries."""
    count = Entry.select().count()  # pylint: disable=no-value-for-parameter
    return count

  def GetEntryById(self, entry_id):
    """Returns an Entry by its primary key.

    Args:
      entry_id(int): the id we're looking for.

    Returns:
      Entry: the corresponding Entry, or None if it wasn't found.
    """
    try:
      entry = Entry.get(Entry.id == entry_id)
    except peewee.DoesNotExist as _:
      return None
    return entry

  def CountAll(self):
    """Returns the number of Entry

    Returns:
      int: the total number of Entry lines in the database.
    """
    return Entry.select().count(None)

  def GetTotalDailyAverageConsumption(self):
    """Returns the average consumption per day.

    Returns:
      float: the averageconsumption per day, in cL.
    """
    total_cl = self.GetTotalAmount()
    earliest_timestamp = self.GetEarliestTimestamp()
    if not earliest_timestamp:
      return 0.0
    days = (self.GetLatestTimestamp() - earliest_timestamp).total_seconds() / 86400.0
    if days <= 2:
      raise errors.BeerLogError("Not enough data to compute a reliable daily average consumption")
    return total_cl / days

  def GetScoreBoard(self):
    """Returns a query with the scoreboard.

    Returns:
      peewee.ModelSelect: the query.
    """
    query = (
      Entry.select(
        Entry,
        peewee.fn.SUM(Entry.amount).alias("total"),
        peewee.fn.MAX(Entry.timestamp).alias("last"),
      )
      .group_by(Entry.character_name)
      .order_by(
        peewee.SQL("total").desc(),
        (peewee.fn.MAX(Entry.timestamp)).asc(),
      )
    )
    return query

  def GetGlassFromName(self, name):
    """Returns the corresponding glass from a uid

    Args:
      name(str): the character name.
    Returns:
      int: the glass size for a character, or the default value if not found.
    """

    entry = (
      Entry.select(Entry.amount)
      .where(Entry.character_name == name)
      .order_by(Entry.timestamp.desc())
      .first()
    )
    if not entry:
      return constants.DEFAULT_GLASS_SIZE
    return entry.amount

  def GetGlassFromHexID(self, uid):
    """Returns the corresponding glass from a uid

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      int: the glass size for a tag uid, or the default value if not found.
    Raises:
      errors.BeerLogError: if the uid can't be found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      raise errors.BeerLogError("Unknown character for tag {0:s}".format(uid))

    return tag_object.get("glass", constants.DEFAULT_GLASS_SIZE)

  def LoadTagsDB(self, known_tags_path):
    """Loads the external known tags list.

    Args:
      known_tags_path(str): path to the known_tags.json file.
    Raises:
      errors.BeerLogError: if we couldn't load the file.
    """
    try:
      with open(known_tags_path, "r") as json_file:
        self.known_tags_list = json.load(json_file)
    except IOError as e:
      raise errors.BeerLogError(
        "Could not load known tags file {0} with error {1!s}".format(known_tags_path, e)
      )
    except ValueError as e:
      raise errors.BeerLogError("Known tags file {0} is invalid: {1!s}".format(known_tags_path, e))

  def GetNameFromHexID(self, uid):
    """Returns the corresponding name from a uid
    Entry.where()

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      str: the corresponding name for that tag uid.
    Raises:
      errors.BeerLogError: if the uid can't be found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      raise errors.BeerLogError("Unknown character for tag {0:s}".format(uid))
    return tag_object.get("realname") or tag_object.get("name")

  def GetEarliestTimestamp(self):
    """Returns the earliest timestamp."""
    query = Entry.select(peewee.fn.MIN(Entry.timestamp))
    return query.scalar()  # pylint: disable=no-value-for-parameter

  def GetEarliestEntry(self, after: datetime.datetime | None = None) -> Entry | None:
    """Returns the earliest Entry.

    Args:
      after(datetime.datetime): an optional timestamp from which to start
        searching.
    Returns:
      Entry: the first entry.
    """
    if after:
      query = (
        Entry.select(Entry)
        .where(Entry.timestamp >= after)
        .group_by(Entry.timestamp)
        .order_by(Entry.timestamp.asc())
      )
    else:
      query = (
        Entry.select(Entry)
        .group_by(Entry.timestamp)
        .having(Entry.timestamp == peewee.fn.MIN(Entry.timestamp))
      )
    try:
      return query.get()
    except Exception:  # pylint: disable=broad-except
      return None

  def GetLatestEntry(self, before: datetime.datetime | None = None) -> Entry | None:
    """Returns the latest Entry.

    Args:
      before(datetime.datetime): an optional timestamp from which to start
        searching.
    Returns:
      Entry: the first entry.
    """
    if before:
      query = (
        Entry.select(Entry)
        .where(Entry.timestamp <= before)
        .group_by(Entry.timestamp)
        .order_by(Entry.timestamp.desc())
      )
    else:
      query = (
        Entry.select(Entry)
        .group_by(Entry.timestamp)
        .having(Entry.timestamp == peewee.fn.MAX(Entry.timestamp))
      )
    try:
      return query.get()
    except Exception:  # pylint: disable=broad-except
      return None

  def GetLatestTimestamp(self, name=None):
    """Returns the timestamp of the last scan."""
    query = Entry.select(peewee.fn.MAX(Entry.timestamp))
    if name:
      query = query.where(Entry.character_name == name)
    return query.scalar()  # pylint: disable=no-value-for-parameter

  def GetAmountFromHexID(self, hexid, at=None):
    """Returns the amount of beer drunk for a Character.

    Args:
      hexid(str): the hexid of a character.
      at(datetime.datetime): optional maximum date to count scans.
    Returns:
      int: the amount of beer.
    """
    character_name = self.GetNameFromHexID(hexid)
    return self.GetAmountFromName(character_name, at=at)

  def GetAmountFromName(self, name, at=None):
    """Returns the amount of beer drunk for a character.

    Args:
      name(str): the name of a character.
      at(datetime.datetime): optional maximum date to count scans.
    Returns:
      int: the amount of beer.
    """
    amount_cl = 0
    if at:
      query = Entry.select(peewee.fn.SUM(Entry.amount)).where(
        Entry.character_name == name, Entry.timestamp <= at
      )
    else:
      query = Entry.select(peewee.fn.SUM(Entry.amount)).where(Entry.character_name == name)
    amount = query.scalar()
    if amount:
      amount_cl = amount
    return amount_cl

  def GetTotalAmount(self, since=None):
    """Returns the total of beer drunk, in cL.

    Args:
      since(datetime.datetime): since when.

    Returns:
      int: the total amount, in cL.

    """
    if since:
      query = Entry.select(peewee.fn.SUM(Entry.amount)).where(Entry.timestamp >= since)
    else:
      query = Entry.select(peewee.fn.SUM(Entry.amount))
    return query.scalar() or 0  # pylint: disable=no-value-for-parameter

  def GetDataFromName(self, name):
    """Returns the accumulated amount for a character name.

    Example:
      (timestamp1, 50)
      (timestamp2, 100)
      (timestamp3, 150)
      ....

    Args:
      name(str): the name to search for.
    Returns:
      peewee.ModelSelect: the query.
    """
    query = Entry.select(
      Entry.timestamp, peewee.fn.SUM(Entry.amount).over(order_by=[Entry.timestamp]).alias("sum")
    ).where(Entry.character_name == name)
    return query.execute()

  def GetAverageTotalHourlyConsumption(self):
    """Returns the average total hourly consumption.

    Returns:
      list[dict]: a list of dict with keys "time" and "average_consumed_l".
    """
    first_scan = self.GetEarliestTimestamp()
    first_day = first_scan.replace(hour=0, minute=0, second=0, microsecond=0)
    last_scan = self.GetLatestTimestamp()
    days = (last_scan.date() - first_scan.date()).days + 1
    averages = []
    for day in range(days):
      first_scan_day = self.GetEarliestEntry(
        after=first_day + datetime.timedelta(days=day) + datetime.timedelta(hours=self.cutoff_hour)
      )
      if first_scan_day is None:
        continue
      first_scan_day = first_scan_day.timestamp
      last_scan_day = self.GetLatestEntry(
        before=first_day
        + datetime.timedelta(days=day + 1)
        + datetime.timedelta(hours=self.cutoff_hour)
      )
      if last_scan_day is None:
        continue
      last_scan_day = last_scan_day.timestamp
      amount = 0
      for entry in self.GetEntriesInWindow(start=first_scan_day, end=last_scan_day).execute():  # pyright: ignore[reportArgumentType]
        amount += entry.amount
      drinking_hours = (last_scan_day - first_scan_day).total_seconds() / 3600
      if drinking_hours <= 0:
        continue
      averages.append(amount / drinking_hours)

    return round(sum(averages) / len(averages), 2) if averages else 0.0

  def MakeKegPrediction(self, keg_size_cl, now: datetime.datetime | None = None):
    if keg_size_cl <= 100 and now is not None:
      raise errors.BeerLogError(
        f"A keg size of {keg_size_cl} cL is too small for a prediction. Please provide a valid keg size in cL."
      )
    now = datetime.datetime.now() if now is None else now
    today_start = now.replace(hour=self.cutoff_hour, minute=0, second=0, microsecond=0)
    elapsed_seconds = max(1, (now - today_start).total_seconds())

    total_today_cl = 0
    for entry in self.GetEntriesInWindow(start=today_start, end=now).execute():
      total_today_cl += entry.amount

    if total_today_cl == 0:
      raise errors.BeerLogError(
        "Not enough data to make a prediction for today (between {0} and {1})".format(
          today_start, now
        )
      )
    total_cl = self.GetTotalAmount() * (1 + self.pertes_percent / 100)
    first_scan = self.GetEarliestTimestamp()
    days_of_data = max(1, (now.date() - first_scan.date()).days + 1)
    avg_daily_cl = total_cl / days_of_data

    average_hourly_cl = self.GetAverageTotalHourlyConsumption()

    amount_left_cl = keg_size_cl - (total_cl % keg_size_cl)

    if average_hourly_cl <= 0:
      empty_time = None
      empty_in_hours = None
    else:
      empty_in_hours = amount_left_cl / average_hourly_cl
      empty_time = now + datetime.timedelta(hours=empty_in_hours)

    should_open_new_keg = False
    if amount_left_cl <= 0:
      should_open_new_keg = True
    if empty_time and empty_time <= (
      now.replace(hour=1, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    ):
      should_open_new_keg = True

    return {
      "pertes_percent": self.pertes_percent,
      "keg_size_cl": keg_size_cl,
      "current_time": now.isoformat(),
      "today_consumed_cl": total_today_cl,
      "total_consumed_cl": total_cl,
      "average_hourly_cl": average_hourly_cl,
      "estimated_left_cl": round(amount_left_cl),
      "predicted_empty_time": empty_time.strftime("%Y-%m-%dT%H:%M:%S") if empty_time else None,
      "empty_in_hours": round(empty_in_hours, 2) if empty_in_hours is not None else None,
      "should_open_new_keg": should_open_new_keg,
      "avg_daily_consumption": avg_daily_cl,
      "elapsed_hours_today": round(elapsed_seconds / 3600.0, 2),
    }

  def GetEntriesInWindow(self, start: datetime.datetime, end: datetime.datetime) -> peewee.Select:
    """Gets the amount of beer consumed by a character in a specific time window.

    Args:
      start(datetime): the start of the time window.
      end(datetime): the end of the time window.
    """
    query = Entry.select(Entry).where(Entry.timestamp >= start, Entry.timestamp <= end)
    return query


# vim: tabstop=2 shiftwidth=2 expandtab
