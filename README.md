# BeerLog

Program NFC215 tags with some code, and use that to keep a leaderboard of who is drinking the manyest beers.

## Installation

```
virtualenv -p python2 beerlog
cd beerlog
source bin/activate
git clone https://github.com/conchyliculture/beerlog
cd beerlog
wget  https://goto.ninja/beertags -O - | jq ".[keys[1]]" > known_tags.json
