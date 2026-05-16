"""Tests for the beerlogdb module"""

from __future__ import unicode_literals

import datetime
import json
import os
import tempfile
import unittest

from beerlog import beerlogdb
from beerlog import errors

# pylint: disable=protected-access


class BeerLogDBTests(unittest.TestCase):
  """Tests for the BeerLogDB class."""

  DB_PATH = ":memory:"

  def setUp(self):
    self.db = beerlogdb.BeerLogDB(self.DB_PATH)
    self.db.known_tags_list = {
      "0x0": {"name": "toto", "glass": 33},
      "0x1": {"name": "toto", "glass": 45},
      "0x2": {"name": "tutu", "glass": 50},
      "0x3": {"name": "tata", "glass": 40},
      "0x4": {"name": "titi", "glass": 40},
    }

  def tearDown(self):
    if self.DB_PATH != ":memory:":
      os.remove(self.DB_PATH)

  def testAddEntry(self):
    """Tests the AddEntry() method."""
    self.db.AddEntry("0x0")
    self.db.AddEntry("0x0")
    self.assertEqual(self.db.CountAll(), 2)

  def testGetNameFromHexID(self):
    """Tests the CharacterFromHexID() method."""
    result = self.db.GetNameFromHexID("0x0")
    self.assertEqual(result, "toto")

    result = self.db.GetNameFromHexID("0x1")
    self.assertEqual(result, "toto")

  def testGetScoreBoard(self):
    """Tests the GetScoreBoard method."""
    self.db.AddEntry("0x0")
    self.db.AddEntry("0x0")
    self.db.AddEntry("0x0")
    self.db.AddEntry("0x1")
    self.db.AddEntry("0x1")
    self.db.AddEntry("0x4")
    self.db.AddEntry("0x2")
    self.db.AddEntry("0x1")
    self.db.AddEntry("0x2")
    self.db.AddEntry("0x3")

    expected = [
      ("toto", 3 * 33 + 3 * 45, None),
      ("tutu", 2 * 50, None),
      ("titi", 1 * 40, None),  # Same amount, but oldest first
      ("tata", 1 * 40, None),
    ]
    results = [(t.character_name, t.total, t.pic) for t in self.db.GetScoreBoard()]
    self.assertEqual(expected, results, "Error in testGetScoreBoard")

  def testGetCharacters(self):
    """Test tags name/hexid operations."""
    self.db.AddEntry("0x0", "pic2")
    self.db.AddEntry("0x2", "pic2")
    self.assertEqual(["toto", "tutu"], self.db.GetAllCharacterNames())

  def testGetTotalDailyAverage(self):
    """Tests the GetTotalDailyAverage() method."""
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 2, 14, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 3, 14, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 3, 14, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 3, 14, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 3, 15, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 3, 16, 00))
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 4, 16, 30))
    self.db.AddEntry("0x1", time=datetime.datetime(2019, 1, 4, 17, 00))

    # Total of 3*33 + 45 + 50 = 244 cl in one day
    self.assertEqual(137, int(self.db.GetTotalDailyAverageConsumption()))

  def testGetAmount(self):
    """Tests for counting total amount drunk per character"""
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 1, 14, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 1, 15, 00))
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 1, 16, 00))
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 1, 16, 30))
    self.db.AddEntry("0x1", time=datetime.datetime(2019, 1, 1, 17, 00))

    self.assertEqual(datetime.datetime(2019, 1, 1, 14, 0), self.db.GetEarliestTimestamp())
    self.assertEqual(datetime.datetime(2019, 1, 1, 17, 0), self.db.GetLatestTimestamp())

    expected_entry = self.db.GetEntryById(1)
    self.assertEqual(expected_entry, self.db.GetEarliestEntry())
    expected_entry = self.db.GetEntryById(4)
    self.assertEqual(
      expected_entry, self.db.GetEarliestEntry(after=datetime.datetime(2019, 1, 1, 16, 30))
    )

    # 3 scans: 2 with 33 & 1 with 45
    self.assertEqual(2 * 33 + 1 * 45, self.db.GetAmountFromHexID("0x0"))

    # Date too old, getting nothing
    self.assertEqual(0, self.db.GetAmountFromHexID("0x0", at=datetime.datetime(2018, 1, 1, 16, 30)))

    # One scan
    self.assertEqual(
      1 * 50, self.db.GetAmountFromHexID("0x2", at=datetime.datetime(2019, 1, 1, 15, 30))
    )

  def testGetAmountInWindow(self):
    """Tests GetAmountInWindow() for inclusive window boundaries and name filtering."""
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 1, 10, 10))
    self.db.AddEntry("0x1", time=datetime.datetime(2019, 1, 1, 11, 10))
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 1, 12, 10))
    self.db.AddEntry("0x3", time=datetime.datetime(2019, 1, 1, 13, 10))

    start = datetime.datetime(2019, 1, 1, 11, 0)
    end = datetime.datetime(2019, 1, 1, 13, 0)
    entries = self.db.GetEntriesInWindow(start=start, end=end).execute()
    total = 0
    for entry in entries:
      total += entry.amount
    self.assertEqual(45 + 50, total)

    total = 0
    for entry in entries:
      if entry.character_name == "tutu":
        total += entry.amount
    self.assertEqual(50, total)

    total = 0
    for entry in entries:
      if entry.character_name == "TUTU":
        total += entry.amount
    self.assertEqual(0, total)

    start = datetime.datetime(2019, 1, 1, 13, 0)
    end = datetime.datetime(2019, 1, 1, 14, 0)
    entries = self.db.GetEntriesInWindow(start=start, end=end).execute()
    total = 0
    for entry in entries:
      total += entry.amount
    self.assertEqual(40, total)

  def testLoadTags(self):
    """Test loading the name/hexid json file."""

    with tempfile.NamedTemporaryFile(mode="w+") as temp:
      temp.write(
        json.dumps(
          {
            "0x0": {"name": "Kikoo", "glass": "30"},
            "0x2": {"name": "name", "realname": "realname", "glass": "45"},
          }
        )
      )
      temp.flush()
      self.db.LoadTagsDB(temp.name)
      thelist = self.db.known_tags_list
      self.assertEqual(2, len(thelist))

      self.assertEqual("Kikoo", self.db.GetNameFromHexID("0x0"))
      self.assertEqual("realname", self.db.GetNameFromHexID("0x2"))

      with self.assertRaises(errors.BeerLogError):
        self.assertEqual(None, self.db.GetNameFromHexID("0x1"))

      self.assertEqual(self.db.GetNameFromHexID("0x0"), "Kikoo")
      self.assertEqual(self.db.GetNameFromHexID("0x2"), "realname")

  def testMakeKegPredictionBasic(self):
    """Tests the MakeKegPrediction() method with moderate consumption."""
    # Add entries over 4 days with consistent consumption
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 7, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 7, 20, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 20, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 9, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 9, 20, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 10, 0))  # 33 cl

    result = self.db.MakeKegPrediction(200.0, now=datetime.datetime(2019, 1, 10, 20, 0))

    expected_results = {
      "average_hourly_cl": 6.6,
      "avg_daily_consumption": 60.6375,
      "elapsed_hours_today": 14.0,
      "current_time": "2019-01-10T20:00:00",
      "keg_size_cl": 200.0,
      "today_consumed_cl": 33,
      "pertes_percent": 5,
      "total_consumed_cl": 7 * 33 * (1.05),
      "estimated_left_cl": 157,
      "predicted_empty_time": "2019-01-11T19:51:21",
      "empty_in_hours": 23.86,
      "should_open_new_keg": False,
    }

    self.maxDiff = None
    self.assertEqual(expected_results, result)

  def testMakeKegPredictionShouldOpenNewKeg(self):
    """Tests the MakeKegPrediction() when keg should be opened."""

    # Heavy consumption today (multiple entries within the last few hours)
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 5, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 6, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 7, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 10, 0))

    # Add historical data from past days for daily average
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 14, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 9, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 9, 14, 0))  # 33 cl

    result = self.db.MakeKegPrediction(200.0, now=datetime.datetime(2019, 1, 10, 12, 0))

    self.assertEqual(result["keg_size_cl"], 200.0)
    self.assertEqual(result["today_consumed_cl"], (33 * 3))
    self.assertEqual(result["estimated_left_cl"], 123)
    self.assertEqual(result["empty_in_hours"], 7.7)
    self.assertTrue(result["should_open_new_keg"])

  def testMakeKegPredictionSmallKeg(self):
    """Tests the MakeKegPrediction() with a small keg size."""
    # Moderate consumption over 4 days
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 7, 10, 0))  # 50 cl
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 7, 20, 0))  # 50 cl
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 8, 10, 0))  # 50 cl
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 9, 10, 0))  # 50 cl
    self.db.AddEntry("0x2", time=datetime.datetime(2019, 1, 10, 10, 0))  # 50 cl

    result = self.db.MakeKegPrediction(500.0, now=datetime.datetime(2019, 1, 10, 12, 0))

    self.assertEqual(result["keg_size_cl"], 500.0)
    self.assertIsNotNone(result["predicted_empty_time"])
    self.assertIsNotNone(result["empty_in_hours"])
    self.assertGreater(result["estimated_left_cl"], 0)

  def testMakeKegPredictionLargeKeg(self):
    """Tests the MakeKegPrediction() with a large keg size."""
    # Light consumption over 4 days
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 7, 10, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 7, 12, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 7, 11, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 12, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 13, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 14, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 8, 15, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 9, 16, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 20, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 21, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 22, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 10, 23, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 11, 1, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 11, 2, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 11, 13, 0))  # 33 cl
    self.db.AddEntry("0x0", time=datetime.datetime(2019, 1, 11, 14, 0))  # 33 cl

    result = self.db.MakeKegPrediction(200.0, now=datetime.datetime(2019, 1, 11, 20, 0))

    self.assertEqual(result["keg_size_cl"], 200.0)
    self.assertTrue(result["should_open_new_keg"])
    # With light consumption, estimated left should be high
    self.assertGreater(result["estimated_left_cl"], 40.0)


if __name__ == "__main__":
  unittest.main()
