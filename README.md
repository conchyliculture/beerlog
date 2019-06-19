# BeerLog

Program NFC215 tags with some code, and use that to keep a leaderboard of who is drinking the manyest beers.

## Installation

```
sudo apt install python-virtualenv
virtualenv -p python2 --system-site-packages beerlog
cd beerlog
source bin/activate

git clone https://github.com/conchyliculture/beerlog
pip install -r requirements.txt


sudo apt install jq
wget  https://goto.ninja/beertags -O - | jq ".[keys[1]]" > known_tags.json

cd beerlog
PYTHONPATH="." python beerlog.py
```
