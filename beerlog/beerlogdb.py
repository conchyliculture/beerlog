"""Wrapper module for a database."""

from __future__ import print_function

from datetime import datetime
import json

from peewee import CharField
from peewee import DateTimeField
from peewee import DoesNotExist
from peewee import Model
from peewee import Proxy
from peewee import SqliteDatabase
from peewee import fn

from beerlog.errors import BeerLogError

database_proxy = Proxy()
# pylint: disable=no-init
class BeerModel(Model):
  """Model for the database."""
  class Meta():
    """Sets Metadata for the database."""
    database = database_proxy

class Entry(BeerModel):
  """class for one Entry in the BeerLog database."""
  character = CharField()
  timestamp = DateTimeField(default=datetime.now)
  pic = CharField(null=True)

class BeerLogDB():
  """Wrapper for the database."""

  def __init__(self, database_path):
    self.database_path = database_path
    sqlite_db = SqliteDatabase(self.database_path)
    database_proxy.initialize(sqlite_db)

    sqlite_db.create_tables([Entry], safe=True)

    self.known_tags_list = None

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

  def GetScoreBoard(self):
    """Returns a query with the scoreboard.

    Returns:
      peewee.ModelSelect: the query.
    """
    query = Entry.select(
        Entry,
        fn.MAX(Entry.timestamp).alias('last'),
        fn.COUNT().alias('count')
    ).group_by(Entry.character).order_by(
        fn.COUNT().desc(),
        fn.MAX(Entry.timestamp).desc())

    return query

  def LoadTagsDB(self, known_tags_path):
    """Loads the external known tags list.

    Args:
      known_tags_path(str): path to the known_tags.json file.
    Raises:
      BeerLogError: if we couldn't load the file.
    """
    try:
      with open(known_tags_path, 'r') as json_file:
        self.known_tags_list = json.load(json_file)
    except IOError as e:
      raise BeerLogError(
          'Could not load known tags file {0} with error {1!s}'.format(
              known_tags_path, e))
    except ValueError as e:
      raise BeerLogError(
          'Known tags file {0} is invalid: {1!s}'.format(
              known_tags_path, e))

  def GetNameFromHexID(self, uid):
    """Returns the corresponding name from a uid

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      str: the corresponding name for that tag uid, or None if no name is found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      return None

    return tag_object.get('realname') or tag_object.get('name')

# vim: tabstop=2 shiftwidth=2 expandtab
