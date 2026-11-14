from __future__ import annotations

import json
import uuid
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from poker_engine import (
    DECK,
    calculate_equity,
    decision_support,
    starting_hand_reference,
)
from storage import history_to_csv, load_history, save_hand_record
from decision_helpers import (append_equity_snapshot, build_progress_chart_rows, next_stage,
                               progress_model_signature, progress_signature_changed,
                               recommend_action, truncate_progress_history)
from i18n import translate
from theme_helpers import plotly_palette, resolve_theme_type
from ui_helpers import (
    is_five_multiple,
    display_card_label,
    display_rank,
    card_color,
    make_card_snapshot,
    parse_card_tokens,
    picker_card,
    RANK_PICKER_OPTIONS,
    SUIT_PICKER_OPTIONS,
    SUIT_PICKER_OPTIONS_EN,
    poker_table_html,
    remove_card,
    restore_card_snapshot,
)

st.set_page_config(
    page_title="Poker Hand Analyzer",
    page_icon="♠️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ACTIVE_THEME = resolve_theme_type(st)
PLOT_THEME = plotly_palette(ACTIVE_THEME)

APP_CSS = """
<style>
  /* Let Streamlit own native control color-scheme; custom surfaces use its live theme tokens. */
  .block-container {max-width:980px; padding-top:1.35rem; padding-bottom:3rem;}
  h1,h2,h3 {letter-spacing:-.035em; color:var(--text-color,#26382f);}
  .eyebrow {font-size:.76rem; font-weight:800; letter-spacing:.11em; color:color-mix(in srgb,var(--text-color,#26382f) 66%,transparent); text-transform:uppercase;}
  .step-title {font-size:1.65rem; font-weight:800; letter-spacing:-.04em; margin:.15rem 0 .35rem; color:var(--text-color,#26382f);}
  .step-copy {color:color-mix(in srgb,var(--text-color,#26382f) 72%,transparent); font-size:.96rem; margin-bottom:1rem;}
  .table-scene {position:relative; width:100%; height:390px; margin:1rem auto 1.15rem; overflow:hidden;
    border-radius:22px; background:radial-gradient(ellipse at center,#183e33 0%,#0d2d25 65%,#081e19 100%); box-shadow:0 12px 30px rgba(7,35,26,.22);}
  .felt {position:absolute; left:12%; top:18%; width:76%; height:64%; border:7px solid #9b7545;
    border-radius:50%; background:radial-gradient(ellipse at center,#267455 0%,#14533f 75%);
    box-shadow:inset 0 0 0 3px rgba(255,255,255,.08),0 8px 25px rgba(0,0,0,.22);
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:9px;}
  .felt-title {color:rgba(255,255,255,.82); font-weight:700; font-size:.75rem; letter-spacing:.08em;}
  .board-row,.hero-row {display:flex; align-items:center; justify-content:center; gap:6px; min-height:64px;}
  .p-card {width:42px; height:58px; border-radius:7px; background:#fff; color:#101820; display:flex; flex-direction:column;
    justify-content:center; align-items:center; box-shadow:0 3px 9px rgba(0,0,0,.25); animation:dealCard .34s ease-out both;}
  .p-card span {font-size:1.08rem; line-height:1.1; font-weight:850;}
  .p-card b {font-size:1rem; line-height:1.1;}
  .p-card.red {color:#d72e42;} .p-card.black {color:#18222b;}
  .p-card.empty {background:rgba(255,255,255,.09); color:rgba(255,255,255,.7); border:1px dashed rgba(255,255,255,.42); box-shadow:none;}
  .p-card.empty span {font-size:1rem;}
  .pot-label {font-size:.7rem; font-weight:700; color:rgba(255,255,255,.76); letter-spacing:.1em; margin-top:-5px;}
  .empty-hint {color:rgba(255,255,255,.72); font-size:.78rem; padding:.4rem;}
  .seat {position:absolute; z-index:2; box-sizing:border-box; transform:translate(-50%,-50%); width:62px; height:54px; border-radius:13px;
    display:flex; flex-direction:column; justify-content:center; align-items:center; color:#f4f5f2;
    background:rgba(4,17,14,.94); border:1px solid rgba(255,255,255,.3); box-shadow:0 3px 10px rgba(0,0,0,.24); animation:seatPop .28s ease-out both;}
  .table-count-badge {position:absolute; z-index:3; top:9px; right:12px; padding:5px 9px; border-radius:999px;
    background:rgba(4,17,14,.76); color:rgba(255,255,255,.95); font-size:.68rem; font-weight:800; letter-spacing:.04em;}
  .table-scene[data-player-count="8"] .seat.opponent {width:56px; height:50px;}
  .table-scene[data-player-count="9"] .seat.opponent {width:52px; height:48px;}
  .table-scene[data-player-count="10"] .seat.opponent {width:48px; height:46px;}
  .seat-icon {font-size:1.12rem; line-height:1.15;}
  .seat small {font-size:.64rem; font-weight:700; color:rgba(255,255,255,.88);}
  .seat.you {left:50%; top:91%; border-color:#e5c98d; background:#533d23;}
  @keyframes dealCard {from {opacity:0; transform:translateY(-14px) rotate(-4deg) scale(.88);} to {opacity:1; transform:translateY(0) rotate(0) scale(1);}}
  @keyframes seatPop {from {opacity:0; transform:translate(-50%,-50%) scale(.7);} to {opacity:1; transform:translate(-50%,-50%) scale(1);}}
  .phase-track {display:flex; gap:5px; margin:.7rem 0 1rem;}
  .phase-chip {flex:1; border-radius:9px; padding:7px 3px; text-align:center; font-size:.68rem; font-weight:700;
    color:var(--text-color,#26382f); background:var(--secondary-background-color,#eff3f0); border:1px solid var(--border-color,#dce5de);}
  .phase-chip.active {background:color-mix(in srgb,var(--primary-color,#287454) 22%,var(--secondary-background-color,#eff3f0));
    color:var(--text-color,#26382f); outline:1px solid var(--primary-color,#9ac8ae);}
  .phase-chip.done {background:color-mix(in srgb,var(--primary-color,#287454) 12%,var(--secondary-background-color,#eff3f0)); color:var(--text-color,#48705a);}
  .metric-card {border:1px solid var(--border-color,#e3e8e4); border-radius:14px; padding:15px 16px;
    background:var(--secondary-background-color,#fbfcfb); min-height:95px;}
  .metric-label {font-size:.76rem; color:color-mix(in srgb,var(--text-color,#26382f) 68%,transparent); font-weight:700;}
  .metric-value {font-size:1.7rem; font-weight:850; letter-spacing:-.045em; color:var(--text-color,#17231d); margin-top:3px;}
  .decision-card {border:1px solid var(--border-color,#d7e5dc); border-radius:16px;
    background:color-mix(in srgb,var(--primary-color,#287454) 8%,var(--secondary-background-color,#f4faf6)); padding:18px;}
  .picker-preview {display:flex; align-items:center; justify-content:center; gap:10px; min-height:70px;
    border:1px solid var(--border-color,#dfe7e1); border-radius:14px;
    background:var(--secondary-background-color,#fff); box-shadow:0 3px 12px rgba(18,53,38,.08); padding:8px 14px;}
  .picker-preview .rank {font-size:1.9rem; font-weight:900; line-height:1; color:var(--text-color,#17231d);}
  .picker-preview .suit {font-size:1.75rem; line-height:1;}
  .picker-preview.red .suit {color:#d43c4c;} .picker-preview.black .suit {color:var(--text-color,#182a24);}
  .picker-preview .hint {font-size:.75rem; color:color-mix(in srgb,var(--text-color,#26382f) 62%,transparent); font-weight:700; margin-left:6px;}
  .selected-card-face {display:flex; align-items:center; justify-content:center; flex-direction:column; gap:2px;
    width:52px; height:68px; margin:0 auto 5px; border-radius:9px; background:#fff;
    box-shadow:0 2px 8px rgba(0,0,0,.15); border:1px solid #e5e9e6; font-weight:900;}
  .selected-card-face .rank {font-size:1.18rem; line-height:1.1;}
  .selected-card-face .suit {font-size:1.22rem; line-height:1.1;}
  .selected-card-face.red {color:#d72e42;} .selected-card-face.black {color:#18222b;}
  .language-control {display:flex; justify-content:flex-end; align-items:center;}
  .player-count-note {display:flex; flex-wrap:wrap; gap:6px; margin:.35rem 0 .6rem;}
  .player-count-note span {border:1px solid var(--border-color,#dfe7e1); background:var(--secondary-background-color,#f7faf8);
    border-radius:999px; padding:4px 9px; font-size:.72rem; color:var(--text-color,#55665c); font-weight:650;}
  .move-card {border-radius:18px; padding:20px 22px; border:1px solid var(--border-color,#cbded2);
    background:color-mix(in srgb,var(--primary-color,#287454) 8%,var(--secondary-background-color,#fff)); box-shadow:0 7px 22px rgba(27,77,53,.1);}
  .move-card.action-fold {background:var(--secondary-background-color,#f5f6f7); border-color:var(--border-color,#d9dfe2);}
  .move-card.action-raise,.move-card.action-bet {background:color-mix(in srgb,#d58a24 14%,var(--secondary-background-color,#fff)); border-color:color-mix(in srgb,#d58a24 52%,var(--border-color,#ead6a7));}
  .move-kicker {font-size:.7rem; color:color-mix(in srgb,var(--text-color,#26382f) 62%,transparent); letter-spacing:.12em; font-weight:850; text-transform:uppercase;}
  .move-title {font-size:1.8rem; font-weight:900; letter-spacing:-.04em; color:var(--text-color,#17231d); margin:.28rem 0;}
  .move-amount {display:inline-block; margin:.25rem 0 .55rem; padding:8px 12px; border-radius:10px;
    background:color-mix(in srgb,var(--primary-color,#287454) 17%,var(--secondary-background-color,#fff));
    color:var(--text-color,#175b3c); font-weight:850; font-size:1.05rem;}
  .move-description {color:var(--text-color,#4e5e55); font-size:.94rem;}
  .chart-heading {font-weight:850; letter-spacing:-.025em; font-size:1.12rem; margin-bottom:.15rem; color:var(--text-color,#26382f);}
  .chart-legend-note {display:flex; flex-wrap:wrap; gap:14px; color:color-mix(in srgb,var(--text-color,#26382f) 70%,transparent); font-size:.8rem; margin:.15rem 0 .6rem;}
  .chart-section-head {display:flex; align-items:center; gap:9px; margin:.35rem 0 .25rem;}
  .chart-section-index {display:inline-flex; align-items:center; justify-content:center; min-width:28px; height:25px; padding:0 7px;
    border-radius:8px; background:color-mix(in srgb,var(--primary-color,#287454) 16%,var(--secondary-background-color,#fff));
    color:var(--text-color,#26382f); font-size:.68rem; font-weight:900; letter-spacing:.04em;}
  .chart-section-title {font-size:1.05rem; font-weight:850; letter-spacing:-.025em; color:var(--text-color,#26382f);}
  .chart-section-subtitle {font-size:.82rem; color:color-mix(in srgb,var(--text-color,#26382f) 70%,transparent); margin:0 0 .65rem 37px; line-height:1.45;}
  [data-testid="stPlotlyChart"] {border-radius:13px; overflow:hidden;}
  .legend-dot {display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px;}
  .sampling-card {display:flex; flex-direction:column; gap:5px; padding:15px 17px; margin:.65rem 0 1rem;
    border-radius:15px; border:1px solid color-mix(in srgb,var(--primary-color,#287454) 35%,var(--border-color,#dce5de));
    background:color-mix(in srgb,var(--primary-color,#287454) 9%,var(--secondary-background-color,#fff)); color:var(--text-color,#26382f);}
  .sampling-kicker {font-size:.68rem; font-weight:850; letter-spacing:.1em; color:color-mix(in srgb,var(--text-color,#26382f) 68%,transparent); text-transform:uppercase;}
  .sampling-main {font-size:1.08rem; font-weight:750; color:var(--text-color,#26382f);}
  .sampling-main strong {font-size:1.38rem; color:var(--primary-color,#1c8058); margin-left:5px;}
  .sampling-range {font-size:.9rem; color:var(--text-color,#26382f); font-variant-numeric:tabular-nums;}
  .sampling-note {font-size:.78rem; color:color-mix(in srgb,var(--text-color,#26382f) 72%,transparent); line-height:1.45;}
  div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button {border-radius:11px; font-weight:750; min-height:2.65rem;}
  div[data-testid="stButton"] button {border:1px solid var(--border-color,#dce5de); background:var(--secondary-background-color,#fbfcfb);
    color:var(--text-color,#253d30); box-shadow:0 2px 6px rgba(20,55,36,.06); transition:transform .12s ease,box-shadow .12s ease,border-color .12s ease;}
  div[data-testid="stButton"] button:hover {border-color:var(--primary-color,#9ab9a4); color:var(--text-color,#174c33); box-shadow:0 5px 14px rgba(20,70,43,.12); transform:translateY(-1px);}
  div[data-testid="stButton"] button[kind="primary"],div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background:linear-gradient(135deg,#246c4b,#174b35); color:#fff; border:1px solid #1b573c; box-shadow:0 5px 13px rgba(27,91,59,.22);}
  div[data-testid="stButton"] button[kind="primary"]:hover {background:linear-gradient(135deg,#2b7955,#1b573d); color:#fff;}
  [data-testid="stRadio"] label,[data-testid="stCheckbox"] label {font-weight:650; color:var(--text-color,#26382f);}
  [data-baseweb="select"] > div,[data-baseweb="input"] > div {background:var(--secondary-background-color,#fff); color:var(--text-color,#26382f); border-color:var(--border-color,#dce5de);}
  [data-baseweb="select"] input,[data-baseweb="input"] input,[data-baseweb="textarea"] textarea {color:var(--text-color,#26382f);}
  [data-baseweb="select"] svg {fill:var(--text-color,#26382f);}
  [data-testid="stSlider"] [data-baseweb="slider"] {padding-top:.25rem;}
  .player-count-ticks {display:grid; grid-template-columns:repeat(9,minmax(0,1fr)); gap:0; margin:-.58rem .54rem .35rem;
    color:var(--text-color,#697a6f); font-size:.73rem; font-weight:750; text-align:center;}
  .player-count-ticks span {padding-top:2px; border-top:1px solid var(--border-color,#dce5de);}
  .player-count-current {display:inline-flex; align-items:center; gap:7px; border:1px solid var(--border-color,#d5e4d9);
    background:color-mix(in srgb,var(--primary-color,#287454) 12%,var(--secondary-background-color,#f1f7f2));
    color:var(--text-color,#1d5b3c); border-radius:999px; padding:7px 12px; font-weight:800; margin:.1rem 0 .35rem;}
  .opponent-model-panel {display:flex; align-items:center; gap:14px; padding:16px 18px;
    border:1px solid var(--border-color,#dce8df); border-radius:16px;
    background:var(--secondary-background-color,#f3f8f4); box-shadow:0 5px 18px rgba(26,66,43,.08);}
  .opponent-model-icon {width:42px; height:42px; border-radius:13px;
    background:color-mix(in srgb,var(--primary-color,#287454) 18%,var(--background-color,#fff));
    color:var(--text-color,#1b6241); display:flex; align-items:center; justify-content:center; font-size:1.2rem; flex:0 0 42px;}
  .opponent-model-kicker {font-size:.66rem; color:color-mix(in srgb,var(--text-color,#26382f) 68%,transparent); font-weight:850; letter-spacing:.12em;}
  .opponent-model-title {font-size:1.06rem; color:var(--text-color,#193b2a); font-weight:850; margin:.12rem 0;}
  .opponent-model-copy {font-size:.83rem; color:color-mix(in srgb,var(--text-color,#26382f) 76%,transparent); line-height:1.45;}
  .metric-card {background:var(--secondary-background-color,#fff); border-color:var(--border-color,#e1e9e2); box-shadow:0 4px 15px rgba(26,60,40,.08);}
  .decision-card,.move-card {box-shadow:0 8px 24px rgba(25,72,45,.1);}
  .stProgress > div > div > div > div {background:var(--primary-color,#287454);}
  [data-testid="stHeader"] {background:transparent;}
  .main .block-container {max-width:960px; padding:1.55rem 2rem 2.7rem; margin-top:1.05rem;
    background:color-mix(in srgb,var(--secondary-background-color,#fff) 24%,var(--background-color,#fff));
    color:var(--text-color,#26382f); border:1px solid var(--border-color,rgba(110,130,118,.25)); border-radius:25px;
    box-shadow:0 18px 48px rgba(23,54,38,.1);}
  h1 {font-size:2.05rem !important; font-weight:850 !important;}
  h2,h3 {color:var(--text-color,#203b2e);}
  .eyebrow {display:inline-flex; padding:5px 10px; border-radius:999px;
    background:var(--secondary-background-color,#edf4ef); color:var(--text-color,#476b55); font-size:.69rem; letter-spacing:.13em;}
  .step-title {font-size:1.78rem;}
  .step-copy {line-height:1.55;}
  .decision-card,.move-card {box-shadow:0 8px 24px rgba(25,72,45,.1);}
  @media (max-width:650px) {
    .table-scene {height:330px;}
    .felt {left:8%; width:84%; top:20%; height:60%;}
    .seat {width:48px; height:44px;}
    .table-scene[data-player-count="8"] .seat.opponent {width:44px; height:42px;}
    .table-scene[data-player-count="9"] .seat.opponent {width:38px; height:40px;}
    .table-scene[data-player-count="10"] .seat.opponent {width:34px; height:38px;}
    .table-scene[data-player-count="8"] .seat.opponent small,
    .table-scene[data-player-count="9"] .seat.opponent small,
    .table-scene[data-player-count="10"] .seat.opponent small {font-size:.52rem;}
    .table-scene[data-player-count="10"] .seat.opponent .seat-icon {font-size:.9rem;}
    .p-card {width:34px; height:50px;}
    .p-card span {font-size:.95rem;}
    .main .block-container {padding:1rem .85rem 1.8rem; margin-top:.35rem; border-radius:17px;}
    h1 {font-size:1.55rem !important;}
    .step-title {font-size:1.42rem;}
    .player-count-ticks {font-size:.66rem; margin-left:.25rem; margin-right:.25rem;}
  }
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)

STAGES = {
    "preflop": {
        "label": "게임 시작 전 (Preflop)",
        "display": "시작 전",
        "board_count": 0,
        "title": "아직 공개된 카드가 없어요",
        "description": "각자 비공개 카드 2장만 받은 상태예요. 테이블 가운데 공개 카드는 아직 없습니다.",
        "analogy": "내 카드 2장으로 시작하는 순간",
    },
    "flop": {
        "label": "첫 공개 카드 3장 (Flop)",
        "display": "첫 공개",
        "board_count": 3,
        "title": "테이블 가운데 카드 3장이 놓였어요",
        "description": "모든 사람이 함께 사용하는 카드 3장이 처음 공개된 상태예요.",
        "analogy": "첫 3장이 공개된 순간",
    },
    "turn": {
        "label": "네 번째 카드 공개 (Turn)",
        "display": "네 번째",
        "board_count": 4,
        "title": "공용 카드가 한 장 더 공개됐어요",
        "description": "처음 공개된 3장에 네 번째 카드가 추가된 상태예요.",
        "analogy": "4번째 공용 카드까지 나온 순간",
    },
    "river": {
        "label": "마지막 카드 공개 (River)",
        "display": "마지막",
        "board_count": 5,
        "title": "마지막 공용 카드까지 공개됐어요",
        "description": "테이블 가운데 공용 카드 5장이 모두 공개된 마지막 상태예요.",
        "analogy": "최종 5장이 모두 놓인 순간",
    },
}

# One fixed, balanced baseline keeps the beginner workflow simple. The model is
# an explicit assumption, not a prediction of real opponents' private cards.
DEFAULT_OPPONENT_RANGE_KEY = "typical"
DEFAULT_OPPONENT_MODEL_KO = "중간 범위 기본 모델"
DEFAULT_OPPONENT_MODEL_EN = "Balanced baseline"
OPPONENT_MODEL_DESC_KO = "강한 시작 카드와 보통 시작 카드를 함께 고려하는 단일 가중 모델입니다."
OPPONENT_MODEL_DESC_EN = "A single weighted baseline that blends stronger and more ordinary starting hands."
LEGACY_RANGE_LABELS_KO = {
    "random": "무작위 카드",
    "strong": "강한 카드 위주",
    "typical": DEFAULT_OPPONENT_MODEL_KO,
    "loose": "넓은 카드 범위",
}
LEGACY_RANGE_LABELS_EN = {
    "random": "Uniform random",
    "strong": "Strong hands",
    "typical": DEFAULT_OPPONENT_MODEL_EN,
    "loose": "Wide range",
}

DEFAULTS: dict[str, Any] = {
    "step": 0,
    "table_size": 6,
    "stage": "flop",
    "hero_cards": [],
    "community_cards": [],
    "undo_stack": [],
    "active_opponents": 2,
    "opponent_style": DEFAULT_OPPONENT_MODEL_KO,
    "betting_mode": "간편",
    "pot_units": 100,
    "call_units": 30,
    "opponent_bet_units": 30,
    "hero_contribution_units": 0,
    "analysis": None,
    "saved_record_id": None,
    "last_error": None,
    "progress_history": [],
    "progress_model_signature": None,
    "hand_session_id": None,
    "language": "KOR",
}
for _key, _value in DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value
# Migrate old radio/selector widget keys from v10.2.4 without disturbing durable game state.
st.session_state.pop("table_size_input", None)
st.session_state.pop("opponent_style_input", None)
# There is intentionally one beginner-facing opponent model in v10.2.5.
st.session_state.opponent_style = DEFAULT_OPPONENT_MODEL_KO

# Read the durable language before the compact header control is rendered.
# The actual EN/KOR selector sits beside the title, not detached above the app.
LANGUAGE = "EN" if str(st.session_state.language).upper() == "EN" else "KOR"

def tr(text: str, **kwargs) -> str:
    return translate(text, LANGUAGE, **kwargs)

STAGES_EN = {
    "preflop": {"label": "Before the flop (Preflop)", "description": "Each player has two private cards. No community cards are on the table yet.", "analogy": "Starting with your two private cards"},
    "flop": {"label": "First 3 community cards (Flop)", "description": "The first three shared community cards have been revealed.", "analogy": "The first three cards are revealed"},
    "turn": {"label": "Fourth community card (Turn)", "description": "A fourth community card has been added to the first three.", "analogy": "The fourth community card is revealed"},
    "river": {"label": "Final community card (River)", "description": "All five community cards are now visible.", "analogy": "All five community cards are on the table"},
}

def stage_text(stage_key: str, field: str) -> str:
    if LANGUAGE == "EN":
        return STAGES_EN[stage_key][field]
    return STAGES[stage_key][field]


def clear_analysis() -> None:
    st.session_state.analysis = None
    st.session_state.saved_record_id = None


def snapshot(*, reset_progress: bool = False) -> None:
    entry = make_card_snapshot(st.session_state.hero_cards, st.session_state.community_cards)
    # Undo must restore the timeline as well as the visible cards; otherwise
    # correcting the river can permanently erase the valid flop/turn history.
    entry["progress_history"] = [dict(item) for item in st.session_state.progress_history]
    entry["progress_model_signature"] = st.session_state.progress_model_signature
    st.session_state.undo_stack.append(entry)
    st.session_state.undo_stack = st.session_state.undo_stack[-50:]
    clear_analysis()
    if reset_progress:
        # A changed hero hand invalidates every previous equity estimate.
        st.session_state.progress_history = []


def undo_cards() -> None:
    if not st.session_state.undo_stack:
        return
    previous_entry = st.session_state.undo_stack[-1]
    previous = restore_card_snapshot(st.session_state.undo_stack)
    if previous is None:
        return
    st.session_state.hero_cards, st.session_state.community_cards = previous
    st.session_state.progress_history = [dict(item) for item in previous_entry.get("progress_history", [])]
    st.session_state.progress_model_signature = previous_entry.get("progress_model_signature")
    clear_analysis()


def add_cards(cards: list[tuple[str, str]], target: str, maximum: int) -> None:
    current = st.session_state.hero_cards + st.session_state.community_cards
    if len(cards) == 0:
        raise ValueError("카드를 입력해 주세요.")
    if any(card in current for card in cards):
        raise ValueError("이미 테이블에 있는 카드가 포함되어 있습니다. 중복 카드는 사용할 수 없어요.")
    if target == "hero" and len(st.session_state.hero_cards) + len(cards) > maximum:
        raise ValueError(f"내 카드는 최대 {maximum}장까지 입력할 수 있어요.")
    if target == "board" and len(st.session_state.community_cards) + len(cards) > maximum:
        raise ValueError(f"현재 단계에서는 공용 카드 {maximum}장까지만 입력할 수 있어요.")
    snapshot(reset_progress=(target == "hero"))
    if target == "hero":
        st.session_state.hero_cards.extend(cards)
    else:
        st.session_state.community_cards.extend(cards)


def card_remove_controls(target: str) -> None:
    cards = st.session_state.hero_cards if target == "hero" else st.session_state.community_cards
    if not cards:
        return
    cols = st.columns(max(1, len(cards)))
    for index, card in enumerate(cards):
        rank, suit = card
        color = card_color(suit)
        with cols[index]:
            st.markdown(
                f'<div class="selected-card-face {color}"><span class="rank">{escape(display_rank(rank))}</span>'
                f'<span class="suit">{escape(suit)}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("× Remove" if LANGUAGE == "EN" else "× 회수", key=f"remove_{target}_{index}_{len(cards)}", use_container_width=True):
                snapshot(reset_progress=(target == "hero"))
                if target == "hero":
                    st.session_state.hero_cards = remove_card(st.session_state.hero_cards, index)
                else:
                    st.session_state.community_cards = remove_card(st.session_state.community_cards, index)
                    st.session_state.progress_history = truncate_progress_history(
                        st.session_state.progress_history, len(st.session_state.community_cards)
                    )
                st.rerun()


def _picker_selection_changed(target: str, maximum: int) -> None:
    """Automatically deal a card as soon as both dropdowns have a value."""
    suit_key = f"{target}_picker_suit"
    rank_key = f"{target}_picker_rank"
    suit_label = st.session_state.get(suit_key)
    rank_label = st.session_state.get(rank_key)
    if not suit_label or not rank_label:
        return
    try:
        selected = picker_card(rank_label, suit_label)
        add_cards([selected], target, maximum)
        st.session_state[suit_key] = None
        st.session_state[rank_key] = None
        st.session_state.last_error = None
    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.session_state[suit_key] = None
        st.session_state[rank_key] = None


def render_card_picker(target: str, maximum: int) -> None:
    """Render two-step dropdowns that auto-deal plus an always-visible shortcut field."""
    cards = st.session_state.hero_cards if target == "hero" else st.session_state.community_cards
    if len(cards) >= maximum:
        return

    st.markdown(f"**{tr('카드를 두 번 선택해 주세요')}**")
    st.caption(
        "Choose a suit and a rank. The card is dealt automatically after the second choice." if LANGUAGE == "EN"
        else "무늬와 숫자를 고르면 두 번째 선택 직후 카드가 자동으로 테이블에 놓입니다. 추가 버튼을 누를 필요가 없어요."
    )
    suit_col, rank_col = st.columns(2)
    suit_options = SUIT_PICKER_OPTIONS_EN if LANGUAGE == "EN" else SUIT_PICKER_OPTIONS
    suit_key = f"{target}_picker_suit"
    rank_key = f"{target}_picker_rank"
    with suit_col:
        st.selectbox(
            "① Suit" if LANGUAGE == "EN" else "① 무늬 선택",
            options=suit_options,
            index=None,
            placeholder="Choose suit" if LANGUAGE == "EN" else "무늬를 선택하세요",
            key=suit_key,
            on_change=_picker_selection_changed,
            args=(target, maximum),
            help="Choose the card suit." if LANGUAGE == "EN" else "카드의 모양을 먼저 고릅니다.",
        )
    with rank_col:
        st.selectbox(
            "② Rank" if LANGUAGE == "EN" else "② 숫자 / 알파벳 선택",
            options=RANK_PICKER_OPTIONS,
            index=None,
            placeholder="Choose rank" if LANGUAGE == "EN" else "숫자 또는 알파벳을 선택하세요",
            key=rank_key,
            on_change=_picker_selection_changed,
            args=(target, maximum),
            help="A, 2–10, J, Q, K." if LANGUAGE == "EN" else "A, 2부터 10, J, Q, K 순서입니다.",
        )

    if st.session_state.last_error:
        message = str(st.session_state.last_error)
        if LANGUAGE == "EN" and "중복 카드" in message:
            message = "This card is already in use. Choose a different card."
        st.warning(message)
        st.session_state.last_error = None

    # Keep keyboard input open and immediately available. Pressing Enter submits
    # the form, avoiding the old expander-open + input-focus double interaction.
    st.markdown(f"**{'Quick keyboard entry' if LANGUAGE == 'EN' else '키보드로 빠르게 입력'}**")
    st.caption(
        "Type cards in either order, e.g. AS / SA, KH / HK, 10D / D10. Press Enter to deal." if LANGUAGE == "EN"
        else "순서 상관없이 입력: AS / SA, 10D / D10, KH / HK, ㅋㅎ / ㅋH. 입력 후 Enter를 누르면 바로 놓입니다."
    )
    entry_key = f"{target}_quick_input_{len(cards)}_{st.session_state.stage}"
    form_key = f"{target}_quick_form_{len(cards)}_{st.session_state.stage}"
    with st.form(form_key, clear_on_submit=True):
        entry_col, submit_col = st.columns([4, 1])
        with entry_col:
            typed = st.text_input(
                "Card shortcuts" if LANGUAGE == "EN" else "카드 기호 입력",
                placeholder="e.g. AS KH 10D QC" if LANGUAGE == "EN" else "예: AS KH 10D QC",
                key=entry_key,
                label_visibility="collapsed",
            )
        with submit_col:
            submitted = st.form_submit_button("Deal ↵" if LANGUAGE == "EN" else "놓기 ↵", use_container_width=True)
    if submitted:
        try:
            parsed = parse_card_tokens(typed)
            add_cards(parsed, target, maximum)
            st.rerun()
        except Exception as exc:
            message = str(exc)
            if LANGUAGE == "EN" and "형식을 읽지 못했습니다" in message:
                message = "Card format not recognized. Try AS / SA, KH / HK, ㅋㅎ / ㅋH, or 10D / D10."
            elif LANGUAGE == "EN" and "중복 카드" in message:
                message = "Duplicate cards are not allowed."
            st.error(message)


def render_table(subtitle: str = "") -> None:
    stage = STAGES[st.session_state.stage]
    st.markdown(
        poker_table_html(
            int(st.session_state.table_size),
            st.session_state.hero_cards,
            st.session_state.community_cards,
            board_slots=stage["board_count"],
            subtitle=subtitle or stage_text(st.session_state.stage, "analogy"),
            language=LANGUAGE,
        ),
        unsafe_allow_html=True,
    )


def phase_track(active: int) -> None:
    names = (["Players", "Stage", "My cards", "Board", "Game info", "Results"]
             if LANGUAGE == "EN" else ["인원", "단계", "내 카드", "공용 카드", "게임 정보", "결과"])
    fragments = []
    for index, name in enumerate(names):
        css = "active" if index == active else "done" if index < active else ""
        fragments.append(f'<div class="phase-chip {css}">{index + 1}. {name}</div>')
    st.markdown(f'<div class="phase-track">{"".join(fragments)}</div>', unsafe_allow_html=True)


def go_to(step: int) -> None:
    st.session_state.step = max(0, min(5, step))
    st.rerun()


def validate_all_cards() -> None:
    from poker_engine import validate_cards
    validate_cards(st.session_state.hero_cards, st.session_state.community_cards)


def render_footer_nav(back_to: int, next_label: str = "다음으로") -> None:
    left, right = st.columns([1, 2])
    with left:
        if st.button(tr("← 이전"), key=f"back_{st.session_state.step}", use_container_width=True):
            go_to(back_to)
    with right:
        if st.button(next_label + " →", type="primary", key=f"next_{st.session_state.step}", use_container_width=True):
            go_to(st.session_state.step + 1)


# Header with language control aligned to the title, in the app's visible content area.
header_main, header_language = st.columns([5, 2], vertical_alignment="center")
with header_language:
    previous_language = st.session_state.language
    language_value = st.radio(
        "Language / 언어", options=["EN", "KOR"],
        index=0 if previous_language == "EN" else 1,
        horizontal=True, key="language_choice", label_visibility="collapsed",
    )
LANGUAGE = "EN" if language_value == "EN" else "KOR"
if LANGUAGE != previous_language:
    # Clear only translated widget selections; durable hand data remains untouched.
    for _widget_key in (
        "betting_mode_input",
        "hero_picker_suit", "hero_picker_rank", "board_picker_suit", "board_picker_rank",
    ):
        st.session_state.pop(_widget_key, None)
st.session_state.language = LANGUAGE
with header_main:
    st.markdown(f'<div class="eyebrow">{tr("OFFLINE POKER STUDY · LOCAL ONLY")}</div>', unsafe_allow_html=True)
    st.title(tr("♠️ 내 포커 상황 분석하기"))
st.caption("v10.2.6 · Probability analysis and decision support." if LANGUAGE == "EN" else "v10.2.6 · 확률 분석 및 의사결정 보조")
if st.session_state.hero_cards:
    st.caption(tr("🟢 현재 핸드 진행 중 · 내 카드와 공개 카드는 다음 단계에서도 유지됩니다."))
phase_track(int(st.session_state.step))

step = int(st.session_state.step)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 · Table size
# ─────────────────────────────────────────────────────────────────────────────
if step == 0:
    st.markdown(f'<div class="step-title">{tr("테이블에 몇 명이 앉아 있나요?")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="step-copy">{tr("나를 포함한 전체 인원으로 선택해 주세요. 상대가 몇 명인지 화면에 표시해 드립니다.")}</div>', unsafe_allow_html=True)
    # Keep durable game state separate from Streamlit's conditional widget state.
    # Streamlit removes keys for widgets that are not rendered on the next page;
    # using the domain key as the widget key would silently reset table_size to 6.
    players = st.slider(
        "Total players" if LANGUAGE == "EN" else "참가 인원 선택",
        min_value=2,
        max_value=10,
        value=int(st.session_state.table_size),
        step=1,
        key="table_size_slider_input",
        help="Slide to choose the total number of players, including you." if LANGUAGE == "EN" else "막대를 움직여 나를 포함한 전체 참가 인원을 선택하세요.",
    )
    st.markdown('<div class="player-count-ticks" aria-label="Player count positions">' + ''.join(f'<span>{count}</span>' for count in range(2, 11)) + '</div>', unsafe_allow_html=True)
    st.session_state.table_size = int(players)
    st.markdown(f'<div class="player-count-current">♟ {tr("참가자 {count}명", count=players)} · {tr("나 1명 + 상대 {opponents}명", opponents=players - 1)}</div>', unsafe_allow_html=True)
    st.caption("2 = Heads-up · 3–5 = Short-handed · 6 = 6-max · 7–10 = Full ring" if LANGUAGE == "EN" else "2명 = 1대1 · 3~5명 = 소수 인원 테이블 · 6명 = 6-Max · 7~10명 = 풀 링")
    render_table((f"{players} players · including you" if LANGUAGE == "EN" else f"참가자 {players}명 · 나 포함"))
    st.info(tr("사람 모양은 테이블 인원을 보여주는 그림입니다. 실제 상대의 카드나 행동을 추적하지 않습니다."))
    if st.button(tr("게임 시작하기 →"), type="primary", use_container_width=True):
        st.session_state.active_opponents = min(int(st.session_state.active_opponents), players - 1)
        if not st.session_state.hand_session_id:
            st.session_state.hand_session_id = uuid.uuid4().hex
        go_to(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 · Current stage
# ─────────────────────────────────────────────────────────────────────────────
elif step == 1:
    st.markdown(f'<div class="step-title">{tr("지금 카드가 어디까지 공개됐나요?")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="step-copy">{tr("어려운 포커 용어 대신 테이블 위에 공개된 카드 수로 고르면 됩니다.")}</div>', unsafe_allow_html=True)
    stage_items = list(STAGES.items())
    for key, item in stage_items:
        selected = st.session_state.stage == key
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"**{'● ' if selected else ''}{stage_text(key, 'label')}**")
                st.caption(stage_text(key, "description"))
                st.caption((f"{item['board_count']} community card(s)" if LANGUAGE == "EN" else f"공용 카드 {item['board_count']}장"))
            with right:
                if st.button("Select" if LANGUAGE == "EN" else "선택", key=f"stage_{key}", type="primary" if selected else "secondary", use_container_width=True):
                    st.session_state.stage = key
                    if len(st.session_state.community_cards) > item["board_count"]:
                        snapshot(reset_progress=False)
                        st.session_state.community_cards = st.session_state.community_cards[:item["board_count"]]
                        st.session_state.progress_history = truncate_progress_history(
                            st.session_state.progress_history, item["board_count"]
                        )
                    clear_analysis()
                    st.rerun()
    current_stage = STAGES[st.session_state.stage]
    st.success(tr("선택한 단계: {label} — 공용 카드 {count}장을 입력합니다.", label=stage_text(st.session_state.stage, "label"), count=current_stage["board_count"]))
    render_table(stage_text(st.session_state.stage, "analogy"))
    render_footer_nav(0, "Enter my cards" if LANGUAGE == "EN" else "내 카드 입력하기")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 · Hero cards
# ─────────────────────────────────────────────────────────────────────────────
elif step == 2:
    st.markdown(f'<div class="step-title">{tr("내 카드 2장을 놓아 주세요")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="step-copy">{tr("카드에 적힌 숫자·알파벳과 무늬를 짧게 입력하면 됩니다. 예: AS KH, 10D QC")}</div>', unsafe_allow_html=True)
    render_table("My private cards" if LANGUAGE == "EN" else "내가 받은 카드")
    st.markdown(f"**{tr('카드를 두 번 선택해 주세요')}**")
    current = st.session_state.hero_cards
    if current:
        st.markdown(f"**{tr('선택된 내 카드 · 아래 × 버튼으로 한 장씩 회수합니다.')}**")
        card_remove_controls("hero")
    if len(current) < 2:
        render_card_picker("hero", 2)
    else:
        st.success(tr("내 카드 2장이 준비됐어요."))
    undo_col, spacer_col = st.columns([1, 2])
    with undo_col:
        if st.button(tr("↶ 실행 취소"), disabled=not st.session_state.undo_stack, use_container_width=True):
            undo_cards()
            st.rerun()
    left, right = st.columns([1, 2])
    with left:
        if st.button(tr("← 이전"), use_container_width=True):
            go_to(1)
    with right:
        if st.button(tr("공용 카드 입력하기 →"), type="primary", disabled=len(st.session_state.hero_cards) != 2, use_container_width=True):
            go_to(3)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 · Community cards
# ─────────────────────────────────────────────────────────────────────────────
elif step == 3:
    stage = STAGES[st.session_state.stage]
    target_count = int(stage["board_count"])
    st.markdown(f'<div class="step-title">{tr("테이블 가운데 공개된 카드를 놓아 주세요")}</div>', unsafe_allow_html=True)
    stage_label_now = stage_text(st.session_state.stage, "label")
    stage_copy = (f"Current stage: <b>{stage_label_now}</b>. Enter {target_count} community card(s) in total." if LANGUAGE == "EN" else f'<div class="step-copy">현재 단계는 <b>{stage_label_now}</b>입니다. 공개된 공용 카드는 모두 합쳐 <b>{target_count}장</b>이어야 해요.</div>')
    if LANGUAGE == "EN":
        st.markdown(f'<div class="step-copy">{stage_copy}</div>', unsafe_allow_html=True)
    else:
        st.markdown(stage_copy, unsafe_allow_html=True)
    render_table(stage_text(st.session_state.stage, "analogy"))
    current = st.session_state.community_cards
    if current:
        st.markdown("**Selected community cards · use the × button under a card to remove it.**" if LANGUAGE == "EN" else "**선택된 공용 카드 · 각 카드 아래 × 회수 버튼으로 한 장씩 제거합니다.**")
        card_remove_controls("board")
    if target_count == 0:
        st.info("No community cards are used at this stage. Continue to the next step." if LANGUAGE == "EN" else "이 단계에서는 공용 카드가 아직 없습니다. 바로 다음으로 넘어가면 돼요.")
    elif len(current) < target_count:
        st.caption(tr("{remaining}장을 더 선택하면 됩니다. 카드는 한 장씩 테이블에 놓입니다.", remaining=target_count - len(current)))
        render_card_picker("board", target_count)
    else:
        st.success(tr("공용 카드 {count}장이 모두 입력됐습니다.", count=target_count))
    if st.session_state.undo_stack:
        if st.button(tr("↶ 실행 취소"), use_container_width=True):
            undo_cards()
            st.rerun()
    left, right = st.columns([1, 2])
    with left:
        if st.button(tr("← 이전"), use_container_width=True):
            go_to(2)
    with right:
        if st.button("Enter game details →" if LANGUAGE == "EN" else "게임 정보 입력하기 →", type="primary", disabled=len(current) != target_count, use_container_width=True):
            go_to(4)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 · Betting and opponent assumptions
# ─────────────────────────────────────────────────────────────────────────────
elif step == 4:
    st.markdown(f'<div class="step-title">{tr("현재 게임 상황을 알려 주세요")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="step-copy">{tr("정확한 금액과 남아 있는 상대 수를 입력하면 현재 승산과 콜 판단을 계산합니다.")}</div>', unsafe_allow_html=True)
    render_table("Current game situation" if LANGUAGE == "EN" else "현재 입력한 게임 상황")
    st.markdown(f"**{tr('아직 게임에 남아 있는 상대는 몇 명인가요?')}**")
    max_active = max(1, int(st.session_state.table_size) - 1)
    st.session_state.active_opponents = min(max(1, int(st.session_state.active_opponents)), max_active)
    # This widget only exists on the game-info page. Use a disposable widget key
    # and copy its value into durable hand state before leaving the page.
    if "active_opponents_input" in st.session_state:
        st.session_state.active_opponents_input = min(
            max(1, int(st.session_state.active_opponents_input)), max_active
        )
    if max_active == 1:
        # Heads-up has exactly one opponent. A Streamlit slider with min=max=1
        # raises StreamlitInvalidMinMaxError, so render a fixed value instead.
        st.session_state.active_opponents = 1
        st.session_state.pop("active_opponents_input", None)
        st.info("Heads-up: exactly 1 opponent remains." if LANGUAGE == "EN" else "1대1 게임입니다. 남아 있는 상대는 1명으로 고정됩니다.")
    else:
        if "active_opponents_input" in st.session_state:
            st.session_state.active_opponents_input = min(
                max(1, int(st.session_state.active_opponents_input)), max_active
            )
        active_opponents_value = st.slider(
            "Active opponents" if LANGUAGE == "EN" else "남아 있는 상대",
            min_value=1,
            max_value=max_active,
            value=int(st.session_state.active_opponents),
            step=1,
            key="active_opponents_input",
            help="Count opponents who have not folded." if LANGUAGE == "EN" else "폴드하지 않고 아직 이 판에 참여 중인 상대만 세면 됩니다.",
        )
        st.session_state.active_opponents = int(active_opponents_value)

    st.markdown(f"**{tr('상대 카드 가정')}**")
    model_title = DEFAULT_OPPONENT_MODEL_EN if LANGUAGE == "EN" else DEFAULT_OPPONENT_MODEL_KO
    model_description = OPPONENT_MODEL_DESC_EN if LANGUAGE == "EN" else OPPONENT_MODEL_DESC_KO
    model_note = ("One fixed baseline is used for a consistent, fast result. It is not an observation of the opponents' actual cards." if LANGUAGE == "EN"
                  else "복잡한 유형 선택 없이 하나의 기준으로 일관되게 계산합니다. 실제 상대의 카드나 성향을 관측한 결과는 아닙니다.")
    st.markdown(
        f'<div class="opponent-model-panel"><div class="opponent-model-icon">♠</div><div>'
        f'<div class="opponent-model-kicker">{("MONTE CARLO · WEIGHTED BASELINE" if LANGUAGE == "EN" else "MONTE CARLO · 단일 기본 모델")}</div>'
        f'<div class="opponent-model-title">{escape(model_title)}</div>'
        f'<div class="opponent-model-copy">{escape(model_description)}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.caption(model_note)

    st.divider()
    st.markdown(f"**{tr('팟과 베팅 금액')}**")
    betting_options_ko = ["간편", "고급"]
    betting_options = [tr(item) for item in betting_options_ko]
    betting_mode_value = st.radio(
        "Input mode" if LANGUAGE == "EN" else "입력 방식", betting_options, horizontal=True,
        index=betting_options.index(tr(st.session_state.betting_mode)),
        key="betting_mode_input",
    )
    st.session_state.betting_mode = betting_options_ko[betting_options.index(str(betting_mode_value))]
    if st.session_state.betting_mode == "간편":
        c1, c2 = st.columns(2)
        with c1:
            pot_value = st.number_input("Current pot" if LANGUAGE == "EN" else "현재 팟", min_value=0, max_value=10_000_000, value=int(st.session_state.pot_units), step=5, format="%d", key="pot_units_input", help="Points currently in the pot, before your call." if LANGUAGE == "EN" else "내가 추가로 콜하기 전, 현재 가운데 쌓인 포인트입니다.")
            st.session_state.pot_units = int(pot_value)
        with c2:
            call_value = st.number_input("Additional call" if LANGUAGE == "EN" else "내가 추가로 콜할 금액", min_value=0, max_value=10_000_000, value=int(st.session_state.call_units), step=5, format="%d", key="call_units_input", help="Points you need to add to stay in the hand." if LANGUAGE == "EN" else "계속 참여하려면 지금 더 내야 하는 포인트입니다.")
            st.session_state.call_units = int(call_value)
    else:
        pot_value = st.number_input("Current pot" if LANGUAGE == "EN" else "현재 팟", min_value=0, max_value=10_000_000, value=int(st.session_state.pot_units), step=5, format="%d", key="pot_units_input", help="The pot before your additional call." if LANGUAGE == "EN" else "내가 추가로 콜하기 전의 팟입니다.")
        st.session_state.pot_units = int(pot_value)
        c1, c2 = st.columns(2)
        with c1:
            opponent_bet_value = st.number_input("Opponent's contribution this round" if LANGUAGE == "EN" else "상대가 이번 라운드에 넣은 금액", min_value=0, max_value=10_000_000, value=int(st.session_state.opponent_bet_units), step=5, format="%d", key="opponent_bet_units_input")
            st.session_state.opponent_bet_units = int(opponent_bet_value)
        with c2:
            hero_contribution_value = st.number_input("My contribution this round" if LANGUAGE == "EN" else "내가 이번 라운드에 이미 넣은 금액", min_value=0, max_value=10_000_000, value=int(st.session_state.hero_contribution_units), step=5, format="%d", key="hero_contribution_units_input")
            st.session_state.hero_contribution_units = int(hero_contribution_value)
        st.session_state.call_units = max(0, int(st.session_state.opponent_bet_units) - int(st.session_state.hero_contribution_units))
        st.info((f"Additional call used: **{st.session_state.call_units:,} points**" if LANGUAGE == "EN" else f"계산에 사용할 추가 콜 금액: **{st.session_state.call_units:,} 포인트**"))
    st.caption("All amounts are points entered in increments of 5. No real money or bets are involved." if LANGUAGE == "EN" else "모든 금액은 포인트이며, 입력 단위는 5입니다. 실제 돈을 다루거나 베팅을 실행하지 않습니다.")

    values_to_check = [int(st.session_state.pot_units), int(st.session_state.call_units)]
    if st.session_state.betting_mode == "고급":
        values_to_check.extend([int(st.session_state.opponent_bet_units), int(st.session_state.hero_contribution_units)])
    invalid_units = [value for value in values_to_check if not is_five_multiple(value)]
    if invalid_units:
        st.error("Enter non-negative amounts in increments of 5, e.g. 0, 5, 10, 15..." if LANGUAGE == "EN" else "금액은 0 이상, 5 포인트 단위로 입력해 주세요. 예: 0, 5, 10, 15...")

    left, right = st.columns([1, 2])
    with left:
        if st.button(tr("← 이전"), use_container_width=True):
            go_to(3)
    with right:
        if st.button("Analyze my equity →" if LANGUAGE == "EN" else "내 승산 분석하기 →", type="primary", disabled=bool(invalid_units), use_container_width=True):
            try:
                validate_all_cards()
                range_key = DEFAULT_OPPONENT_RANGE_KEY
                result = calculate_equity(
                    st.session_state.hero_cards,
                    st.session_state.community_cards,
                    int(st.session_state.active_opponents),
                    method="monte_carlo",
                    samples=25_000,
                    seed=2026,
                    opponent_range=range_key,
                )
                decision = decision_support(
                    result["equity"],
                    int(st.session_state.pot_units),
                    int(st.session_state.call_units),
                )
                recommendation = recommend_action(
                    result["equity"],
                    int(st.session_state.pot_units),
                    int(st.session_state.call_units),
                    int(st.session_state.active_opponents),
                )
                decision["recommendation"] = recommendation
                current_model_signature = progress_model_signature(
                    int(st.session_state.table_size),
                    int(st.session_state.active_opponents),
                    range_key,
                )
                if (
                    st.session_state.progress_model_signature is None
                    or progress_signature_changed(st.session_state.progress_model_signature, current_model_signature)
                ):
                    # Existing pre-hotfix browser sessions have no signature; their
                    # old points cannot be safely compared to this new series.
                    st.session_state.progress_history = []
                st.session_state.progress_model_signature = current_model_signature
                updated_progress = append_equity_snapshot(
                    st.session_state.progress_history,
                    stage=st.session_state.stage,
                    board_count=len(st.session_state.community_cards),
                    equity=result["equity"],
                    pot_odds=decision["pot_odds"],
                    pot=int(st.session_state.pot_units),
                    call=int(st.session_state.call_units),
                    action=recommendation["action"],
                    sampling_half_width=float(result.get("confidence_interval", {}).get("half_width", 0.0)),
                    samples=int(result.get("samples", 0)) or None,
                )
                st.session_state.progress_history = updated_progress
                record = {
                    "hero_cards": [display_card_label(card) for card in st.session_state.hero_cards],
                    "community_cards": [display_card_label(card) for card in st.session_state.community_cards],
                    "table_size": int(st.session_state.table_size),
                    "active_opponents": int(st.session_state.active_opponents),
                    "street": st.session_state.stage,
                    "pot_units": int(st.session_state.pot_units),
                    "call_units": int(st.session_state.call_units),
                    "quality": "Standard · 25,000회",
                    "seed": 2026,
                    "equity": result,
                    "monte_carlo": result,
                    "exact": None,
                    "decision": decision,
                    "starting_hand_reference": starting_hand_reference(st.session_state.hero_cards),
                    "opponent_range": range_key,
                    "opponent_style": DEFAULT_OPPONENT_MODEL_KO,
                    "equity_history": list(st.session_state.progress_history),
                    "hand_session_id": st.session_state.hand_session_id,
                    "analysis_parameters": {
                        "table_size": int(st.session_state.table_size),
                        "active_opponents": int(st.session_state.active_opponents),
                        "street": st.session_state.stage,
                        "pot_units": int(st.session_state.pot_units),
                        "call_units": int(st.session_state.call_units),
                        "opponent_range": range_key,
                        "samples": 25_000,
                    },
                }
                st.session_state.analysis = record
                st.session_state.saved_record_id = None
                go_to(5)
            except Exception as exc:
                st.error((f"Analysis failed: {exc}" if LANGUAGE == "EN" else f"분석을 진행하지 못했습니다: {exc}"))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 · Results and history
# ─────────────────────────────────────────────────────────────────────────────
elif step == 5:
    analysis = st.session_state.analysis
    if not analysis:
        st.warning(tr("아직 분석 결과가 없습니다. 게임 정보를 입력한 뒤 분석해 주세요."))
        if st.button(tr("게임 정보로 돌아가기"), type="primary", use_container_width=True):
            go_to(4)
    else:
        result = analysis["equity"]
        decision = analysis["decision"]
        st.markdown(f'<div class="step-title">{tr("현재 내 승산은 이 정도예요")}</div>', unsafe_allow_html=True)
        current_range_key = str(analysis.get("opponent_range", DEFAULT_OPPONENT_RANGE_KEY))
        if current_range_key == DEFAULT_OPPONENT_RANGE_KEY:
            result_intro = ("25,000 Monte Carlo deals using one balanced, weighted opponent baseline." if LANGUAGE == "EN"
                            else "중간 범위 기본 모델을 적용해 25,000번 가상으로 카드를 나눠 본 결과입니다.")
        else:
            result_intro = ("This is an earlier analysis created with a previous opponent-range setting." if LANGUAGE == "EN"
                            else "이전 버전의 상대 카드 유형 설정으로 계산했던 과거 분석 결과입니다.")
        st.markdown(f'<div class="step-copy">{escape(result_intro)}</div>', unsafe_allow_html=True)
        render_table("Cards used in analysis" if LANGUAGE == "EN" else "분석에 사용한 카드")

        top = st.columns(3)
        metrics = [
            (tr("내가 가져갈 것으로 기대되는 팟 비율"), f"{result['equity'] * 100:.2f}%"),
            (tr("내가 이길 확률"), f"{result['strict_win'] * 100:.2f}%"),
            (tr("비길 확률"), f"{result['tie'] * 100:.2f}%"),
        ]
        for col, (label, value) in zip(top, metrics):
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)
        st.caption(tr("질 확률: **{loss:.2f}%** · 여기서 ‘팟 비율’은 무승부일 때 나눠 받는 몫까지 포함한 기대값.", loss=result['strict_loss'] * 100))

        # Explain simulation precision in the primary result view, not only in
        # the advanced-methodology expander. A 95% Hoeffding bound is a
        # conservative distribution-free bound conditional on the model.
        ci = result.get("confidence_interval", {})
        if result.get("method") == "monte_carlo":
            margin_pp = float(ci.get("half_width", 0.0)) * 100
            ci_low_pp = float(ci.get("equity_low", result["equity"])) * 100
            ci_high_pp = float(ci.get("equity_high", result["equity"])) * 100
            if LANGUAGE == "EN":
                sampling_html = (
                    f'<div class="sampling-card"><div class="sampling-kicker">MONTE CARLO · {int(result["samples"]):,} SIMULATED DEALS</div>'
                    f'<div class="sampling-main">Conservative 95% sampling-error bound <strong>±{margin_pp:.2f} pp</strong></div>'
                    f'<div class="sampling-range">Estimated equity {result["equity"] * 100:.2f}% · Bound {ci_low_pp:.2f}%–{ci_high_pp:.2f}%</div>'
                    '<div class="sampling-note">This is not a 95% chance that the recommendation is correct. It covers random simulation error only, assuming the selected opponent model is appropriate; it does not cover model mismatch.</div></div>'
                )
            else:
                sampling_html = (
                    f'<div class="sampling-card"><div class="sampling-kicker">MONTE CARLO · 가상 분배 {int(result["samples"]):,}회</div>'
                    f'<div class="sampling-main">보수적 95% 표본 오차 한계 <strong>±{margin_pp:.2f}%p</strong></div>'
                    f'<div class="sampling-range">추정 승산 {result["equity"] * 100:.2f}% · 95% 구간 {ci_low_pp:.2f}%–{ci_high_pp:.2f}%</div>'
                    '<div class="sampling-note">이 수치는 추천이 95% 확률로 정답이라는 뜻이 아닙니다. 선택한 상대 모델이 적절하다는 조건에서 무작위 시뮬레이션 표본 오차만 나타내며, 상대 가정 자체가 실제와 다를 때의 오차는 포함하지 않습니다.</div></div>'
                )
            st.markdown(sampling_html, unsafe_allow_html=True)
        elif result.get("method") == "exact_enumeration":
            st.markdown(
                '<div class="sampling-card"><div class="sampling-kicker">EXACT ENUMERATION</div>'
                + (f'<div class="sampling-main">Exact calculation · {int(result["samples"]):,} states</div><div class="sampling-note">No Monte Carlo sampling error for the enumerated states.</div>' if LANGUAGE == "EN"
                   else f'<div class="sampling-main">전수 계산 · {int(result["samples"]):,}개 상태</div><div class="sampling-note">가능한 상태를 모두 계산한 범위에서는 Monte Carlo 표본 오차가 없습니다.</div>')
                + '</div>', unsafe_allow_html=True
            )

        st.markdown(
            f'<div class="chart-section-head"><span class="chart-section-index">01</span><span class="chart-section-title">{escape(tr("승산 흐름"))}</span></div>'
            f'<div class="chart-section-subtitle">{escape(tr("초록 선은 내 승산, 주황 선은 지금 콜하려면 필요한 최소 승산입니다."))}</div>',
            unsafe_allow_html=True,
        )
        progress = list(st.session_state.progress_history or analysis.get("equity_history", []))
        chart_rows = build_progress_chart_rows(progress)
        if chart_rows:
            stage_labels_en = {"시작 전": "Preflop", "플랍": "Flop", "턴": "Turn", "리버": "River"}
            labels = []
            for row in chart_rows:
                stage_name = stage_labels_en.get(row["stage"], row["stage"]) if LANGUAGE == "EN" else row["stage"]
                update_number = int(row.get("stage_update", 1))
                if update_number > 1:
                    suffix = f" · bet update {update_number - 1}" if LANGUAGE == "EN" else f" · 베팅 변경 {update_number - 1}"
                    stage_name += suffix
                labels.append(stage_name)
            customdata = [
                [stage_labels_en.get(row["stage"], row["stage"]) if LANGUAGE == "EN" else row["stage"], row["pot_units"], row["call_units"], row["action"]]
                for row in chart_rows
            ]
            equity_hover = (
                "<b>%{x}</b><br>Your equity: %{y:.2f}%<br>Stage: %{customdata[0]}"
                "<br>Pot: %{customdata[1]:,} points<br>Additional call: %{customdata[2]:,} points"
                "<br>Suggested action: %{customdata[3]}<extra></extra>"
                if LANGUAGE == "EN" else
                "<b>%{x}</b><br>내 승산: %{y:.2f}%<br>단계: %{customdata[0]}"
                "<br>팟: %{customdata[1]:,} 포인트<br>추가 콜: %{customdata[2]:,} 포인트"
                "<br>추천: %{customdata[3]}<extra></extra>"
            )
            pot_odds_hover = (
                "<b>%{x}</b><br>Equity needed to call: %{y:.2f}%<br>Stage: %{customdata[0]}"
                "<br>Pot: %{customdata[1]:,} points<br>Additional call: %{customdata[2]:,} points"
                "<br>Suggested action: %{customdata[3]}<extra></extra>"
                if LANGUAGE == "EN" else
                "<b>%{x}</b><br>콜에 필요한 승산: %{y:.2f}%<br>단계: %{customdata[0]}"
                "<br>팟: %{customdata[1]:,} 포인트<br>추가 콜: %{customdata[2]:,} 포인트"
                "<br>추천: %{customdata[3]}<extra></extra>"
            )
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=labels,
                y=[row["equity_low_pct"] for row in chart_rows],
                mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                hoverinfo="skip",
                showlegend=False,
                name="Equity lower bound" if LANGUAGE == "EN" else "승산 하한",
            ))
            fig.add_trace(go.Scatter(
                x=labels,
                y=[row["equity_high_pct"] for row in chart_rows],
                mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                fill="tonexty",
                fillcolor=PLOT_THEME["green_fill"],
                name="Equity sampling range" if LANGUAGE == "EN" else "승산 표본 오차 범위",
                customdata=[[row["equity_low_pct"], row["equity_high_pct"], row["samples"]] for row in chart_rows],
                hovertemplate=("<b>%{x}</b><br>95% sampling range: %{customdata[0]:.2f}%–%{customdata[1]:.2f}%<br>Samples: %{customdata[2]:,}<extra></extra>" if LANGUAGE == "EN"
                               else "<b>%{x}</b><br>95% 표본 오차 범위: %{customdata[0]:.2f}%–%{customdata[1]:.2f}%<br>표본: %{customdata[2]:,}회<extra></extra>"),
            ))
            fig.add_trace(go.Scatter(
                x=labels,
                y=[row["equity_pct"] for row in chart_rows],
                name=tr("내 승산"),
                mode="lines+markers",
                line={"color": PLOT_THEME["green"], "width": 3.2, "shape": "spline"},
                marker={"size": 9, "color": PLOT_THEME["green"], "line": {"color": PLOT_THEME["surface"], "width": 2}},
                fill="tozeroy",
                fillcolor=PLOT_THEME["green_fill"],
                customdata=customdata,
                hovertemplate=equity_hover,
            ))
            fig.add_trace(go.Scatter(
                x=labels,
                y=[row["pot_odds_pct"] for row in chart_rows],
                name=tr("콜에 필요한 승산"),
                mode="lines+markers",
                line={"color": PLOT_THEME["amber"], "width": 3, "dash": "dash"},
                marker={"size": 8, "color": PLOT_THEME["amber"], "symbol": "diamond"},
                customdata=customdata,
                hovertemplate=pot_odds_hover,
            ))
            fig.update_layout(
                template=PLOT_THEME["template"],
                height=370,
                margin={"l": 16, "r": 18, "t": 28, "b": 58},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=PLOT_THEME["surface"],
                font={"family": "-apple-system, BlinkMacSystemFont, sans-serif", "color": PLOT_THEME["text"], "size": 12},
                hovermode="x unified",
                hoverlabel={"bgcolor": PLOT_THEME["hover_bg"], "bordercolor": PLOT_THEME["border"], "font": {"color": PLOT_THEME["text"], "size": 12}},
                legend={"orientation": "h", "y": 1.14, "x": 0.02, "title": {"text": ""}, "font": {"color": PLOT_THEME["text"]}},
                xaxis={"title": tr("핸드 진행 기록"), "showgrid": False, "tickangle": 0, "linecolor": PLOT_THEME["axis"], "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}},
                yaxis={"title": tr("확률"), "range": [0, 100], "dtick": 20, "ticksuffix": "%", "gridcolor": PLOT_THEME["grid"], "zeroline": False, "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}},
            )
            with st.container(border=True):
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
            current_cols = st.columns(2)
            current_cols[0].metric(tr("현재 내 승산"), f"{result['equity'] * 100:.2f}%")
            current_cols[1].metric(tr("현재 콜에 필요한 승산"), f"{decision['pot_odds'] * 100:.2f}%")
            st.caption(tr("새 공용 카드가 열리면 내 승산이 다시 계산됩니다. 베팅만 바꾸면 내 승산은 보통 그대로지만, 콜에 필요한 승산은 바뀝니다. 그래프 점에 마우스를 올리면 당시 팟과 콜 금액도 볼 수 있어요."))

            # Put the values users ask about directly below the trend chart:
            # stage, equity, call threshold, pot, call and recommended action.
            history_table_rows = []
            for label, row in zip(labels, chart_rows):
                action_value = row["action"]
                if LANGUAGE == "EN":
                    action_value = {"CHECK": "Check", "BET": "Bet", "CALL": "Call", "FOLD": "Fold", "RAISE": "Raise", "MARGINAL": "Caution"}.get(action_value, action_value)
                    history_table_rows.append({
                        "Stage": label, "Equity": f"{row['equity_pct']:.2f}%",
                        "Call threshold": f"{row['pot_odds_pct']:.2f}%",
                        "Pot": row["pot_units"], "Additional call": row["call_units"],
                        "Suggested move": action_value,
                    })
                else:
                    action_value = {"CHECK": "체크", "BET": "베팅", "CALL": "콜", "FOLD": "폴드", "RAISE": "레이즈", "MARGINAL": "주의"}.get(action_value, action_value)
                    history_table_rows.append({
                        "단계": label, "내 승산": f"{row['equity_pct']:.2f}%",
                        "콜 필요 승산": f"{row['pot_odds_pct']:.2f}%",
                        "팟": row["pot_units"], "추가 콜": row["call_units"],
                        "추천 무브": action_value,
                    })
            st.dataframe(pd.DataFrame(history_table_rows), use_container_width=True, hide_index=True)

            # A second chart makes pot size and the amount still required to call
            # visible, rather than leaving them only in hover tooltips.
            pot_call_fig = go.Figure()
            pot_call_fig.add_trace(go.Bar(
                x=labels, y=[row["pot_units"] for row in chart_rows],
                name="Pot" if LANGUAGE == "EN" else "팟",
                marker_color=PLOT_THEME["green"],
                text=[f"{value:,}" for value in [row["pot_units"] for row in chart_rows]],
                textposition="auto",
                hovertemplate=("%{x}<br>Pot: %{y:,} points<extra></extra>" if LANGUAGE == "EN" else "%{x}<br>팟: %{y:,} 포인트<extra></extra>"),
            ))
            pot_call_fig.add_trace(go.Bar(
                x=labels, y=[row["call_units"] for row in chart_rows],
                name="Additional call" if LANGUAGE == "EN" else "추가 콜",
                marker_color=PLOT_THEME["amber"],
                text=[f"{value:,}" for value in [row["call_units"] for row in chart_rows]],
                textposition="auto",
                hovertemplate=("%{x}<br>Additional call: %{y:,} points<extra></extra>" if LANGUAGE == "EN" else "%{x}<br>추가 콜: %{y:,} 포인트<extra></extra>"),
            ))
            pot_call_fig.update_layout(
                template=PLOT_THEME["template"], barmode="group", height=295,
                margin={"l": 14, "r": 18, "t": 26, "b": 52},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_THEME["surface"],
                font={"family": "-apple-system, BlinkMacSystemFont, sans-serif", "color": PLOT_THEME["text"], "size": 12},
                hoverlabel={"bgcolor": PLOT_THEME["hover_bg"], "bordercolor": PLOT_THEME["border"], "font": {"color": PLOT_THEME["text"]}},
                legend={"orientation": "h", "y": 1.14, "x": 0.02, "font": {"color": PLOT_THEME["text"]}},
                xaxis={"showgrid": False, "tickfont": {"color": PLOT_THEME["muted"]}, "linecolor": PLOT_THEME["axis"]},
                yaxis={"title": "Points" if LANGUAGE == "EN" else "포인트", "rangemode": "tozero", "gridcolor": PLOT_THEME["grid"], "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}},
            )
            st.markdown(
                f'<div class="chart-section-head"><span class="chart-section-index">02</span><span class="chart-section-title">{escape("Pot and additional call" if LANGUAGE == "EN" else "단계별 팟과 추가 콜")}</span></div>'
                f'<div class="chart-section-subtitle">{escape("Compare the pot already in play with the extra amount needed to continue." if LANGUAGE == "EN" else "현재 팟과 다음 행동을 위해 추가로 필요한 금액을 비교합니다.")}</div>',
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.plotly_chart(pot_call_fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        else:
            st.info(tr("첫 분석 결과입니다. 다음 카드가 공개되거나 베팅 정보를 바꾸고 다시 분석하면 그래프가 쌓입니다."))

        # Show that Monte Carlo is a repeated-sampling procedure using the real
        # run's cumulative equity path and final win/tie/loss counts.
        convergence = result.get("convergence", [])
        if convergence:
            st.markdown(
                f'<div class="chart-section-head"><span class="chart-section-index">03</span><span class="chart-section-title">{escape("Monte Carlo convergence" if LANGUAGE == "EN" else "Monte Carlo 수렴 과정")}</span></div>'
                f'<div class="chart-section-subtitle">{escape("See how the estimated equity settles as more simulated deals are added." if LANGUAGE == "EN" else "가상 카드 분배가 늘어날수록 승산 추정치가 안정되는 과정을 보여줍니다.")}</div>',
                unsafe_allow_html=True,
            )
            sample_x = [int(point["samples"]) for point in convergence]
            equity_y = [float(point["equity"]) * 100 for point in convergence]
            lower_y = [float(point["equity_low"]) * 100 for point in convergence]
            upper_y = [float(point["equity_high"]) * 100 for point in convergence]
            convergence_fig = go.Figure()
            # Draw a pointwise confidence band that narrows as Monte Carlo
            # samples accumulate, instead of stretching the final interval
            # across the entire history (which would misstate early uncertainty).
            convergence_fig.add_trace(go.Scatter(
                x=sample_x, y=lower_y, mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                hoverinfo="skip", showlegend=False,
                name="95% lower bound",
            ))
            convergence_fig.add_trace(go.Scatter(
                x=sample_x, y=upper_y, mode="lines",
                line={"color": "rgba(0,0,0,0)", "width": 0},
                fill="tonexty", fillcolor=PLOT_THEME["green_fill"],
                name="95% interval" if LANGUAGE == "EN" else "지점별 95% 구간",
                customdata=list(zip(lower_y, upper_y)),
                hovertemplate=("Samples: %{x:,}<br>95% interval: %{customdata[0]:.2f}%–%{customdata[1]:.2f}%<extra></extra>" if LANGUAGE == "EN"
                               else "시뮬레이션: %{x:,}회<br>지점별 95% 구간: %{customdata[0]:.2f}%–%{customdata[1]:.2f}%<extra></extra>"),
            ))
            convergence_fig.add_trace(go.Scatter(
                x=sample_x, y=equity_y, mode="lines",
                name="Running equity" if LANGUAGE == "EN" else "누적 승산",
                line={"color": PLOT_THEME["green"], "width": 3.1, "shape": "spline"},
                marker={"size": 4, "color": PLOT_THEME["green"]},
                hovertemplate=("Samples: %{x:,}<br>Running equity: %{y:.2f}%<extra></extra>" if LANGUAGE == "EN"
                               else "시뮬레이션 횟수: %{x:,}회<br>누적 승산: %{y:.2f}%<extra></extra>"),
            ))
            convergence_fig.add_trace(go.Scatter(
                x=[sample_x[-1]], y=[equity_y[-1]], mode="markers",
                marker={"size": 13, "color": PLOT_THEME["amber"], "line": {"color": PLOT_THEME["surface"], "width": 2}},
                name="Final estimate" if LANGUAGE == "EN" else "최종 추정치",
                hovertemplate=("Final estimate: %{y:.2f}%<extra></extra>" if LANGUAGE == "EN" else "최종 추정 승산: %{y:.2f}%<extra></extra>"),
                showlegend=False,
            ))
            convergence_fig.add_hline(
                y=result["equity"] * 100,
                line_dash="dash", line_color=PLOT_THEME["amber"], line_width=1.8,
                annotation_text=(f"Final {result['equity'] * 100:.2f}%" if LANGUAGE == "EN" else f"최종 {result['equity'] * 100:.2f}%"),
                annotation_position="bottom right",
                annotation_font_color=PLOT_THEME["text"],
            )
            final_equity_pct = float(result["equity"]) * 100
            final_half_width_pp = float(result.get("confidence_interval", {}).get("half_width", 0.0)) * 100
            # The first checkpoints have extremely wide bounds. Zoom around the
            # final estimate so the running line and the final ±0.86pp band are
            # readable; early bounds may extend beyond the visible plot window.
            convergence_radius = max(5.0, final_half_width_pp * 1.25)
            convergence_y_range = [
                max(0.0, final_equity_pct - convergence_radius),
                min(100.0, final_equity_pct + convergence_radius),
            ]
            convergence_fig.update_layout(
                template=PLOT_THEME["template"], height=365,
                margin={"l": 16, "r": 18, "t": 30, "b": 56},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_THEME["surface"],
                font={"family": "-apple-system, BlinkMacSystemFont, sans-serif", "color": PLOT_THEME["text"], "size": 12},
                hoverlabel={"bgcolor": PLOT_THEME["hover_bg"], "bordercolor": PLOT_THEME["border"], "font": {"color": PLOT_THEME["text"]}},
                showlegend=False,
                uirevision="poker-monte-carlo-v1026",
                xaxis={"title": "Simulated deals" if LANGUAGE == "EN" else "가상 카드 분배 횟수", "rangemode": "tozero", "gridcolor": PLOT_THEME["grid"], "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}, "zeroline": False},
                yaxis={"title": "Estimated equity" if LANGUAGE == "EN" else "추정 승산", "ticksuffix": "%", "gridcolor": PLOT_THEME["grid"], "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}, "range": convergence_y_range, "zeroline": False},
            )
            counts = result.get("outcome_counts", {})
            outcome_labels = ["Win", "Tie", "Loss"] if LANGUAGE == "EN" else ["승리", "무승부", "패배"]
            outcome_values = [int(counts.get("strict_win", 0)), int(counts.get("tie", 0)), int(counts.get("strict_loss", 0))]
            mc_col, outcome_col = st.columns([3, 2])
            with mc_col:
                with st.container(border=True):
                    st.plotly_chart(convergence_fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
            with outcome_col:
                outcome_percentages = [value / max(1, int(result["samples"])) * 100 for value in outcome_values]
                outcome_fig = go.Figure(go.Bar(
                    x=outcome_percentages,
                    y=outcome_labels,
                    orientation="h",
                    marker={"color": [PLOT_THEME["green"], PLOT_THEME["blue"], PLOT_THEME["red"]],
                            "line": {"color": PLOT_THEME["surface"], "width": 1}},
                    text=[f"{pct:.1f}%  ·  {count:,}" for pct, count in zip(outcome_percentages, outcome_values)],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=outcome_values,
                    hovertemplate=("%{y}<br>%{x:.2f}%<br>%{customdata:,} simulated deals<extra></extra>" if LANGUAGE == "EN"
                                   else "%{y}<br>%{x:.2f}%<br>가상 분배 %{customdata:,}회<extra></extra>"),
                ))
                outcome_fig.update_layout(
                    template=PLOT_THEME["template"], height=285,
                    margin={"l": 12, "r": 16, "t": 24, "b": 38},
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_THEME["surface"],
                    font={"family": "-apple-system, BlinkMacSystemFont, sans-serif", "color": PLOT_THEME["text"], "size": 12},
                    hoverlabel={"bgcolor": PLOT_THEME["hover_bg"], "bordercolor": PLOT_THEME["border"], "font": {"color": PLOT_THEME["text"]}},
                    showlegend=False,
                    xaxis={"title": "Share of simulations" if LANGUAGE == "EN" else "전체 시뮬레이션 중 비율", "range": [0, 112], "ticksuffix": "%", "dtick": 25, "gridcolor": PLOT_THEME["grid"], "tickfont": {"color": PLOT_THEME["muted"]}, "title_font": {"color": PLOT_THEME["muted"]}},
                    yaxis={"autorange": "reversed", "tickfont": {"color": PLOT_THEME["text"]}},
                )
                st.markdown(
                    f'<div class="chart-section-head"><span class="chart-section-index">04</span><span class="chart-section-title">{escape("Outcomes" if LANGUAGE == "EN" else "결과 분포")}</span></div>'
                    f'<div class="chart-section-subtitle">{escape("Count of wins, ties and losses in this run." if LANGUAGE == "EN" else "이번 시뮬레이션에서 승리·무승부·패배가 나온 횟수입니다.")}</div>',
                    unsafe_allow_html=True,
                )
                with st.container(border=True):
                    st.plotly_chart(outcome_fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
            st.caption(
                "Win/tie/loss counts come from this exact Monte Carlo run. The convergence chart is zoomed around the final estimate for readability; early wide bounds can extend beyond the visible y-axis. The shaded band measures sampling error, not opponent-model accuracy." if LANGUAGE == "EN"
                else "승리·무승부·패배 수는 이번 Monte Carlo 실행에서 실제로 나온 표본 횟수입니다. 수렴 그래프는 마지막 추정치 주변을 확대해 보여 주므로 초기의 넓은 오차 범위 일부는 세로축 밖에 있을 수 있습니다. 음영은 표본추출 오차만 나타내며 상대 모델 가정의 정확도를 보장하지는 않습니다."
            )

        recommendation = decision.get("recommendation") or recommend_action(
            result["equity"], int(analysis.get("pot_units", 0)),
            int(analysis.get("call_units", 0)), int(analysis.get("active_opponents", 1))
        )
        action = recommendation["action"]
        if LANGUAGE == "EN":
            action_display = {
                "CHECK": ("CHECK", "Check without adding more points and see the next card."),
                "BET": ("BET", "No bet is currently facing you. A small bet is suggested by the simplified model."),
                "CALL": ("CALL", "Your estimated equity is above the break-even equity required to call."),
                "FOLD": ("FOLD", "Your estimated equity is below the break-even equity required to call."),
                "RAISE": ("RAISE", "The simplified model sees a strong equity edge and suggests raising after matching the call."),
                "MARGINAL": ("MARGINAL · CAUTION", "The difference between calling and folding is small. More information is needed."),
            }
        else:
            action_display = {
                "CHECK": ("CHECK · 체크", "지금은 추가 베팅하지 않고 다음 카드를 보는 쪽을 추천합니다."),
                "BET": ("BET · 베팅", "상대가 아직 베팅하지 않았습니다. 현재 계산상 작은 베팅으로 주도권을 잡는 선택을 제안합니다."),
                "CALL": ("CALL · 콜", "현재 계산상 콜에 필요한 승산보다 내 승산이 높아 콜을 제안합니다."),
                "FOLD": ("FOLD · 폴드", "현재 계산상 콜에 필요한 승산에 미치지 못해 추가 투자를 멈추는 편을 제안합니다."),
                "RAISE": ("RAISE · 레이즈", "현재 추정 승산이 충분히 높아 콜을 맞춘 뒤 추가로 올리는 선택을 후보로 제안합니다."),
                "MARGINAL": ("경계 상황 · 신중", "콜과 폴드의 계산 차이가 작습니다. 정보가 더 필요해 보수적으로 접근하는 편을 권합니다."),
            }
        headline, short_explanation = action_display[action]
        if action == "BET":
            amount_summary = (f"Suggested bet: {recommendation['amount']:,} points" if LANGUAGE == "EN" else f"권장 베팅 금액: {recommendation['amount']:,} 포인트")
        elif action == "RAISE":
            amount_summary = (
                (f"Call {recommendation['call_units']:,} + extra raise {recommendation['extra_raise_units']:,} = total add {recommendation['total_additional_units']:,} points" if LANGUAGE == "EN" else
                 f"콜 {recommendation['call_units']:,} + 추가 레이즈 "
                 f"{recommendation['extra_raise_units']:,} = 지금 추가할 총액 "
                 f"{recommendation['total_additional_units']:,} 포인트")
            )
        elif action == "CALL":
            amount_summary = (f"Suggested call: {recommendation['call_units']:,} points" if LANGUAGE == "EN" else f"권장 콜 금액: {recommendation['call_units']:,} 포인트")
        elif action == "CHECK":
            amount_summary = "Additional bet: 0 points" if LANGUAGE == "EN" else "추가 베팅: 0 포인트"
        elif action == "FOLD":
            amount_summary = "Additional investment: 0 points" if LANGUAGE == "EN" else "추가 투자: 0 포인트"
        else:
            amount_summary = "Review the betting details before entering more points." if LANGUAGE == "EN" else "추가 금액을 정하기 전에 베팅 상황을 다시 확인하세요."
        action_class = action.lower() if action in {"CHECK", "BET", "CALL", "FOLD", "RAISE"} else "check"
        st.subheader(tr("내가 추천하는 무브"))
        st.markdown(
            f'<div class="move-card action-{action_class}">'
            f'<div class="move-kicker">{"Based on current inputs and opponent range" if LANGUAGE == "EN" else "현재 입력과 기본 상대 모델 기준"}</div>'
            f'<div class="move-title">{escape(headline)}</div>'
            f'<div class="move-amount">{escape(amount_summary)}</div>'
            f'<div class="move-description">{escape(short_explanation)}</div></div>',
            unsafe_allow_html=True,
        )
        if LANGUAGE == "EN":
            reason_en = {
                "CHECK": "There is no additional bet to call. The simplified model prefers checking rather than building the pot.",
                "BET": "Estimated equity is above the simplified betting threshold. A bet of about half the current pot is suggested as an aggressive option.",
                "CALL": "Call EV is positive under the current single-decision assumptions. The stronger raise threshold is not met.",
                "FOLD": "Estimated equity is below the minimum equity required to call.",
                "RAISE": "Estimated equity is above the simplified raise threshold and at least 18 percentage points above the call threshold.",
                "MARGINAL": "The simplified call/fold comparison is close. The available information does not support a confident action.",
            }
            sizing_en = {
                "CHECK": "No additional points are required.",
                "BET": f"Suggested bet: about 50% of the current pot, rounded to the nearest 5 points ({recommendation['amount']:,} points).",
                "CALL": f"Match the current additional call amount: {recommendation['call_units']:,} points.",
                "FOLD": "Do not add more points to this hand.",
                "RAISE": f"First call {recommendation['call_units']:,}, then add {recommendation['extra_raise_units']:,} more points. Total additional amount: {recommendation['total_additional_units']:,}.",
                "MARGINAL": "Review the betting details before adding more points.",
            }
            limit_en = "This is a simplified heuristic, not a GTO solution. It does not model fold equity, stack sizes, position, minimum-raise constraints, rake or future betting."
            st.markdown(f"**Why:** {reason_en[action]}")
            st.caption(sizing_en[action])
            st.caption(limit_en)
        else:
            st.markdown(f"**추천 근거:** {recommendation['reason']}")
            st.caption(recommendation["sizing_note"])
            st.caption(recommendation["model_limit"])
        st.caption("This is a simplified decision aid based on your cards, pot, call amount and the fixed balanced opponent baseline. Optimal play may also depend on position, stack sizes, prior actions, opponent responses and future betting." if LANGUAGE == "EN" else "이 추천은 입력한 카드·팟·콜 금액·중간 범위 기본 모델에 근거한 간이 의사결정 보조입니다. 실제 최적 전략은 포지션, 남은 스택, 이전 액션, 상대 반응과 향후 베팅에 따라 달라질 수 있습니다.")

        b1, b2, b3 = st.columns(3)
        b1.metric("Minimum equity to call" if LANGUAGE == "EN" else "콜에 필요한 최소 승산", f"{decision['pot_odds'] * 100:.2f}%")
        b2.metric("Equity edge" if LANGUAGE == "EN" else "내 승산과의 차이", f"{decision['equity_edge'] * 100:+.2f}%p")
        b3.metric("Call EV" if LANGUAGE == "EN" else "콜의 기대값", f"{decision['ev']:+.2f} points" if LANGUAGE == "EN" else f"{decision['ev']:+.2f} 포인트")
        st.caption(tr("기대값은 현재 팟과 추가 콜만 반영한 단일 판단 계산입니다. 이후 베팅, 레이크, 사이드팟, 토너먼트 상황은 반영하지 않습니다."))

        with st.expander(tr("상세 결과와 계산 방식 보기")):
            ci = result["confidence_interval"]
            st.markdown((f"**95% confidence interval:** {ci['equity_low'] * 100:.2f}% – {ci['equity_high'] * 100:.2f}%" if LANGUAGE == "EN" else f"**95% 신뢰구간:** {ci['equity_low'] * 100:.2f}% – {ci['equity_high'] * 100:.2f}%"))
            st.caption("The 95% Hoeffding bound is a conservative, distribution-free sampling-error limit for this fixed model. It is not a 95% probability that the recommendation is correct and does not cover opponent-model mismatch." if LANGUAGE == "EN" else "95% Hoeffding 구간은 현재 모델을 고정했을 때의 보수적인 표본 오차 한계입니다. 추천이 95% 확률로 정답이라는 뜻이 아니며, 상대 모델 가정이 실제와 다른 오차는 포함하지 않습니다.")
            st.markdown((f"**Method:** Monte Carlo · {result['samples']:,} samples" if LANGUAGE == "EN" else f"**계산 방식:** Monte Carlo(가상 카드 분배 반복) · {result['samples']:,}회"))
            analysis_range_key = str(analysis.get("opponent_range", DEFAULT_OPPONENT_RANGE_KEY))
            range_label = LEGACY_RANGE_LABELS_EN.get(analysis_range_key, DEFAULT_OPPONENT_MODEL_EN) if LANGUAGE == "EN" else LEGACY_RANGE_LABELS_KO.get(analysis_range_key, DEFAULT_OPPONENT_MODEL_KO)
            st.markdown((f"**Opponent model:** {range_label}" if LANGUAGE == "EN" else f"**상대 모델:** {range_label}"))
            st.markdown((f"**Active opponents:** {analysis['active_opponents']}" if LANGUAGE == "EN" else f"**상대 수:** {analysis['active_opponents']}명"))
            st.markdown(f"**Model:** {result['opponent_model']}")
            model_description = OPPONENT_MODEL_DESC_EN if LANGUAGE == "EN" else OPPONENT_MODEL_DESC_KO
            if analysis_range_key != DEFAULT_OPPONENT_RANGE_KEY:
                model_description = ("Legacy saved calculation using a previous opponent-range setting." if LANGUAGE == "EN"
                                     else "이전 버전에서 저장한 상대 유형 가정으로 계산된 과거 결과입니다.")
            st.markdown(("**Model description:** " if LANGUAGE == "EN" else "**모델 설명:** ") + model_description)
            st.markdown("The simulation seed is fixed for reproducible comparisons. No additional setup is needed." if LANGUAGE == "EN" else "같은 입력이면 같은 표본 추출 순서로 비교할 수 있도록 내부 계산 설정을 고정했습니다. 별도 설정은 필요하지 않습니다.")

        st.divider()
        st.subheader(tr("이 핸드 계속하기"))
        next_key = next_stage(st.session_state.stage)
        continue_col, edit_col = st.columns(2)
        with continue_col:
            if next_key is not None:
                next_label = stage_text(next_key, "label")
                if st.button(tr("다음 단계로 계속 · {label} →", label=next_label), type="primary", use_container_width=True):
                    # Keep hero cards, existing board cards, settings and accumulated history.
                    st.session_state.stage = next_key
                    clear_analysis()
                    st.session_state.step = 3
                    st.rerun()
            else:
                st.success("The river is revealed. This is the final card stage." if LANGUAGE == "EN" else "리버까지 공개됐습니다. 이 핸드는 최종 카드 단계입니다.")
        with edit_col:
            if st.button(tr("베팅 정보 수정 / 다시 분석"), use_container_width=True):
                go_to(4)

        saved_id = st.session_state.saved_record_id
        if st.button(tr("이 핸드 기록 저장"), disabled=saved_id is not None, use_container_width=True):
            try:
                saved = save_hand_record(analysis)
                st.session_state.saved_record_id = saved["record_id"]
                st.success(tr("현재 핸드 진행 상태를 저장했습니다."))
                st.rerun()
            except Exception as exc:
                st.error((f"Could not save: {exc}" if LANGUAGE == "EN" else f"저장하지 못했습니다: {exc}"))
        if saved_id:
            st.success("This hand is saved." if LANGUAGE == "EN" else "현재 핸드 상태가 저장됐습니다.")

        with st.expander("End this hand and start a new one" if LANGUAGE == "EN" else "현재 핸드를 종료하고 새 핸드 시작하기"):
            st.caption("Starting a new hand clears your cards, community cards and equity history." if LANGUAGE == "EN" else "새 핸드를 시작하면 내 카드·공용 카드·승산 변화 기록이 초기화됩니다.")
            if st.button("Start a new hand" if LANGUAGE == "EN" else "새 핸드 시작", key="confirm_new_hand", type="secondary"):
                st.session_state.hero_cards = []
                st.session_state.community_cards = []
                st.session_state.undo_stack = []
                st.session_state.analysis = None
                st.session_state.saved_record_id = None
                st.session_state.progress_history = []
                st.session_state.progress_model_signature = None
                st.session_state.hand_session_id = None
                st.session_state.stage = "flop"
                st.session_state.opponent_style = DEFAULT_OPPONENT_MODEL_KO
                st.session_state.betting_mode = "간편"
                st.session_state.pot_units = 100
                st.session_state.call_units = 30
                st.session_state.opponent_bet_units = 30
                st.session_state.hero_contribution_units = 0
                st.session_state.active_opponents = min(2, int(st.session_state.table_size) - 1)
                st.session_state.step = 0
                go_to(0)

        st.subheader("Saved hand history" if LANGUAGE == "EN" else "저장된 핸드 기록")
        try:
            history = load_history()
            if not history:
                st.caption(tr("아직 저장된 핸드가 없습니다. 위의 ‘이 핸드 기록 저장’을 누르면 여기에 표시됩니다."))
            else:
                rows = []
                for item in reversed(history[-20:]):
                    eq = item.get("equity", {})
                    rows.append(
                        {
                            ("Cards" if LANGUAGE == "EN" else "카드"): " ".join(item.get("hero_cards", [])),
                            ("Board" if LANGUAGE == "EN" else "공용 카드"): " ".join(item.get("community_cards", [])),
                            ("Opponents" if LANGUAGE == "EN" else "상대 수"): item.get("active_opponents", ""),
                            ("Equity" if LANGUAGE == "EN" else "내 팟 비율"): f"{eq.get('equity', 0) * 100:.2f}%",
                            ("Saved at" if LANGUAGE == "EN" else "저장 시각"): item.get("recorded_at", ""),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                json_data = json.dumps(history, ensure_ascii=False, indent=2).encode("utf-8")
                csv_data = history_to_csv(history)
                d1, d2 = st.columns(2)
                d1.download_button("Download JSON" if LANGUAGE == "EN" else "JSON으로 저장", data=json_data, file_name="poker_hand_history.json", mime="application/json", use_container_width=True)
                d2.download_button("Download CSV" if LANGUAGE == "EN" else "CSV로 저장", data=csv_data, file_name="poker_hand_history.csv", mime="text/csv", use_container_width=True)
        except Exception as exc:
            st.error((f"Could not load hand history: {exc}" if LANGUAGE == "EN" else f"핸드 기록을 불러오지 못했습니다: {exc}"))

st.divider()
with st.expander("Poker streets · A quick guide" if LANGUAGE == "EN" else "포커 단계가 헷갈릴 때 · 4단계 설명"):
    if LANGUAGE == "EN":
        st.markdown("""
        1. **Preflop** — Each player has two private cards. No community cards are visible.
        2. **Flop** — Three community cards are revealed together.
        3. **Turn** — A fourth community card is added.
        4. **River** — The fifth and final community card is revealed.

        Make the best five-card hand from your two private cards and the five community cards.
        """)
    else:
        st.markdown("""
        1. **게임 시작 전 (Preflop)** — 각자 자기 카드 2장만 받은 상태예요. 아직 테이블 가운데 공개 카드는 없습니다.
        2. **첫 공개 카드 3장 (Flop)** — 가운데 공용 카드 3장이 한꺼번에 공개됩니다.
        3. **네 번째 카드 공개 (Turn)** — 공용 카드가 한 장 더 놓입니다.
        4. **마지막 카드 공개 (River)** — 다섯 번째 공용 카드가 놓이고, 카드 공개가 끝납니다.

        내 카드 2장과 가운데 공개 카드 5장을 조합해 가장 좋은 5장짜리 패를 만듭니다.
        """)
with st.expander("What this app does and does not calculate" if LANGUAGE == "EN" else "이 앱이 계산하는 것과 계산하지 않는 것"):
    if LANGUAGE == "EN":
        st.markdown("""
        - This is an offline tool for learning card probabilities and comparing a hand's current situation.
        - Monte Carlo estimates outcomes by repeatedly simulating possible card deals.
        - The app uses one balanced weighted opponent baseline. It is an assumption, not observed information about opponents' private cards or behavior.
        - Call EV is a single-decision estimate. It excludes future betting, rake, side pots, stack limits and tournament ICM.
        - No login, poker-account connection, screen monitoring, real money, payments or bet execution.
        - Hand history stores cards and analysis values only; no name or account details are required.
        """)
    else:
        st.markdown("""
        - 이 앱은 오프라인에서 카드 확률을 공부하고 현재 상황을 비교하는 도구입니다.
        - Monte Carlo는 가능한 카드 분배를 반복해서 표본으로 뽑는 계산 방법입니다.
        - 앱은 하나의 중간 범위 기본 모델을 사용합니다. 실제 상대의 카드를 관찰하거나 행동을 학습하지 않는 계산 가정입니다.
        - 현재 콜 기대값은 한 번의 판단만 계산합니다. 이후 베팅, 레이크, 사이드팟, 스택 제한, 토너먼트 ICM은 계산하지 않습니다.
        - 로그인, 포커 계정 연결, 화면 감시, 실제 화폐, 결제, 베팅 실행 기능은 없습니다.
        - 핸드 기록에는 카드와 게임 분석 값만 저장하며 이름·계정 등 개인 정보는 필요하지 않습니다.
        """)
