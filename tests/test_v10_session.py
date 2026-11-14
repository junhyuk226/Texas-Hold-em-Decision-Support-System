from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from storage import load_history, save_hand_record, history_to_csv
from decision_helpers import append_equity_snapshot, build_progress_chart_rows, next_stage, progress_model_signature, progress_signature_changed, recommend_action, truncate_progress_history


class TestContinuousHandProgression(unittest.TestCase):
    def test_street_order_and_river_end(self):
        self.assertEqual(next_stage("preflop"), "flop")
        self.assertEqual(next_stage("flop"), "turn")
        self.assertEqual(next_stage("turn"), "river")
        self.assertIsNone(next_stage("river"))

    def test_invalid_stage_rejected(self):
        with self.assertRaises(ValueError):
            next_stage("new-hand")

    def test_progress_points_append_on_new_street(self):
        first = append_equity_snapshot(
            [], stage="flop", board_count=3, equity=0.55, pot_odds=0.20,
            pot=100, call=25, action="CALL"
        )
        second = append_equity_snapshot(
            first, stage="turn", board_count=4, equity=0.61, pot_odds=0.20,
            pot=100, call=25, action="CALL"
        )
        self.assertEqual(len(second), 2)
        self.assertEqual(second[-1]["stage"], "turn")
        self.assertAlmostEqual(second[-1]["equity"], 0.61)

    def test_progress_points_append_when_bet_changes_equity_same(self):
        first = append_equity_snapshot(
            [], stage="flop", board_count=3, equity=0.55, pot_odds=0.20,
            pot=100, call=25, action="CALL"
        )
        second = append_equity_snapshot(
            first, stage="flop", board_count=3, equity=0.55, pot_odds=0.30,
            pot=100, call=45, action="FOLD"
        )
        self.assertEqual(len(second), 2)
        self.assertEqual(second[0]["equity"], second[1]["equity"])
        self.assertNotEqual(second[0]["pot_odds"], second[1]["pot_odds"])

    def test_exact_duplicate_progress_point_is_deduplicated(self):
        args = dict(stage="flop", board_count=3, equity=0.55, pot_odds=0.20,
                    pot=100, call=25, action="CALL")
        first = append_equity_snapshot([], **args)
        second = append_equity_snapshot(first, **args)
        self.assertEqual(len(second), 1)


class TestProgressModelSignature(unittest.TestCase):
    def test_same_table_and_opponent_assumptions_keep_one_history_series(self):
        first = progress_model_signature(6, 2, "typical")
        second = progress_model_signature(6, 2, "typical")
        self.assertFalse(progress_signature_changed(first, second))

    def test_changing_table_or_opponent_assumption_starts_new_history_series(self):
        first = progress_model_signature(6, 2, "typical")
        for current in (
            progress_model_signature(6, 3, "typical"),
            progress_model_signature(6, 2, "strong"),
            progress_model_signature(7, 2, "typical"),
        ):
            with self.subTest(current=current):
                self.assertTrue(progress_signature_changed(first, current))

    def test_initial_signature_does_not_count_as_change(self):
        current = progress_model_signature(2, 1, "random")
        self.assertFalse(progress_signature_changed(None, current))

    def test_invalid_assumption_signature_rejected(self):
        for args in ((1, 1, "random"), (6, 6, "random"), (6, 1, "unknown")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                progress_model_signature(*args)


class TestProgressChartData(unittest.TestCase):
    def test_chart_data_formats_equity_and_pot_odds_separately(self):
        history = [{
            "event": "플랍", "stage": "flop", "board_count": 3,
            "equity": 0.6142, "pot_odds": 0.2307, "pot": 100,
            "call": 30, "action": "CALL",
        }]
        rows = build_progress_chart_rows(history)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stage"], "플랍")
        self.assertEqual(rows[0]["equity_pct"], 61.42)
        self.assertEqual(rows[0]["pot_odds_pct"], 23.07)
        self.assertEqual(rows[0]["pot_units"], 100)
        self.assertEqual(rows[0]["call_units"], 30)


    def test_progress_snapshots_store_sampling_bounds_for_each_street(self):
        first = append_equity_snapshot(
            [], stage="flop", board_count=3, equity=0.55, pot_odds=0.20,
            pot=100, call=25, action="CALL", sampling_half_width=0.0086, samples=25_000
        )
        second = append_equity_snapshot(
            first, stage="turn", board_count=4, equity=0.61, pot_odds=0.20,
            pot=100, call=25, action="CALL", sampling_half_width=0.0086, samples=25_000
        )
        rows = build_progress_chart_rows(second)
        self.assertAlmostEqual(rows[0]["equity_low_pct"], 54.14, places=2)
        self.assertAlmostEqual(rows[0]["equity_high_pct"], 55.86, places=2)
        self.assertEqual(rows[0]["samples"], 25_000)
        self.assertEqual(rows[1]["equity_pct"], 61.0)

    def test_legacy_progress_without_sampling_bounds_remains_displayable(self):
        rows = build_progress_chart_rows([{
            "event": "플랍", "stage": "flop", "board_count": 3,
            "equity": 0.55, "pot_odds": 0.20, "pot": 100, "call": 25, "action": "CALL",
        }])
        self.assertEqual(rows[0]["equity_low_pct"], rows[0]["equity_pct"])
        self.assertEqual(rows[0]["equity_high_pct"], rows[0]["equity_pct"])
        self.assertEqual(rows[0]["samples"], 0)

    def test_chart_data_rejects_invalid_probability(self):
        with self.assertRaises(ValueError):
            build_progress_chart_rows([{
                "event": "플랍 · 1", "stage": "flop", "equity": 1.2,
                "pot_odds": 0.2, "pot": 100, "call": 20,
            }])

    def test_chart_data_rejects_unknown_stage(self):
        with self.assertRaises(ValueError):
            build_progress_chart_rows([{
                "event": "bad", "stage": "bad", "equity": 0.5,
                "pot_odds": 0.2, "pot": 100, "call": 20,
            }])


class TestSimpleActionRecommendation(unittest.TestCase):
    def test_no_bet_and_not_strong_enough_recommends_check(self):
        result = recommend_action(0.50, 100, 0, 1)
        self.assertEqual(result["action"], "CHECK")
        self.assertEqual(result["total_additional_units"], 0)

    def test_no_bet_and_high_equity_recommends_bet_not_raise(self):
        result = recommend_action(0.80, 100, 0, 1)
        self.assertEqual(result["action"], "BET")
        self.assertEqual(result["amount"], 50)
        self.assertEqual(result["amount"] % 5, 0)

    def test_facing_bet_positive_ev_recommends_call_when_not_raise_strength(self):
        result = recommend_action(0.48, 100, 30, 2)
        self.assertEqual(result["action"], "CALL")
        self.assertEqual(result["total_additional_units"], 30)

    def test_facing_bet_negative_ev_recommends_fold(self):
        result = recommend_action(0.20, 100, 30, 2)
        self.assertEqual(result["action"], "FOLD")

    def test_high_equity_edge_recommends_raise_and_explains_amount(self):
        result = recommend_action(0.80, 100, 30, 1)
        self.assertEqual(result["action"], "RAISE")
        self.assertEqual(result["call_units"], 30)
        self.assertEqual(result["extra_raise_units"], 50)
        self.assertEqual(result["total_additional_units"], 80)
        self.assertEqual(result["extra_raise_units"] % 5, 0)
        self.assertIn("폴드", result["model_limit"])


    def test_saved_hand_keeps_equity_history_and_recommendation(self):
        record = {
            "hero_cards": ["A♠", "K♠"],
            "community_cards": ["Q♠", "J♠", "3♦"],
            "table_size": 6,
            "active_opponents": 2,
            "street": "flop",
            "pot_units": 100,
            "call_units": 30,
            "equity": {"equity": 0.7, "strict_win": 0.65, "tie": 0.1, "strict_loss": 0.25},
            "decision": {
                "action": "CALL", "pot_odds": 0.23, "ev": 40.0,
                "recommendation": {
                    "action": "RAISE", "amount": 50, "call_units": 30,
                    "extra_raise_units": 50, "total_additional_units": 80,
                    "reason": "test", "sizing_note": "heuristic", "model_limit": "not GTO"
                }
            },
            "equity_history": [{"event": "플랍", "stage": "flop", "board_count": 3, "equity": 0.7, "pot_odds": 0.23, "pot": 100, "call": 30, "action": "RAISE"}],
            "hand_session_id": "session-test",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hands.json"
            saved = save_hand_record(record, path)
            loaded = load_history(path)[0]
            self.assertEqual(loaded["hand_session_id"], "session-test")
            self.assertEqual(len(loaded["equity_history"]), 1)
            self.assertEqual(loaded["decision"]["recommendation"]["action"], "RAISE")
            csv_text = history_to_csv([saved])
            self.assertIn("recommended_action", csv_text.splitlines()[0])
            self.assertIn("RAISE", csv_text)

    def test_invalid_recommendation_input_rejected(self):
        with self.assertRaises(ValueError):
            recommend_action(0.5, 100, 3, 1)
        with self.assertRaises(ValueError):
            recommend_action(0.5, 100, 0, 0)


if __name__ == "__main__":
    unittest.main()


class TestBoardEditKeepsValidHistory(unittest.TestCase):
    def test_removing_turn_card_keeps_preflop_and_flop_only(self):
        history = [
            {"event": "게임 시작 전", "stage": "preflop", "board_count": 0, "equity": 0.5, "pot_odds": 0.1, "pot": 100, "call": 10, "action": "CHECK"},
            {"event": "플랍", "stage": "flop", "board_count": 3, "equity": 0.6, "pot_odds": 0.2, "pot": 100, "call": 25, "action": "CALL"},
            {"event": "턴", "stage": "turn", "board_count": 4, "equity": 0.7, "pot_odds": 0.3, "pot": 150, "call": 65, "action": "FOLD"},
        ]
        trimmed = truncate_progress_history(history, 3)
        self.assertEqual([item["stage"] for item in trimmed], ["preflop", "flop"])
        self.assertEqual(trimmed[-1]["event"], "플랍")

    def test_removing_river_card_keeps_turn_and_rebuilds_stage_labels(self):
        history = [
            {"event": "플랍", "stage": "flop", "stage_update": 1, "board_count": 3, "equity": 0.6, "pot_odds": 0.2, "pot": 100, "call": 25, "action": "CALL"},
            {"event": "턴", "stage": "turn", "stage_update": 1, "board_count": 4, "equity": 0.7, "pot_odds": 0.3, "pot": 150, "call": 65, "action": "CALL"},
            {"event": "리버", "stage": "river", "stage_update": 1, "board_count": 5, "equity": 0.8, "pot_odds": 0.35, "pot": 200, "call": 100, "action": "RAISE"},
        ]
        trimmed = truncate_progress_history(history, 4)
        self.assertEqual([item["stage"] for item in trimmed], ["flop", "turn"])
        self.assertEqual(trimmed[-1]["event"], "턴")

    def test_same_stage_reanalysis_has_bet_update_label_not_global_count(self):
        first = append_equity_snapshot([], stage="flop", board_count=3, equity=0.55, pot_odds=0.2, pot=100, call=25, action="CALL")
        second = append_equity_snapshot(first, stage="flop", board_count=3, equity=0.55, pot_odds=0.3, pot=100, call=45, action="FOLD")
        third = append_equity_snapshot(second, stage="turn", board_count=4, equity=0.61, pot_odds=0.3, pot=100, call=45, action="CALL")
        rows = build_progress_chart_rows(third)
        self.assertEqual(rows[0]["event"], "플랍")
        self.assertEqual(rows[1]["event"], "플랍 · 베팅 변경 1")
        self.assertEqual(rows[2]["event"], "턴")
        self.assertEqual(rows[2]["stage_update"], 1)
