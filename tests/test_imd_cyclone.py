from __future__ import annotations

import unittest

from scripts.alerts.imd_cyclone import parse_bulletins


class ImdCycloneTests(unittest.TestCase):
    def test_no_cyclone_bulletin_is_recognized(self):
        html = """
        <a href="/uploads/archive/1/1_example_No_Cyclone.pdf">National Bulletin</a>
        <a href="/uploads/archive/2/outlook.pdf">Tropical Weather Outlook</a>
        """
        result = parse_bulletins(html)

        self.assertEqual(result["status"], "NO_ACTIVE_CYCLONE_BULLETIN")
        self.assertEqual(len(result["bulletins"]), 2)

    def test_active_national_bulletin_takes_priority(self):
        html = '<a href="/uploads/current.pdf">National Bulletin</a>'
        result = parse_bulletins(html)

        self.assertEqual(result["status"], "ACTIVE_CYCLONE_BULLETIN")


if __name__ == "__main__":
    unittest.main()
