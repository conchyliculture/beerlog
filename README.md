# BeerLog

Program NFC215 tags with some code, and use that to keep a leaderboard of who is drinking the manyest beers.

## Installation

```
sudo apt install python-virtualenv
sudo apt install python2-peewee # Or use pip
virtualenv -p python2 --system-site-packages beerlog
cd beerlog
source bin/activate
pip install nfcpy
pip install luma.oled
git clone https://github.com/conchyliculture/beerlog
cd beerlog


sudo apt install jq
wget  https://goto.ninja/beertags -O - | jq ".[keys[1]]" > known_tags.json
