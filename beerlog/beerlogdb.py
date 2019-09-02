"""Wrapper module for a database."""

from __future__ import print_function

from datetime import datetime
import json

import peewee

from beerlog import errors
from beerlog import constants


database_proxy = peewee.Proxy()
# pylint: disable=no-init
class BeerModel(peewee.Model):
  """Model for the database."""
  class Meta():
    """Sets Metadata for the database."""
    database = database_proxy

class Entry(BeerModel):
  """class for one Entry in the BeerLog database."""
  character_name = peewee.CharField()
  amount = peewee.IntegerField(default=constants.DEFAULT_GLASS_SIZE)
  timestamp = peewee.DateTimeField(default=datetime.now)
  pic = peewee.CharField(null=True)

class BeerLogDB():
  """Wrapper for the database."""

  def __init__(self, database_path):
    self.database_path = database_path
    sqlite_db = peewee.SqliteDatabase(self.database_path)
    database_proxy.initialize(sqlite_db)

    sqlite_db.create_tables([Entry], safe=True)

    self.known_tags_list = None

  def Connect(self):
    """Connects to the database."""
    database_proxy.connect()

  def Close(self):
    """Closes the database."""
    database_proxy.close()

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
      entry = Entry.create(
          character_name=character_name,
          amount=amount,
          timestamp=time,
          pic=pic
      )
    else:
      entry = Entry.create(
          character_name=character_name,
          amount=amount,
          pic=pic
      )
    return entry

  def GetAllCharacterNames(self):
    """Gets all active characters."""
    query = Entry.select(Entry.character_name).distinct()
    return [entry.character_name for entry in query.execute()]

  def GetEntriesCount(self):
    """Returns the number of entries."""
    count = Entry.select().count() #pylint: disable=no-value-for-parameter
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

  def GetScoreBoard(self):
    """Returns a query with the scoreboard.

    Returns:
      peewee.ModelSelect: the query.
    """
    query = Entry.select(
        Entry,
        peewee.fn.SUM(Entry.amount).alias('total'),
        peewee.fn.MAX(Entry.timestamp).alias('last'),
    ).group_by(
        Entry.character_name
    ).order_by(
        peewee.SQL('total').desc(),
        (peewee.fn.MAX(Entry.timestamp)).asc(),
    )
    return query

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
      raise errors.BeerLogError('Unknown character for tag {0:s}'.format(uid))

    return tag_object.get('glass', constants.DEFAULT_GLASS_SIZE)

  def LoadTagsDB(self, known_tags_path):
    """Loads the external known tags list.

    Args:
      known_tags_path(str): path to the known_tags.json file.
    Raises:
      errors.BeerLogError: if we couldn't load the file.
    """
    try:
      with open(known_tags_path, 'r') as json_file:
        self.known_tags_list = json.load(json_file)
    except IOError as e:
      raise errors.BeerLogError(
          'Could not load known tags file {0} with error {1!s}'.format(
              known_tags_path, e))
    except ValueError as e:
      raise errors.BeerLogError(
          'Known tags file {0} is invalid: {1!s}'.format(
              known_tags_path, e))

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
      raise errors.BeerLogError('Unknown character for tag {0:s}'.format(uid))
    return tag_object.get('realname') or tag_object.get('name')

  def GetEarliestTimestamp(self):
    """Returns the earliest timestamp."""
    query = Entry.select(peewee.fn.MIN(Entry.timestamp))
    return query.scalar() #pylint: disable=no-value-for-parameter

  def GetEarliestEntry(self, after=None):
    """Returns the earliest Entry.

    Args:
      after(datetime.datetime): an optional timestamp from which to start
        searching.
    Returns:
      Entry: the first entry.
    """
    if after:
      query = Entry.select(Entry).where(
          Entry.timestamp >= after).group_by(Entry.timestamp).order_by(
              Entry.timestamp.asc())
    else:
      query = Entry.select(Entry).group_by(Entry.timestamp).having(
          Entry.timestamp == peewee.fn.MIN(Entry.timestamp))
    try:
      return query.get()
    except Exception: # pylint: disable=broad-except
      return None

  def GetLatestTimestamp(self):
    """Returns the timestamp of the last scan."""
    query = Entry.select(peewee.fn.MAX(Entry.timestamp))
    return query.scalar() #pylint: disable=no-value-for-parameter

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
          Entry.character_name == name,
          Entry.timestamp <= at)
    else:
      query = Entry.select(peewee.fn.SUM(Entry.amount)).where(
          Entry.character_name == name)
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
      query = Entry.select(peewee.fn.SUM(Entry.amount)).where(
          Entry.timestamp >= since)
    else:
      query = Entry.select(peewee.fn.SUM(Entry.amount))
    return query.scalar() or 0 # pylint: disable=no-value-for-parameter


# vim: tabstop=2 shiftwidth=2 expandtab
