from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser

from ui_helpers import poker_table_html, table_seat_positions


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scene_attrs = None
        self.opponents = []
        self.hero_count = 0
        self.count_badges = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if "table-scene" in classes:
            self.scene_attrs = attrs
        if "opponent" in classes and "seat" in classes:
            self.opponents.append(attrs)
        if "you" in classes and "seat" in classes:
            self.hero_count += 1

    def handle_data(self, data):
        if "전체 " in data and "명" in data:
            self.count_badges.append(data.strip())


class TestDynamicPokerTableLayout(unittest.TestCase):
    def test_every_supported_table_size_renders_exactly_one_seat_per_player(self):
        for players in range(2, 11):
            with self.subTest(players=players):
                html = poker_table_html(players, [], [], board_slots=5, subtitle="테이블 테스트")
                parser = TableParser()
                parser.feed(html)
                self.assertEqual(parser.scene_attrs.get("data-player-count"), str(players))
                self.assertEqual(parser.scene_attrs.get("data-opponent-count"), str(players - 1))
                self.assertEqual(len(parser.opponents), players - 1)
                self.assertEqual(parser.hero_count, 1)
                self.assertEqual(len(parser.opponents) + parser.hero_count, players)
                self.assertIn(f"총 {players}명", parser.scene_attrs.get("aria-label", ""))
                self.assertEqual(parser.count_badges, [f"전체 {players}명"])

    def test_opponent_positions_are_unique_and_exclude_hero_seat(self):
        for players in range(2, 11):
            with self.subTest(players=players):
                positions = table_seat_positions(players)
                self.assertEqual(len(positions), players - 1)
                self.assertEqual(len(set(positions)), players - 1)
                for left, top in positions:
                    self.assertGreaterEqual(left, 12)
                    self.assertLessEqual(left, 88)
                    self.assertGreaterEqual(top, 12)
                    self.assertLessEqual(top, 40)
                    self.assertNotEqual((left, top), (50.0, 91.0))

    def test_mobile_opponent_seats_do_not_overlap_for_all_table_sizes(self):
        # Mirrors the responsive CSS dimensions in app.py at a 390 x 330 table.
        widths = {8: 44, 9: 38, 10: 34}
        heights = {8: 42, 9: 40, 10: 38}
        for players in range(2, 11):
            width = widths.get(players, 48)
            height = heights.get(players, 44)
            positions = table_seat_positions(players)
            pixel_positions = [(x * 3.9, y * 3.3) for x, y in positions]
            for i, (x1, y1) in enumerate(pixel_positions):
                for x2, y2 in pixel_positions[i + 1:]:
                    separated_x = abs(x1 - x2) >= width
                    separated_y = abs(y1 - y2) >= height
                    self.assertTrue(
                        separated_x or separated_y,
                        f"{players} players: opponent seats overlap at {(x1, y1)} and {(x2, y2)}",
                    )

    def test_positions_and_visible_count_change_for_reported_problem_cases(self):
        expected = {}
        for players in (3, 5, 9):
            html = poker_table_html(players, [], [], board_slots=5)
            parser = TableParser()
            parser.feed(html)
            expected[players] = (
                parser.scene_attrs["data-player-count"],
                len(parser.opponents),
                tuple(attrs["style"] for attrs in parser.opponents),
            )
        self.assertEqual(expected[3][1], 2)
        self.assertEqual(expected[5][1], 4)
        self.assertEqual(expected[9][1], 8)
        self.assertEqual(len({expected[n][2] for n in expected}), 3)

    def test_invalid_player_counts_rejected(self):
        for players in (1, 11, 2.5, True, "3"):
            with self.subTest(players=players), self.assertRaises(ValueError):
                table_seat_positions(players)

    def test_subtitle_is_html_escaped(self):
        html = poker_table_html(3, [], [], board_slots=5, subtitle='<script>alert(1)</script>')
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_invalid_board_slot_count_rejected(self):
        for slots in (-1, 6, True, 2.5):
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                poker_table_html(3, [], [], board_slots=slots)


if __name__ == "__main__":
    unittest.main()
