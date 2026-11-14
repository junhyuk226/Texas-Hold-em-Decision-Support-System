from __future__ import annotations

import runpy
import sys
import types
import unittest
from pathlib import Path

from ui_helpers import parse_card_tokens, picker_card, SUIT_PICKER_MAP
from poker_engine import calculate_equity, decision_support
from decision_helpers import append_equity_snapshot, recommend_action

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class _State(dict):
    __getattr__ = dict.__getitem__
    def __setattr__(self, key, value):
        self[key] = value


class _Ctx:
    def __init__(self, owner): self.owner = owner
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def __getattr__(self, name): return getattr(self.owner, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self, state):
        super().__init__("streamlit")
        self.session_state = _State(state)
        self.markdown_calls = []
        self.slider_calls = []
        self.selectbox_calls = []
        self.radio_calls = []
        self.display_calls = []

    def set_page_config(self, *a, **k): pass
    def markdown(self, body, *a, **k): self.markdown_calls.append(str(body))
    def title(self, body, *a, **k): self.markdown_calls.append(str(body))
    def columns(self, spec, *a, **k):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Ctx(self) for _ in range(count)]
    def container(self, *a, **k): return _Ctx(self)
    def expander(self, *a, **k): return _Ctx(self)
    def form(self, *a, **k): return _Ctx(self)
    def slider(self, label, *a, **k):
        mn, mx = k.get("min_value"), k.get("max_value")
        self.slider_calls.append((label, mn, mx))
        if mn is not None and mx is not None and mn >= mx:
            raise ValueError("StreamlitInvalidMinMaxError: min_value and max_value must differ")
        return self._widget(k)
    def selectbox(self, label, options, *a, **k):
        self.selectbox_calls.append((label, list(options)))
        index = k.get("index", 0)
        default = None if index is None else options[index]
        return self._widget(k, default)
    def radio(self, label, options, *a, **k):
        self.radio_calls.append((label, list(options)))
        default = options[k.get("index", 0)]
        value = self._widget(k, default)
        return value if value in options else default
    def number_input(self, label, *a, **k): return self._widget(k)
    def text_input(self, label, *a, **k): return self._widget(k, "")
    def _widget(self, k, default=None):
        key = k.get("key")
        initial = k.get("value", default)
        if key is None: return initial
        if key not in self.session_state: self.session_state[key] = initial
        return self.session_state[key]
    def button(self, *a, **k):
        if a: self.display_calls.append(str(a[0]))
        return False
    def form_submit_button(self, *a, **k):
        if a: self.display_calls.append(str(a[0]))
        return False
    def download_button(self, *a, **k):
        if a: self.display_calls.append(str(a[0]))
        return False
    def plotly_chart(self, *a, **k): pass
    def __getattr__(self, name):
        def _capture(*args, **kwargs):
            if args and isinstance(args[0], (str, int, float)):
                self.display_calls.append(str(args[0]))
            return None
        return _capture


def _render(step: int, **overrides):
    state = {
        "step": step, "table_size": 2 if step == 4 else 3, "stage": "flop",
        "hero_cards": [("A", "♠"), ("K", "♠")] if step in (3, 4, 5) else [],
        "community_cards": [("Q", "♠"), ("J", "♠"), ("3", "♦")] if step in (4, 5) else [],
        "undo_stack": [], "active_opponents": 1, "opponent_style": "일반적인 플레이",
        "betting_mode": "간편", "pot_units": 100, "call_units": 30,
        "opponent_bet_units": 30, "hero_contribution_units": 0,
        "analysis": None, "saved_record_id": None, "progress_history": [],
        "progress_model_signature": None, "hand_session_id": "test-session",
        "language": "KOR",
    }
    state.update(overrides)
    fake = _FakeStreamlit(state)
    old = sys.modules.get("streamlit")
    sys.modules["streamlit"] = fake
    try:
        fake.app_namespace = runpy.run_path(str(APP_PATH), run_name=f"_i18n_{step}_{id(fake)}")
    finally:
        if old is None: sys.modules.pop("streamlit", None)
        else: sys.modules["streamlit"] = old
    return fake


class TestFlexibleCardShortcuts(unittest.TestCase):
    def test_rank_and_suit_order_are_interchangeable(self):
        expected = [("A", "♠"), ("K", "♥"), ("T", "♦"), ("J", "♣")]
        for text in ("AS KH 10D JC", "SA HK D10 CJ", "A♠ K♥ 10♦ J♣"):
            with self.subTest(text=text): self.assertEqual(parse_card_tokens(text), expected)

    def test_english_first_letter_and_korean_initial_shortcuts(self):
        expected = [("A", "♣"), ("2", "♦"), ("3", "♠"), ("4", "♥")]
        self.assertEqual(parse_card_tokens("Aㅋ ㄷ2 ㅅ3 4ㅎ"), expected)
        self.assertEqual(parse_card_tokens("CA D2 S3 H4"), expected)

    def test_all_ranks_and_suits_work_in_both_orders(self):
        suit_map = {"C": "♣", "D": "♦", "S": "♠", "H": "♥", "ㅋ": "♣", "ㄷ": "♦", "ㅅ": "♠", "ㅎ": "♥"}
        for rank in "A23456789TJQK":
            for shortcut, symbol in suit_map.items():
                for token in (rank + shortcut, shortcut + rank):
                    with self.subTest(token=token):
                        self.assertEqual(parse_card_tokens(token), [(rank, symbol)])
        for shortcut, symbol in suit_map.items():
            for token in ("10" + shortcut, shortcut + "10"):
                with self.subTest(token=token):
                    self.assertEqual(parse_card_tokens(token), [("T", symbol)])

    def test_spaced_rank_suit_pairs_work_in_both_orders(self):
        expected = [("A", "♠"), ("T", "♦"), ("J", "♥"), ("Q", "♣")]
        self.assertEqual(parse_card_tokens("A S D 10 H J Q C"), expected)
        self.assertEqual(parse_card_tokens("S A 10 D J H C Q"), expected)

    def test_duplicate_cards_are_rejected_after_normalization(self):
        with self.assertRaises(ValueError):
            parse_card_tokens("AS SA")

    def test_lowercase_english_and_suit_symbol_first_are_accepted(self):
        self.assertEqual(parse_card_tokens("as hk d10 cJ"), [("A", "♠"), ("K", "♥"), ("T", "♦"), ("J", "♣")])
        self.assertEqual(parse_card_tokens("♠A ♥K ♦10 ♣J"), [("A", "♠"), ("K", "♥"), ("T", "♦"), ("J", "♣")])

    def test_dropdown_auto_deals_after_second_selection_without_an_add_button(self):
        fake = _render(2)
        fake.session_state.hero_picker_suit = "♥ 하트"
        fake.session_state.hero_picker_rank = "K"
        fake.app_namespace["_picker_selection_changed"]("hero", 2)
        self.assertEqual(fake.session_state.hero_cards, [("K", "♥")])
        self.assertIsNone(fake.session_state.hero_picker_suit)
        self.assertIsNone(fake.session_state.hero_picker_rank)

    def test_invalid_tokens_are_rejected(self):
        for value in ("AX", "Z9", "A?", "10X"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_card_tokens(value)

    def test_english_picker_suit_labels_map_to_same_internal_cards(self):
        self.assertEqual(picker_card("A", "♣ Club"), ("A", "♣"))
        self.assertEqual(picker_card("10", "♦ Diamond"), ("T", "♦"))


class TestHeadsUpSliderBoundary(unittest.TestCase):
    def test_two_player_game_does_not_render_invalid_one_to_one_slider(self):
        fake = _render(4, table_size=2, active_opponents=1)
        self.assertEqual(fake.session_state.active_opponents, 1)
        self.assertEqual(fake.slider_calls, [])
        rendered = "\n".join(fake.markdown_calls)
        self.assertIn('data-player-count="2"', rendered)

    def test_three_player_game_still_renders_valid_opponent_slider(self):
        fake = _render(4, table_size=3, active_opponents=1)
        self.assertEqual(fake.session_state.active_opponents, 1)
        self.assertEqual(len(fake.slider_calls), 1)
        self.assertEqual(fake.slider_calls[0][1:], (1, 2))

    def test_active_opponent_slider_bounds_are_valid_for_all_table_sizes(self):
        for players in range(2, 11):
            with self.subTest(players=players):
                fake = _render(4, table_size=players, active_opponents=players - 1)
                self.assertEqual(fake.session_state.active_opponents, players - 1)
                if players == 2:
                    self.assertEqual(fake.slider_calls, [])
                else:
                    self.assertEqual(fake.slider_calls[0][1:], (1, players - 1))

    def test_heads_up_removes_a_stale_slider_value_from_a_previous_larger_table(self):
        fake = _render(4, table_size=2, active_opponents=1, active_opponents_input=6)
        self.assertEqual(fake.session_state.active_opponents, 1)
        self.assertNotIn("active_opponents_input", fake.session_state)
        self.assertEqual(fake.slider_calls, [])


class TestLanguageSwitch(unittest.TestCase):
    def test_english_mode_translates_wizard_and_suit_picker(self):
        fake = _render(2, language="EN", language_choice="EN")
        rendered = "\n".join(fake.markdown_calls)
        self.assertIn("Add your two private cards", rendered)
        self.assertIn("Poker Hand Analyzer", rendered)
        self.assertTrue(any("♣ Club" in options for _, options in fake.selectbox_calls))
        language_options = next(options for label, options in fake.radio_calls if label == "Language / 언어")
        self.assertEqual(language_options, ["EN", "KOR"])

    def test_switching_language_keeps_durable_card_and_player_state(self):
        fake = _render(2, table_size=5, hero_cards=[("A", "♠")], language="KOR", language_choice="EN")
        self.assertEqual(fake.session_state.table_size, 5)
        self.assertEqual(fake.session_state.hero_cards, [("A", "♠")])
        self.assertEqual(fake.session_state.language, "EN")

    def test_switching_back_to_korean_keeps_durable_state(self):
        fake = _render(2, table_size=7, hero_cards=[("K", "♥")], language="EN", language_choice="KOR")
        self.assertEqual(fake.session_state.table_size, 7)
        self.assertEqual(fake.session_state.hero_cards, [("K", "♥")])
        self.assertEqual(fake.session_state.language, "KOR")

    def test_all_six_wizard_screens_render_in_english(self):
        for step in range(6):
            with self.subTest(step=step):
                fake = _render(step, language="EN", language_choice="EN")
                combined = "\n".join(fake.markdown_calls + fake.display_calls)
                # The language toggle is intentionally bilingual; Korean consonants are documented input shortcuts.
                combined = combined.replace("ㅋ", "").replace("ㄷ", "").replace("ㅅ", "").replace("ㅎ", "")
                self.assertNotRegex(combined, r"[가-힣]")
                self.assertEqual(fake.session_state.language, "EN")

    def test_english_results_screen_localizes_action_guidance_and_chart(self):
        hero = [("A", "♠"), ("K", "♠")]
        board = [("Q", "♠"), ("J", "♠"), ("3", "♦")]
        result = calculate_equity(hero, board, 1, method="monte_carlo", samples=150, seed=2026, opponent_range="typical")
        decision = decision_support(result["equity"], 100, 30)
        recommendation = recommend_action(result["equity"], 100, 30, 1)
        decision["recommendation"] = recommendation
        history = append_equity_snapshot([], stage="flop", board_count=3, equity=result["equity"],
                                         pot_odds=decision["pot_odds"], pot=100, call=30, action=recommendation["action"])
        analysis = {"hero_cards": hero, "community_cards": board, "table_size": 2, "active_opponents": 1,
                    "stage": "flop", "pot_units": 100, "call_units": 30, "equity": result,
                    "decision": decision, "equity_history": history}
        fake = _render(5, language="EN", language_choice="EN", analysis=analysis,
                       hero_cards=hero, community_cards=board, table_size=2, active_opponents=1,
                       progress_history=history)
        self.assertTrue(fake.display_calls)
        combined = "\n".join(fake.markdown_calls + fake.display_calls)
        self.assertIn("Why:", combined)
        self.assertTrue("Suggested" in combined or "points" in combined)
        # Korean consonant shortcuts remain intentionally documented in the keyboard hint.
        stripped = combined.replace("ㅋ", "").replace("ㄷ", "").replace("ㅅ", "").replace("ㅎ", "")
        self.assertNotRegex(stripped, r"[가-힣]")


if __name__ == "__main__":
    unittest.main()
