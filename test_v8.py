from __future__ import annotations

import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path

import poker_engine as pe
from storage import history_to_csv, load_history, save_hand_record


def c(rank: str, suit: str) -> pe.Card:
    return rank, suit


class TestHandEvaluation(unittest.TestCase):
    def test_royal_flush(self):
        cards = [c("A", "♠"), c("K", "♠"), c("Q", "♠"), c("J", "♠"), c("T", "♠")]
        self.assertEqual(pe.evaluate_five(pe.cards_to_ints(cards)), (8, (14,)))

    def test_wheel_straight(self):
        cards = [c("A", "♠"), c("2", "♥"), c("3", "♦"), c("4", "♣"), c("5", "♠")]
        self.assertEqual(pe.evaluate_five(pe.cards_to_ints(cards)), (4, (5,)))

    def test_full_house_ordering(self):
        cards = [c("A", "♠"), c("A", "♥"), c("A", "♦"), c("K", "♠"), c("K", "♥"), c("Q", "♦"), c("2", "♣")]
        score = pe.best_hand_from_seven(pe.cards_to_ints(cards))
        self.assertEqual(score, (6, (14, 13)))

    def test_invalid_five_card_input(self):
        with self.assertRaises(ValueError):
            pe.evaluate_five([0, 1, 2, 3])

    def test_400_random_seven_card_hands_match_exhaustive_subsets(self):
        rng = random.Random(2026)
        for _ in range(400):
            hand = rng.sample(range(52), 7)
            fast = pe.best_hand_from_seven(hand)
            brute = max(pe.evaluate_five(combo) for combo in itertools.combinations(hand, 5))
            self.assertEqual(fast, brute)

    def test_1000_random_seven_card_hands_match_v7_golden_fixtures(self):
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "v7_hand_evaluation_golden.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(len(fixture["cases"]), 1000)
        for case in fixture["cases"]:
            with self.subTest(cards=case["cards"]):
                category, kickers = pe.best_hand_from_seven(case["cards"])
                self.assertEqual([category, list(kickers)], case["expected"])


class TestEquity(unittest.TestCase):
    def test_board_royal_flush_heads_up_exact_tie(self):
        board = [c("A", "♠"), c("K", "♠"), c("Q", "♠"), c("J", "♠"), c("T", "♠")]
        hero = [c("2", "♥"), c("3", "♦")]
        result = pe.calculate_equity(hero, board, 1, method="exact")
        self.assertEqual(result["strict_win"], 0)
        self.assertEqual(result["tie"], 1)
        self.assertEqual(result["strict_loss"], 0)
        self.assertEqual(result["equity"], 0.5)

    def test_exact_river_state_count(self):
        hero = [c("A", "♠"), c("K", "♥")]
        board = [c("Q", "♣"), c("J", "♦"), c("9", "♠"), c("2", "♥"), c("3", "♣")]
        result = pe.calculate_equity(hero, board, 1, method="exact")
        self.assertEqual(result["samples"], 990)
        self.assertEqual(result["method"], "exact_enumeration")

    def test_exact_turn_equity_is_within_mc_confidence_interval(self):
        hero = [c("A", "♠"), c("K", "♠")]
        board = [c("Q", "♠"), c("J", "♥"), c("2", "♣"), c("3", "♦")]
        exact = pe.calculate_equity(hero, board, 1, method="exact")
        mc = pe.calculate_equity(hero, board, 1, method="monte_carlo", samples=30000, seed=13)
        ci = mc["confidence_interval"]
        self.assertLessEqual(ci["equity_low"], exact["equity"])
        self.assertGreaterEqual(ci["equity_high"], exact["equity"])

    def test_multiway_nine_opponents_monte_carlo(self):
        result = pe.calculate_equity([c("A", "♠"), c("K", "♥")], [], 9,
                                     method="monte_carlo", samples=5000, seed=5)
        self.assertEqual(result["method"], "monte_carlo")
        self.assertEqual(result["samples"], 5000)
        self.assertAlmostEqual(result["probability_sum"], 1.0)

    def test_duplicate_cards_rejected(self):
        with self.assertRaises(ValueError):
            pe.validate_cards([c("A", "♠"), c("A", "♠")], [])

    def test_seed_reproducibility(self):
        args = ([c("A", "♠"), c("K", "♥")], [c("Q", "♦"), c("J", "♣"), c("2", "♠")], 2)
        a = pe.calculate_equity(*args, method="monte_carlo", samples=2000, seed=99)
        b = pe.calculate_equity(*args, method="monte_carlo", samples=2000, seed=99)
        self.assertEqual(a, b)

    def test_confidence_interval_bounds(self):
        result = pe.calculate_equity([c("A", "♠"), c("K", "♥")], [], 2,
                                     method="monte_carlo", samples=1000, seed=19)
        ci = result["confidence_interval"]
        self.assertGreaterEqual(ci["equity_low"], 0)
        self.assertLessEqual(ci["equity_high"], 1)
        self.assertGreaterEqual(ci["equity_high"], ci["equity_low"])


class TestReferenceProbabilities(unittest.TestCase):
    def test_aa_starting_hand_frequency(self):
        result = pe.starting_hand_reference([c("A", "♠"), c("A", "♥")])
        self.assertEqual(result["class_combinations"], 6)
        self.assertEqual(result["all_starting_combinations"], 1326)

    def test_ten_rank_alias(self):
        result = pe.starting_hand_reference([c("10", "♠"), c("A", "♠")])
        self.assertEqual(result["class_combinations"], 4)

    def test_preflop_classes_sum_to_deck(self):
        rows = pe.common_preflop_references()
        self.assertEqual(sum(row["combinations"] for row in rows), 1326)
        self.assertAlmostEqual(sum(row["probability"] for row in rows), 1.0)

    def test_nine_out_flop_to_river_exact_probability(self):
        result = pe.draw_odds_from_outs(9, "flop")
        self.assertAlmostEqual(result["exact_probability"], 1 - (38 / 47) * (37 / 46))

    def test_nine_out_turn_to_river_probability(self):
        result = pe.draw_odds_from_outs(9, "turn")
        self.assertAlmostEqual(result["exact_probability"], 9 / 46)


class TestDecisionMath(unittest.TestCase):
    def test_pot_odds_call_ev_and_positive_call(self):
        equity = 0.45
        pot, call = 100, 40
        self.assertAlmostEqual(pe.pot_odds(pot, call), 40 / 140)
        self.assertAlmostEqual(pe.call_ev(equity, pot, call), 23.0)
        self.assertEqual(pe.decision_support(equity, pot, call)["action"], "CALL")

    def test_negative_ev_maps_to_fold(self):
        self.assertEqual(pe.decision_support(0.20, 100, 40)["action"], "FOLD")

    def test_zero_call_maps_to_check(self):
        self.assertEqual(pe.decision_support(0.50, 100, 0)["action"], "CHECK")

    def test_invalid_numeric_inputs_rejected(self):
        with self.assertRaises(ValueError):
            pe.pot_odds(float("nan"), 10)
        with self.assertRaises(ValueError):
            pe.call_ev(1.2, 100, 10)


class TestStorage(unittest.TestCase):
    def test_json_history_save_load_and_csv(self):
        sample = {
            "hero_cards": ["A♠", "K♥"], "community_cards": ["Q♦", "J♣", "2♠"],
            "table_size": 6, "active_opponents": 2, "street": "Flop",
            "pot_units": 100.0, "call_units": 30.0, "quality": "Fast", "seed": 2026,
            "equity": {"equity": 0.42, "strict_win": 0.40, "tie": 0.04,
                       "strict_loss": 0.56, "method": "monte_carlo", "samples": 5000,
                       "confidence_interval": {"equity_low": 0.40, "equity_high": 0.44}},
            "decision": {"pot_odds": 0.23, "ev": 25.0, "action": "CALL"},
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hands.json"
            saved = save_hand_record(sample, path)
            loaded = load_history(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(saved["record_id"], loaded[0]["record_id"])
            csv_text = history_to_csv(loaded)
            self.assertIn("record_id", csv_text)
            self.assertIn("CALL", csv_text)
            self.assertIn("opponent_model", csv_text)
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(parsed), 1)

    def test_storage_rejects_duplicate_cards_and_invalid_equity(self):
        sample = {
            "hero_cards": ["A♠", "A♠"], "community_cards": [],
            "table_size": 6, "active_opponents": 2,
            "equity": {"equity": 0.5}, "decision": {"action": "CALL"},
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hands.json"
            with self.assertRaises(ValueError):
                save_hand_record(sample, path)
            sample["hero_cards"] = ["A♠", "K♥"]
            sample["equity"]["equity"] = float("nan")
            with self.assertRaises(ValueError):
                save_hand_record(sample, path)
            self.assertFalse(path.exists())

    def test_storage_preserves_schema_version_and_whitelisted_fields(self):
        sample = {
            "hero_cards": ["A♠", "K♥"], "community_cards": [],
            "table_size": 6, "active_opponents": 2,
            "equity": {"equity": 0.5}, "decision": {"action": "CHECK"},
            "unexpected_personal_field": "must not be stored",
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hands.json"
            saved = save_hand_record(sample, path)
            self.assertEqual(saved["schema_version"], 1)
            self.assertNotIn("unexpected_personal_field", saved)

    def test_storage_rejects_non_unit_outcome_probabilities(self):
        sample = {
            "hero_cards": ["A♠", "K♥"], "community_cards": [],
            "table_size": 6, "active_opponents": 2,
            "equity": {"equity": 0.5, "strict_win": 0.7, "tie": 0.1, "strict_loss": 0.1},
            "decision": {"action": "CALL", "pot_odds": 0.2, "ev": 1.0},
        }
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                save_hand_record(sample, Path(temp) / "hands.json")

    def test_legacy_v8_history_without_schema_version_loads(self):
        legacy = [{
            "record_id": "legacy-id",
            "hero_cards": ["A♠", "K♥"],
            "community_cards": [],
            "equity": {"equity": 0.5},
            "decision": {"action": "CHECK"},
        }]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.json"
            path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            loaded = load_history(path)
            self.assertEqual(loaded[0]["record_id"], "legacy-id")
            self.assertNotIn("schema_version", loaded[0])


class TestHardeningAndEdgeCases(unittest.TestCase):
    def test_boolean_and_out_of_range_card_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            pe.int_to_card(True)
        with self.assertRaises(ValueError):
            pe.evaluate_five([0, 1, 2, 3, 52])
        with self.assertRaises(ValueError):
            pe.best_hand_from_seven([0, 1, 2, 3, 4, 5, True])

    def test_invalid_simulation_parameters_are_rejected(self):
        hero = [c("A", "♠"), c("K", "♥")]
        with self.assertRaises(ValueError):
            pe.calculate_equity(hero, [], True)
        with self.assertRaises(ValueError):
            pe.calculate_equity(hero, [], 1, samples=1.5)
        with self.assertRaises(ValueError):
            pe.calculate_equity(hero, [], 1, exact_max_states=0)
        with self.assertRaises(ValueError):
            pe.calculate_equity(hero, [], 1, seed=True)

    def test_exact_is_explicitly_rejected_for_multiway_unknown_hands(self):
        hero = [c("A", "♠"), c("K", "♥")]
        with self.assertRaises(ValueError):
            pe.calculate_equity(hero, [], 2, method="exact")
        auto = pe.calculate_equity(hero, [], 2, method="auto", samples=200, seed=8)
        self.assertEqual(auto["method"], "monte_carlo")

    def test_known_opponent_cards_are_removed_from_remaining_deck(self):
        hero = [c("A", "♠"), c("K", "♠")]
        board = [c("Q", "♠"), c("J", "♠"), c("T", "♠"), c("2", "♣"), c("3", "♦")]
        known = [[c("2", "♦"), c("4", "♣")]]
        result = pe.calculate_equity(hero, board, 1, opponent_holes=known, method="exact")
        self.assertEqual(result["opponent_model"], "known_holes")
        self.assertEqual(result["equity"], 1.0)
        self.assertEqual(result["samples"], 1)

    def test_three_way_tie_splits_equity_equally(self):
        category, share = pe.classify_showdown((5, (14, 13, 12, 11, 9)), [
            (5, (14, 13, 12, 11, 9)), (5, (14, 13, 12, 11, 9))
        ])
        self.assertEqual(category, "tie")
        self.assertAlmostEqual(share, 1 / 3)

    def test_starting_hand_pair_and_suited_classes(self):
        pair = pe.starting_hand_reference([c("A", "♠"), c("A", "♥")])
        suited = pe.starting_hand_reference([c("A", "♠"), c("K", "♠")])
        offsuit = pe.starting_hand_reference([c("A", "♠"), c("K", "♥")])
        self.assertEqual(pair["class_combinations"], 6)
        self.assertEqual(suited["class_combinations"], 4)
        self.assertEqual(offsuit["class_combinations"], 12)

    def test_invalid_out_count_and_street_are_rejected(self):
        with self.assertRaises(ValueError):
            pe.draw_odds_from_outs(True, "flop")
        with self.assertRaises(ValueError):
            pe.draw_odds_from_outs(9, "river")

    def test_zero_and_all_outs_boundaries(self):
        zero = pe.draw_odds_from_outs(0, "flop")
        all_turn = pe.draw_odds_from_outs(46, "turn")
        self.assertEqual(zero["exact_probability"], 0.0)
        self.assertEqual(all_turn["exact_probability"], 1.0)

    def test_displayed_win_tie_loss_sum_is_exactly_one(self):
        result = pe.calculate_equity(
            [c("A", "♠"), c("K", "♥")], [], 3,
            method="monte_carlo", samples=3333, seed=1001
        )
        displayed_sum = result["strict_win"] + result["tie"] + result["strict_loss"]
        self.assertEqual(displayed_sum, 1.0)
        self.assertEqual(result["probability_sum"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
