from __future__ import annotations
import ast
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
APP_AST = ast.parse(APP_SOURCE)


class TestUIWiring(unittest.TestCase):
    def test_card_picker_has_two_dropdowns(self):
        function = next(node for node in APP_AST.body if isinstance(node, ast.FunctionDef) and node.name == "render_card_picker")
        calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
        selectboxes = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "selectbox"]
        self.assertEqual(len(selectboxes), 2)
        self.assertIn("picker_card", APP_SOURCE)
        self.assertIn("on_change=_picker_selection_changed", APP_SOURCE)
        self.assertIn("index=None", APP_SOURCE)
        self.assertIn("카드가 자동으로 테이블에 놓입니다", APP_SOURCE)

    def test_keyboard_entry_is_always_visible_and_enter_submits(self):
        self.assertIn("키보드로 빠르게 입력", APP_SOURCE)
        self.assertIn("with st.form(form_key, clear_on_submit=True)", APP_SOURCE)
        self.assertIn("parse_card_tokens(typed)", APP_SOURCE)
        self.assertNotIn("키보드로 직접 입력하기 (선택 사항)", APP_SOURCE)

    def test_selected_cards_use_suit_aware_color_and_ten_label(self):
        self.assertIn("selected-card-face {color}", APP_SOURCE)
        self.assertIn("display_rank(rank)", APP_SOURCE)

    def test_plotly_charts_include_equity_pot_call_and_mc_convergence(self):
        self.assertIn('name=tr("내 승산")', APP_SOURCE)
        self.assertIn('name=tr("콜에 필요한 승산")', APP_SOURCE)
        self.assertIn("st.plotly_chart(fig", APP_SOURCE)
        self.assertIn("단계별 팟과 추가 콜", APP_SOURCE)
        self.assertIn("Monte Carlo convergence", APP_SOURCE)
        self.assertIn("chart-section-head", APP_SOURCE)
        self.assertIn('result.get("convergence", [])', APP_SOURCE)
        self.assertIn("outcome_counts", APP_SOURCE)
        self.assertIn('equity_low', APP_SOURCE)
        self.assertIn('equity_high', APP_SOURCE)
        self.assertIn('fill="tonexty"', APP_SOURCE)

    def test_recommended_move_panel_is_prominent(self):
        self.assertIn('st.subheader(tr("내가 추천하는 무브"))', APP_SOURCE)
        self.assertIn("move-card action-", APP_SOURCE)
        self.assertIn("권장 베팅 금액", APP_SOURCE)
        self.assertIn("지금 추가할 총액", APP_SOURCE)


if __name__ == "__main__":
    unittest.main()


class TestConditionalWidgetStatePersistence(unittest.TestCase):
    """Durable poker state must not share keys with conditional Streamlit widgets."""

    PERSISTENT_STATE_KEYS = {
        "table_size",
        "active_opponents",
        "opponent_style",
        "betting_mode",
        "pot_units",
        "call_units",
        "opponent_bet_units",
        "hero_contribution_units",
    }

    def test_conditional_widgets_use_separate_input_keys(self):
        widget_keys = set()
        for node in ast.walk(APP_AST):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"slider", "radio", "number_input"}:
                continue
            for keyword in node.keywords:
                if keyword.arg == "key" and isinstance(keyword.value, ast.Constant):
                    widget_keys.add(keyword.value.value)
        self.assertTrue(self.PERSISTENT_STATE_KEYS.isdisjoint(widget_keys))

    def test_table_size_is_a_slider_with_visible_number_at_each_position(self):
        self.assertIn("players = st.slider(", APP_SOURCE)
        self.assertIn('key="table_size_slider_input"', APP_SOURCE)
        self.assertIn('st.session_state.pop("table_size_input", None)', APP_SOURCE)
        self.assertIn("min_value=2", APP_SOURCE)
        self.assertIn("max_value=10", APP_SOURCE)
        self.assertIn("range(2, 11)", APP_SOURCE)
        self.assertIn("player-count-ticks", APP_SOURCE)
        self.assertIn("st.session_state.table_size = int(players)", APP_SOURCE)

    def test_opponent_model_is_one_fixed_balanced_baseline_not_four_options(self):
        self.assertIn('DEFAULT_OPPONENT_RANGE_KEY = "typical"', APP_SOURCE)
        self.assertIn('DEFAULT_OPPONENT_MODEL_KO = "중간 범위 기본 모델"', APP_SOURCE)
        self.assertIn("opponent-model-panel", APP_SOURCE)
        self.assertNotIn('key="opponent_style_input"', APP_SOURCE)
        self.assertIn('st.session_state.pop("opponent_style_input", None)', APP_SOURCE)
        self.assertNotIn("range_labels_ko", APP_SOURCE)
        self.assertNotIn("다른 상대 유형이면 결과가 얼마나 달라질까요?", APP_SOURCE)

    def test_active_opponent_count_is_copied_to_durable_state(self):
        self.assertIn('key="active_opponents_input"', APP_SOURCE)
        self.assertIn("st.session_state.active_opponents = int(active_opponents_value)", APP_SOURCE)

    def test_card_edits_and_opponent_model_changes_do_not_mix_old_equity_history(self):
        snapshot = next(node for node in ast.walk(APP_AST) if isinstance(node, ast.FunctionDef) and node.name == "snapshot")
        self.assertIn("progress_history", ast.unparse(snapshot))
        add_cards = next(node for node in ast.walk(APP_AST) if isinstance(node, ast.FunctionDef) and node.name == "add_cards")
        self.assertIn("snapshot(reset_progress=target == 'hero')", ast.unparse(add_cards))
        removal = next(node for node in ast.walk(APP_AST) if isinstance(node, ast.FunctionDef) and node.name == "card_remove_controls")
        self.assertIn("snapshot(reset_progress=target == 'hero')", ast.unparse(add_cards))
        self.assertIn("progress_model_signature", APP_SOURCE)
        self.assertIn("progress_signature_changed", APP_SOURCE)

    def test_betting_and_range_values_are_copied_to_durable_state(self):
        for key in (
            "betting_mode_input", "pot_units_input", "call_units_input",
            "opponent_bet_units_input", "hero_contribution_units_input",
        ):
            self.assertIn(f'key="{key}"', APP_SOURCE)
        self.assertIn("range_key = DEFAULT_OPPONENT_RANGE_KEY", APP_SOURCE)
        self.assertIn("betting_options_ko[betting_options.index(str(betting_mode_value))]", APP_SOURCE)
        self.assertIn("st.session_state.pot_units = int(pot_value)", APP_SOURCE)
        self.assertIn("st.session_state.call_units = int(call_value)", APP_SOURCE)


if __name__ == "__main__":
    unittest.main()
