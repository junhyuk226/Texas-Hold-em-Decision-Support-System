from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from poker_engine import OPPONENT_RANGE_PRESETS, calculate_equity
from storage import load_history, save_hand_record
from ui_helpers import (
    is_five_multiple, make_card_snapshot, parse_card_tokens, picker_card, remove_card,
    restore_card_snapshot, RANK_PICKER_OPTIONS, SUIT_PICKER_OPTIONS
)


class TestCompactCardInput(unittest.TestCase):
    def test_compact_alphanumeric_and_symbol_input(self):
        self.assertEqual(parse_card_tokens("AS KH 10D QC"), [
            ("A", "♠"), ("K", "♥"), ("T", "♦"), ("Q", "♣")
        ])
        self.assertEqual(parse_card_tokens("A♠, K♥"), [("A", "♠"), ("K", "♥")])

    def test_duplicate_cards_in_one_entry_rejected(self):
        with self.assertRaises(ValueError):
            parse_card_tokens("AS AS")

    def test_invalid_card_text_rejected(self):
        for value in ("1S", "AX", "A", "ZZ"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_card_tokens(value)

    def test_remove_only_one_selected_card(self):
        cards = [("A", "♠"), ("K", "♥"), ("Q", "♦")]
        self.assertEqual(remove_card(cards, 1), [("A", "♠"), ("Q", "♦")])
        self.assertEqual(len(cards), 3)  # Pure helper does not mutate caller input.

    def test_invalid_remove_index_rejected(self):
        with self.assertRaises(IndexError):
            remove_card([("A", "♠")], 1)

    def test_undo_restores_last_card_removal_without_aliasing(self):
        hero = [("A", "♠"), ("K", "♥")]
        board = [("Q", "♦")]
        stack = [make_card_snapshot(hero, board)]
        hero = remove_card(hero, 1)
        restored_hero, restored_board = restore_card_snapshot(stack)
        self.assertEqual(restored_hero, [("A", "♠"), ("K", "♥")])
        self.assertEqual(restored_board, [("Q", "♦")])
        self.assertEqual(stack, [])
        self.assertIsNone(restore_card_snapshot(stack))


class TestTwoBoxCardPicker(unittest.TestCase):
    def test_picker_rank_order_is_easy_to_scan(self):
        self.assertEqual(RANK_PICKER_OPTIONS, ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"))

    def test_picker_suits_include_all_four_suits(self):
        self.assertEqual(len(SUIT_PICKER_OPTIONS), 4)
        self.assertEqual(set(SUIT_PICKER_OPTIONS), {"♠ 스페이드", "♥ 하트", "♦ 다이아", "♣ 클럽"})

    def test_two_box_picker_builds_canonical_card(self):
        self.assertEqual(picker_card("A", "♠ 스페이드"), ("A", "♠"))
        self.assertEqual(picker_card("10", "♦ 다이아"), ("T", "♦"))
        self.assertEqual(picker_card("J", "♥ 하트"), ("J", "♥"))

    def test_picker_rejects_invalid_option(self):
        with self.assertRaises(ValueError):
            picker_card("1", "♠ 스페이드")
        with self.assertRaises(ValueError):
            picker_card("A", "star")


class TestOpponentPresets(unittest.TestCase):
    def setUp(self):
        self.hero = [("A", "♠"), ("K", "♠")]
        self.board = [("Q", "♠"), ("J", "♠"), ("3", "♦")]

    def test_four_beginner_friendly_presets_exist(self):
        self.assertEqual(set(OPPONENT_RANGE_PRESETS), {"random", "strong", "typical", "loose"})

    def test_each_preset_is_reproducible_and_probabilities_sum_to_one(self):
        for preset in OPPONENT_RANGE_PRESETS:
            with self.subTest(preset=preset):
                first = calculate_equity(self.hero, self.board, 2, method="monte_carlo", samples=1200, seed=77, opponent_range=preset)
                second = calculate_equity(self.hero, self.board, 2, method="monte_carlo", samples=1200, seed=77, opponent_range=preset)
                self.assertEqual(first, second)
                self.assertAlmostEqual(first["probability_sum"], 1.0)
                self.assertEqual(first["samples"], 1200)

    def test_weighted_presets_are_labeled_as_assumptions(self):
        result = calculate_equity(self.hero, self.board, 2, method="monte_carlo", samples=1000, seed=77, opponent_range="typical")
        self.assertIn("user_weighted_ranges:typical", result["opponent_model"])
        self.assertIn("observed or inferred", result["model_note"])

    def test_exact_enumeration_rejected_for_weighted_range(self):
        with self.assertRaises(ValueError):
            calculate_equity(self.hero, self.board, 2, method="exact", opponent_range="typical")

    def test_invalid_range_name_rejected(self):
        with self.assertRaises(ValueError):
            calculate_equity(self.hero, self.board, 2, method="monte_carlo", samples=100, opponent_range="magic")

    def test_weighted_range_supports_nine_opponents(self):
        result = calculate_equity(self.hero, self.board, 9, method="monte_carlo", samples=800, seed=9, opponent_range="loose")
        self.assertEqual(result["samples"], 800)
        self.assertAlmostEqual(result["probability_sum"], 1.0)


class TestIntegerPointInputs(unittest.TestCase):
    def test_five_point_steps(self):
        for value in (0, 5, 10, 150):
            self.assertTrue(is_five_multiple(value))
        for value in (1, 3, 12, -5, 5.0, True):
            self.assertFalse(is_five_multiple(value))

    def test_storage_normalizes_integral_legacy_floats(self):
        record = {
            "hero_cards": ["A♠", "K♠"],
            "community_cards": ["Q♠", "J♠", "3♦"],
            "table_size": 6,
            "active_opponents": 2,
            "street": "flop",
            "pot_units": 100.0,
            "call_units": 30.0,
            "equity": {"equity": 0.5, "strict_win": 0.4, "tie": 0.2, "strict_loss": 0.4},
            "decision": {"action": "CALL", "pot_odds": 0.23, "ev": 20.0},
            "opponent_range": "typical",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hands.json"
            saved = save_hand_record(record, path)
            loaded = load_history(path)[0]
            self.assertEqual(saved["pot_units"], 100)
            self.assertEqual(saved["call_units"], 30)
            self.assertEqual(loaded["opponent_range"], "typical")

    def test_storage_rejects_non_five_increment(self):
        record = {
            "hero_cards": ["A♠", "K♠"],
            "community_cards": [],
            "table_size": 6,
            "active_opponents": 2,
            "street": "preflop",
            "pot_units": 101,
            "call_units": 30,
            "equity": {"equity": 0.5},
            "decision": {"action": "CALL"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_hand_record(record, Path(tmp) / "hands.json")


if __name__ == "__main__":
    unittest.main()
