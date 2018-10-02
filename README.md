# BeerLog

Program NFC215 tags with some code, and use that to keep a leaderboard of who is drinking the manyest beers.

## Installation

```
sudo apt install python2-peewee
virtualenv -p python2 --system-site-packages beerlog
pip install nfcpy
cd beerlog
source bin/activate
git clone https://github.com/conchyliculture/beerlog
cd beerlog
wget  https://goto.ninja/beertags -O - | jq ".[keys[1]]" > known_tags.json
