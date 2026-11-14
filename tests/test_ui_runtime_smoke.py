from __future__ import annotations

import runpy
import sys
import types
import unittest
from pathlib import Path

from poker_engine import calculate_equity, decision_support
from decision_helpers import recommend_action

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class _State(dict):
    __getattr__ = dict.__getitem__

    def __setattr__(self, key, value):
        self[key] = value


class _Context:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __getattr__(self, name):
        return getattr(self.owner, name)


class _FakeStreamlit(types.ModuleType):
    def __init__(self, state):
        super().__init__("streamlit")
        self.session_state = _State(state)
        self.context = types.SimpleNamespace(theme=types.SimpleNamespace(type="light"))
        self.markdown_calls = []
        self.plotly_calls = []

    def set_page_config(self, *args, **kwargs):
        return None

    def markdown(self, body, *args, **kwargs):
        self.markdown_calls.append(str(body))

    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Context(self) for _ in range(count)]

    def container(self, *args, **kwargs):
        return _Context(self)

    def expander(self, *args, **kwargs):
        return _Context(self)

    def form(self, *args, **kwargs):
        return _Context(self)

    def slider(self, label, *args, **kwargs):
        return self._widget_value(kwargs)

    def selectbox(self, label, options, *args, **kwargs):
        value = self._widget_value(kwargs, default=options[0])
        return value if value in options else options[0]

    def radio(self, label, options, *args, **kwargs):
        default = options[kwargs.get("index", 0)]
        value = self._widget_value(kwargs, default=default)
        return value if value in options else default

    def number_input(self, label, *args, **kwargs):
        return self._widget_value(kwargs)

    def text_input(self, label, *args, **kwargs):
        return self._widget_value(kwargs, default="")

    def _widget_value(self, kwargs, default=None):
        key = kwargs.get("key")
        initial = kwargs.get("value", default)
        if key is None:
            return initial
        if key not in self.session_state:
            self.session_state[key] = initial
        return self.session_state[key]

    def button(self, *args, **kwargs):
        return False

    def form_submit_button(self, *args, **kwargs):
        return False

    def download_button(self, *args, **kwargs):
        return False

    def plotly_chart(self, figure, *args, **kwargs):
        self.plotly_calls.append(figure)

    def __getattr__(self, name):
        # Most display-only Streamlit functions are no-ops for this render smoke test.
        return lambda *args, **kwargs: None


def _result_record():
    hero = [("A", "♠"), ("K", "♠")]
    board = [("Q", "♠"), ("J", "♠"), ("3", "♦")]
    equity = calculate_equity(hero, board, 1, method="monte_carlo", samples=150, seed=2026, opponent_range="typical")
    decision = decision_support(equity["equity"], 100, 30)
    decision["recommendation"] = recommend_action(equity["equity"], 100, 30, 1)
    ci = equity["confidence_interval"]
    history = [{
        "event": "플랍", "stage": "flop", "stage_update": 1, "board_count": 3,
        "equity": equity["equity"], "equity_low": ci["equity_low"], "equity_high": ci["equity_high"],
        "sampling_half_width": ci["half_width"], "samples": equity["samples"],
        "pot_odds": decision["pot_odds"], "pot": 100, "call": 30,
        "action": decision["recommendation"]["action"],
    }]
    equity["convergence"] = [
        {"samples": 1, "equity": 0.0, "equity_low": 0.0, "equity_high": 1.0},
        {"samples": 75, "equity": equity["equity"] * 0.92, "equity_low": max(0.0, equity["equity"] * 0.92 - 0.16), "equity_high": min(1.0, equity["equity"] * 0.92 + 0.16)},
        {"samples": 150, "equity": equity["equity"], "equity_low": max(0.0, equity["equity"] - 0.12), "equity_high": min(1.0, equity["equity"] + 0.12)},
    ]
    equity["outcome_counts"] = {"strict_win": 90, "tie": 10, "strict_loss": 50}
    return {
        "hero_cards": hero,
        "community_cards": board,
        "table_size": 3,
        "active_opponents": 1,
        "stage": "flop",
        "pot_units": 100,
        "call_units": 30,
        "opponent_style": "일반적인 플레이",
        "betting_mode": "간편",
        "pot": 100,
        "call": 30,
        "equity": equity,
        "decision": decision,
        "equity_history": history,
        "hand_session_id": "runtime-smoke-session",
    }


class TestStreamlitScreenRenderSmoke(unittest.TestCase):
    def _render(self, step, **overrides):
        theme_type = overrides.pop("_theme_type", "light")
        state = {
            "step": step,
            "table_size": 3,
            "stage": "flop",
            "hero_cards": [("A", "♠"), ("K", "♠")] if step in (3, 4, 5) else [],
            "community_cards": [("Q", "♠"), ("J", "♠"), ("3", "♦")] if step in (4, 5) else [],
            "active_opponents": 1,
            "opponent_style": "일반적인 플레이",
            "betting_mode": "간편",
            "pot_units": 100,
            "call_units": 30,
            "opponent_bet_units": 30,
            "hero_contribution_units": 0,
            "undo_stack": [],
            "analysis": _result_record() if step == 5 else None,
            "saved_record_id": None,
            "progress_history": _result_record()["equity_history"] if step == 5 else [],
            "hand_session_id": "runtime-smoke-session",
        }
        state.update(overrides)
        fake = _FakeStreamlit(state)
        fake.context.theme.type = theme_type
        previous = sys.modules.get("streamlit")
        sys.modules["streamlit"] = fake
        try:
            runpy.run_path(str(APP_PATH), run_name=f"_poker_screen_smoke_{step}_{id(fake)}")
        finally:
            if previous is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = previous
        return fake

    def test_all_six_wizard_screens_render_without_exceptions(self):
        for step in range(6):
            with self.subTest(step=step):
                fake = self._render(step)
                rendered = "\n".join(fake.markdown_calls)
                self.assertIn('data-player-count="3"', rendered)

    def test_participant_slider_values_2_3_5_9_are_passed_to_table_html(self):
        for players in (2, 3, 5, 9):
            with self.subTest(players=players):
                fake = self._render(0, table_size_slider_input=players)
                rendered = "\n".join(fake.markdown_calls)
                self.assertIn(f'data-player-count="{players}"', rendered)
                self.assertEqual(fake.session_state.table_size, players)

    def test_player_slider_shows_numeric_ticks_from_two_through_ten(self):
        fake = self._render(0, table_size_slider_input=5)
        rendered = "\n".join(fake.markdown_calls)
        for count in range(2, 11):
            self.assertIn(f"<span>{count}</span>", rendered)
        self.assertIn("참가자 5명", rendered)

    def test_game_info_screen_shows_one_fixed_balanced_opponent_model(self):
        fake = self._render(4)
        rendered = "\n".join(fake.markdown_calls)
        self.assertIn("중간 범위 기본 모델", rendered)
        self.assertIn("MONTE CARLO · 단일 기본 모델", rendered)
        self.assertNotIn("강한 카드 위주", rendered)
        self.assertNotIn("넓은 카드 범위", rendered)
        self.assertNotIn("완전 무작위", rendered)

    def test_fixed_opponent_model_panel_is_translated_in_english(self):
        fake = self._render(4, language="EN")
        rendered = "\n".join(fake.markdown_calls)
        self.assertIn("Balanced baseline", rendered)
        self.assertIn("MONTE CARLO · WEIGHTED BASELINE", rendered)
        self.assertIn("Opponent model", rendered)

    def test_result_screen_constructs_a_plotly_figure(self):
        fake = self._render(5)
        self.assertGreaterEqual(len(fake.plotly_calls), 4)
        figure = fake.plotly_calls[0]
        self.assertEqual(len(figure.data), 4)
        self.assertEqual(figure.data[1].fill, "tonexty")
        self.assertLess(figure.data[0].y[0], figure.data[2].y[0])
        self.assertGreater(figure.data[1].y[0], figure.data[2].y[0])
        self.assertEqual(figure.data[2].name, "내 승산")
        self.assertEqual(figure.data[3].name, "콜에 필요한 승산")

    def test_dark_theme_uses_dark_css_and_dark_plotly_figures(self):
        fake = self._render(5, _theme_type="dark")
        rendered_css = "\n".join(fake.markdown_calls)
        self.assertNotIn("color-scheme: light", rendered_css)
        self.assertNotIn("color-scheme: dark", rendered_css)
        self.assertIn("Let Streamlit own native control color-scheme", rendered_css)
        self.assertIn("var(--background-color", rendered_css)
        self.assertIn("var(--secondary-background-color", rendered_css)
        self.assertGreaterEqual(len(fake.plotly_calls), 4)
        for figure in fake.plotly_calls:
            self.assertEqual(figure.layout.plot_bgcolor, "#1b2229")
            self.assertEqual(figure.layout.paper_bgcolor, "rgba(0,0,0,0)")
            self.assertEqual(figure.layout.font.color, "#edf3ef")

    def test_outcome_visual_is_a_bar_chart_not_a_donut(self):
        fake = self._render(5)
        outcome_figure = fake.plotly_calls[3]
        self.assertEqual(outcome_figure.data[0].type, "bar")
        self.assertEqual(outcome_figure.data[0].orientation, "h")
        self.assertEqual(list(outcome_figure.data[0].y), ["승리", "무승부", "패배"])

    def test_sampling_error_is_prominently_explained_on_results_screen(self):
        fake = self._render(5)
        rendered = "\n".join(fake.markdown_calls)
        self.assertIn("보수적 95% 표본 오차 한계", rendered)
        self.assertIn("±", rendered)
        self.assertIn("상대 가정 자체가 실제와 다를 때의 오차는 포함하지 않습니다", rendered)
        self.assertEqual(len(fake.plotly_calls[1].data), 2)  # pot + additional call
        convergence_figure = fake.plotly_calls[2]
        self.assertEqual(len(convergence_figure.data), 4)  # lower, upper band, running estimate, final marker
        self.assertEqual(convergence_figure.data[2].name, "누적 승산")
        self.assertEqual(convergence_figure.data[1].fill, "tonexty")
        self.assertEqual(convergence_figure.data[3].showlegend, False)
        self.assertLess(convergence_figure.layout.yaxis.range[0], convergence_figure.layout.yaxis.range[1])
        self.assertLess(convergence_figure.layout.yaxis.range[1] - convergence_figure.layout.yaxis.range[0], 100)
        self.assertEqual(fake.plotly_calls[3].data[0].type, "bar")

    def test_editing_private_cards_resets_old_equity_history_but_new_board_cards_keep_it(self):
        base_state = {
            "step": 0,
            "table_size": 3,
            "stage": "flop",
            "hero_cards": [],
            "community_cards": [],
            "undo_stack": [],
            "progress_history": [{"event": "old hand", "stage": "flop", "board_count": 3,
                                  "equity": 0.5, "pot_odds": 0.2, "pot": 100, "call": 25, "action": "CALL"}],
        }
        fake = _FakeStreamlit(base_state)
        previous = sys.modules.get("streamlit")
        sys.modules["streamlit"] = fake
        try:
            namespace = runpy.run_path(str(APP_PATH), run_name=f"_poker_snapshot_smoke_{id(fake)}")
            namespace["add_cards"]([("A", "♠")], "hero", 2)
            self.assertEqual(fake.session_state.progress_history, [])
            fake.session_state.hero_cards = [("A", "♠"), ("K", "♠")]
            fake.session_state.progress_history = [{"event": "flop", "stage": "flop", "board_count": 3,
                                                     "equity": 0.6, "pot_odds": 0.2, "pot": 100, "call": 25, "action": "CALL"}]
            namespace["add_cards"]([("Q", "♠")], "board", 3)
            self.assertEqual(len(fake.session_state.progress_history), 1)
        finally:
            if previous is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = previous

    def test_undo_restores_cards_and_prior_progress_history_after_board_edit(self):
        history = [
            {"event": "플랍", "stage": "flop", "stage_update": 1, "board_count": 3,
             "equity": 0.58, "pot_odds": 0.20, "pot": 100, "call": 25, "action": "CALL"},
            {"event": "턴", "stage": "turn", "stage_update": 1, "board_count": 4,
             "equity": 0.62, "pot_odds": 0.25, "pot": 100, "call": 35, "action": "CALL"},
        ]
        state = {
            "step": 0, "table_size": 2, "stage": "turn",
            "hero_cards": [("A", "♠"), ("K", "♥")],
            "community_cards": [("Q", "♦"), ("9", "♣"), ("3", "♠"), ("2", "♥")],
            "undo_stack": [], "progress_history": [dict(item) for item in history],
            "progress_model_signature": (2, 1, "typical"),
        }
        fake = _FakeStreamlit(state)
        previous = sys.modules.get("streamlit")
        sys.modules["streamlit"] = fake
        try:
            namespace = runpy.run_path(str(APP_PATH), run_name=f"_poker_undo_smoke_{id(fake)}")
            namespace["snapshot"](reset_progress=False)
            fake.session_state.community_cards = fake.session_state.community_cards[:3]
            from decision_helpers import truncate_progress_history
            fake.session_state.progress_history = truncate_progress_history(fake.session_state.progress_history, 3)
            self.assertEqual([row["stage"] for row in fake.session_state.progress_history], ["flop"])
            namespace["undo_cards"]()
            self.assertEqual(len(fake.session_state.community_cards), 4)
            self.assertEqual(fake.session_state.progress_history, history)
            self.assertEqual(fake.session_state.progress_model_signature, (2, 1, "typical"))
        finally:
            if previous is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = previous

    def test_selected_community_cards_render_rank_ten_and_red_heart(self):
        fake = self._render(
            3, hero_cards=[("A", "♠"), ("K", "♥")],
            community_cards=[("T", "♦"), ("K", "♥")], table_size=3,
        )
        combined = "\n".join(fake.markdown_calls)
        self.assertIn("selected-card-face red", combined)
        self.assertIn("<span class=\"rank\">10</span>", combined)
        self.assertIn("<span class=\"suit\">♥</span>", combined)


if __name__ == "__main__":
    unittest.main()
