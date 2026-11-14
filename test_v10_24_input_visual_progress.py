from __future__ import annotations

import unittest

from poker_engine import calculate_equity
from ui_helpers import parse_card_tokens, card_html, display_card_label, card_color


class TestKoreanKeyboardKAndSuitShortcuts(unittest.TestCase):
    def test_korean_physical_k_key_plus_heart_reads_king_of_hearts(self):
        for token in ("ㅋㅎ", "ㅋH", "ㅎㅋ", "Hㅋ", "KH", "HK", "kH", "hk"):
            with self.subTest(token=token):
                self.assertEqual(parse_card_tokens(token), [("K", "♥")])

    def test_korean_physical_k_key_combines_with_other_suits(self):
        cases = {
            "ㅋㅋ": ("K", "♣"),
            "ㅋㄷ": ("K", "♦"),
            "ㅋㅅ": ("K", "♠"),
            "ㅋㅎ": ("K", "♥"),
            "ㅋC": ("K", "♣"),
            "ㅋD": ("K", "♦"),
            "ㅋS": ("K", "♠"),
            "ㅋH": ("K", "♥"),
        }
        for token, expected in cases.items():
            with self.subTest(token=token):
                self.assertEqual(parse_card_tokens(token), [expected])

    def test_club_suit_shortcut_still_works_with_unambiguous_rank(self):
        for token in ("Aㅋ", "ㅋA", "C2", "2C"):
            with self.subTest(token=token):
                self.assertEqual(parse_card_tokens(token)[0][1], "♣")

    def test_ten_is_displayed_as_10_not_internal_t(self):
        self.assertEqual(display_card_label(("T", "♦")), "10♦")
        html = card_html([("T", "♦"), ("K", "♥")], "empty")
        self.assertIn("<span>10</span><b>♦</b>", html)
        self.assertIn("<span>K</span><b>♥</b>", html)

    def test_hearts_and_diamonds_are_red_in_selected_card_display(self):
        self.assertEqual(card_color("♥"), "red")
        self.assertEqual(card_color("♦"), "red")
        self.assertEqual(card_color("♠"), "black")
        self.assertEqual(card_color("♣"), "black")


class TestMonteCarloVisualizationData(unittest.TestCase):
    def test_monte_carlo_returns_cumulative_convergence_and_actual_outcome_counts(self):
        result = calculate_equity(
            [("A", "♠"), ("K", "♠")], [("Q", "♠"), ("J", "♠"), ("3", "♦")], 1,
            method="monte_carlo", samples=500, seed=2026, opponent_range="typical",
        )
        self.assertEqual(result["samples"], 500)
        self.assertEqual(sum(result["outcome_counts"].values()), 500)
        self.assertTrue(result["convergence"])
        self.assertEqual(result["convergence"][-1]["samples"], 500)
        self.assertAlmostEqual(result["convergence"][-1]["equity"], result["equity"], places=12)
        self.assertGreaterEqual(len(result["convergence"]), 50)
        self.assertLessEqual(len(result["convergence"]), 102)
        for point in result["convergence"]:
            self.assertLessEqual(point["equity_low"], point["equity"])
            self.assertGreaterEqual(point["equity_high"], point["equity"])
        half_widths = [point["half_width"] for point in result["convergence"]]
        self.assertTrue(all(later <= earlier for earlier, later in zip(half_widths, half_widths[1:])))

    def test_final_convergence_point_matches_rounded_reported_equity_exactly(self):
        result = calculate_equity(
            [("A", "♠"), ("K", "♠")], [], 1,
            method="monte_carlo", samples=350, seed=2026, opponent_range="typical",
        )
        self.assertEqual(result["convergence"][-1]["equity"], result["equity"])

    def test_seeded_monte_carlo_visual_data_is_reproducible(self):
        args = dict(
            hole_cards=[("A", "♠"), ("K", "♠")],
            community=[("Q", "♠"), ("J", "♠"), ("3", "♦")],
            num_opponents=1, method="monte_carlo", samples=300, seed=42,
            opponent_range="random",
        )
        first = calculate_equity(**args)
        second = calculate_equity(**args)
        self.assertEqual(first["outcome_counts"], second["outcome_counts"])
        self.assertEqual(first["convergence"], second["convergence"])


if __name__ == "__main__":
    unittest.main()
