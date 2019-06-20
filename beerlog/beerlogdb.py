"""Wrapper module for a database."""

from __future__ import print_function

from datetime import datetime

from peewee import CharField
from peewee import DateTimeField
from peewee import DoesNotExist
from peewee import Model
from peewee import Proxy
from peewee import SqliteDatabase
from peewee import fn

database_proxy = Proxy()
# pylint: disable=no-init
class BeerModel(Model):
  """Model for the database."""
  class Meta(object):
    """Sets Metadata for the database."""
    database = database_proxy

class Entry(BeerModel):
  """class for one Entry in the BeerLog database."""
  character = CharField()
  timestamp = DateTimeField(default=datetime.now)
  pic = CharField(null=True)

class BeerLogDB(object):
  """Wrapper for the database."""

  def __init__(self, database_path):
    self.database_path = database_path
    sqlite_db = SqliteDatabase(self.database_path)
    database_proxy.initialize(sqlite_db)

    sqlite_db.create_tables([Entry], safe=True)

  def Connect(self):
    """Connects to the database."""
    database_proxy.connect()

  def Close(self):
    """Closes the database."""
    database_proxy.close()

  def AddEntry(self, character, pic):
    """Inserts an entry in the database.

    Args:
      character(str): the name of the character in the tag.
      pic(str): the path to a picture.

    Returns:
      Entry: the Entry that was stored in the database.
    """
    entry = Entry.create(
        character=character,
        pic=pic
    )
    return entry

  def GetEntryById(self, entry_id):
    """Returns an Entry by its primary key.

    Args:
      entry_id(int): the id we're looking for.

    Returns:
      Entry: the corresponding Entry, or None if it wasn't found.
    """
    try:
      entry = Entry.get(Entry.id == entry_id)
    except DoesNotExist as _:
      return None
    return entry

  def CountAll(self):
    """Returns the number of Entry

    Returns:
      int: the total number of Entry lines in the database.
    """
    return Entry.select().count(None)

  def GetScoreBoard(self, limit=10):
    """Returns a query with the scoreboard.

    Args:
      limit(int): the number of top scorer to display.
    Returns:
      peewee.ModelSelect: the query.
    """
    query = Entry.select(
        Entry,
        fn.MAX(Entry.timestamp).alias('last'),
        fn.COUNT().alias('count')
    ).group_by(Entry.character).limit(limit).order_by(fn.COUNT().desc())
    return query

# vim: tabstop=2 shiftwidth=2 expandtab
