# BeerLog

Program NFC215 tags with some code, and use that to keep a leaderboard of who is drinking the manyest beers.


<p align="center"><img src='doc/cheers.gif' width="200"/></p>

Tested with [these NFC215 stickers](https://www.aliexpress.com/item/32817199724.html). Program them with your phone and your [favorite app](https://github.com/HiddenRamblings/TagMo).

NFC reader is [this one](https://www.aliexpress.com/item/32548770388.html).

Other recommended hardware, especially if the device you're setting up doesn't have access to the internet is a I2C RTC such as [this one](https://www.aliexpress.com/item/32881077060.html) which has its own battery and is pretty small.

## Installation

```
sudo apt install python3-virtualenv
virtualenv --system-site-packages beerlog
cd beerlog
source bin/activate

git clone https://github.com/conchyliculture/beerlog
pip install -r requirements.txt

sudo apt install jq
wget  https://goto.rip/beertags -O - | jq ".[keys[1]]" | jq "del(.|.[].release)" > known_tags.json
```

In `known_tags.json`, add the optional characteristics `realname` or `glass`volume to each entry:
```
{
  "0x0000000000000002": {
     "name": "Marius",
     "realname": "Raymond",
     "glass": "40" // This is in cL
}
```

This way, `Raymond` will be displayed in the UI instead of `Marius`, and we'll count 40cL for earch scan.


```


PYTHONPATH="." python beerlog/cli/beerlog_cli.py
```

If you need hardware clock, here are some helpful links:

  * [https://thepihut.com/blogs/raspberry-pi-tutorials/17209332-adding-a-real-time-clock-to-your-raspberry-pi](https://thepihut.com/blogs/raspberry-pi-tutorials/17209332-adding-a-real-time-clock-to-your-raspberry-pi)
  * Put this in `/etc/systemd/system/hwclock.service`, then enable & start the service

```
[Unit]
Description=hwclock
[Service]
Type=oneshot
ExecStart=/sbin/hwclock --hctosys
ExecStop=
[Install]
WantedBy=multi-user.target
```

## Tests

I have some!

```
python run_tests.py
```

## Development

For development purposes, you can run the code with an emulated interface.

```
apt install python3-gi
```
