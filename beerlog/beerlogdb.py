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


def BeerPerCharacter(character, amount):
  """Helper function to generate the SQL expression for the total amount
  of beer drunk."""
  return peewee.Expression(character.glass, '*', amount)


class Character(BeerModel):
  """class for one Character in the BeerLog database."""
  hexid = peewee.CharField()
  glass = peewee.IntegerField(default=constants.DEFAULT_GLASS_SIZE)

  @property
  def name(self):
    """Gets the corresponding name from hexid using the parent db object
    method."""
    return self._meta.database.GetNameFromHexID(self.hexid)

  def GetAmountDrunk(self, at=None):
    """Gets the amount of beer drunk."""
    return self._meta.database.GetAmountFromHexID(self.hexid, self.glass, at=at)



class Entry(BeerModel):
  """class for one Entry in the BeerLog database."""
  character = peewee.ForeignKeyField(Character, backref='entries')
  timestamp = peewee.DateTimeField(default=datetime.now)
  pic = peewee.CharField(null=True)

class BeerLogDB():
  """Wrapper for the database."""

  def __init__(self, database_path):
    self.database_path = database_path
    sqlite_db = peewee.SqliteDatabase(self.database_path)
    database_proxy.initialize(sqlite_db)

    # This is used for the Character.name property
    sqlite_db.GetNameFromHexID = self.GetNameFromHexID
    # This is used for the Character.GetAmountDrink() method
    sqlite_db.GetAmountFromHexID = self.GetAmountFromHexID

    sqlite_db.create_tables([Character, Entry], safe=True)

    self.known_tags_list = None

  def Connect(self):
    """Connects to the database."""
    database_proxy.connect()

  def Close(self):
    """Closes the database."""
    database_proxy.close()

  def AddEntry(self, character_hexid, pic, time=None):
    """Inserts an entry in the database.

    Args:
      character_hexid(str): the hexid of the character in the tag.
      pic(str): the path to a picture.
      time(datetime): the optional time to set when adding the Entry.

    Returns:
      Entry: the Entry that was stored in the database.
    """
    glass = self.GetGlassFromHexID(character_hexid)
    character, _ = Character.get_or_create(hexid=character_hexid, glass=glass)
    if time:
      entry = Entry.create(
          character=character,
          timestamp=time,
          pic=pic
      )
    else:
      entry = Entry.create(
          character=character,
          pic=pic
      )
    return entry

  def GetAllCharacters(self):
    """Gets all active characters."""
    query = Character.select(Character).join(Entry).where(
        Character.id == Entry.character_id).distinct()
    return query

  def GetCharacterFromHexID(self, character_hexid):
    """Returns a Character from its hexid.

    Args:
      character_hexid(str): the character's hexid.
    Returns:
      Character: a Character object, or None.
    """
    return Character.get_or_none(Character.hexid == character_hexid)

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
        Character,
        peewee.fn.MAX(Entry.timestamp).alias('last'),
        BeerPerCharacter(Character, peewee.fn.COUNT()).alias('amount')
    ).join(Character).group_by(Entry.character).order_by(
        BeerPerCharacter(Character, peewee.fn.COUNT()).desc(),
        (peewee.fn.MAX(Entry.timestamp)).desc()
    )

    return query

  def GetGlassFromHexID(self, uid):
    """Returns the corresponding glass from a uid

    Args:
      uid(str): the uid in form 0x0580000000050002
    Returns:
      int: the corresponding glass for a tag uid, or None if no name is found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      return None

    return tag_object.get('glass')

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
      str: the corresponding name for that tag uid, or None if no name is found.
    """
    tag_object = self.known_tags_list.get(uid)
    if not tag_object:
      return None

    return tag_object.get('realname') or tag_object.get('name')

  def GetEarliestTimestamp(self):
    """Returns the timestamp of the first scan."""
    return Entry.select(peewee.fn.MIN(Entry.timestamp)).scalar() #pylint: disable=no-value-for-parameter

  def GetLatestTimestamp(self):
    """Returns the timestamp of the last scan."""
    return Entry.select(peewee.fn.MAX(Entry.timestamp)).scalar() #pylint: disable=no-value-for-parameter

  def GetAmountFromHexID(self, hexid, glass_size, at=None):
    """Returns the amount of beer drunk for a Character.

    Args:
      hexid(str): the hexid of a character.
      glass_size(int): the size of the character's glass.
      at(datetime.datetime): optional maximum date to count scans.
    Returns:
      int: the amount of beer.
    """
    character = self.GetCharacterFromHexID(hexid)
    amount_cl = 0
    if character:
      if at:
        entries = Entry.select(Entry).where(
            Entry.character == character,
            Entry.timestamp <= at).count()
      else:
        entries = Entry.select(Entry).where(
            Entry.character == character).count()
      amount_cl = entries * glass_size
    return amount_cl

# vim: tabstop=2 shiftwidth=2 expandtab
