import os
import sys
from beerlog import beerlogdb
from beerlog import utils

SOURCEDB = os.path.join('beerlog.sqlite')
TAGS_FILE = os.path.join('known_tags.json')

if len(sys.argv) == 2:
  SOURCEDB = sys.argv[1]

if not os.path.isfile(SOURCEDB):
  print('{0!s} is not a file'.format(SOURCEDB))
  sys.exit(1)

db = beerlogdb.BeerLogDB(SOURCEDB)
db.LoadTagsDB(TAGS_FILE)

last_scan = db.GetLatestTimestamp()
result = [(alcoolique, db.GetAmountFromName(alcoolique, at=last_scan)) for alcoolique in db.GetAllCharacterNames()]
i = 0
for c, a in sorted(result, key=lambda result: result[1], reverse=True):
  print('{0:2d} {1:<10s}'.format(i+1, c)+' '+utils.GetShortAmountOfBeer(round(a/100.0, 1))+'L')
  i+=1
