"""Beginner-oriented hand progression and transparent action heuristics.

These helpers intentionally do not claim to solve full poker strategy. Bet sizing
is a deterministic study heuristic, not a GTO or fold-equity model.
"""
from __future__ import annotations

from typing import Any, Sequence
import math

STAGE_ORDER = ("preflop", "flop", "turn", "river")
STAGE_KOREAN = {
    "preflop": "시작 전",
    "flop": "플랍",
    "turn": "턴",
    "river": "리버",
}



def build_progress_chart_rows(history: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare safe, display-ready values for the Equity / Pot Odds trend chart."""
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(history, start=1):
        stage = item.get("stage")
        if stage not in STAGE_KOREAN:
            raise ValueError("Unknown poker stage in progress history")
        equity = item.get("equity")
        pot_odds = item.get("pot_odds")
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value)) or not 0 <= float(value) <= 1
            for value in (equity, pot_odds)
        ):
            raise ValueError("Progress probabilities must be between 0 and 1")
        pot = item.get("pot", 0)
        call = item.get("call", 0)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (pot, call)):
            raise ValueError("Progress pot and call values must be non-negative integers")
        equity_low = item.get("equity_low", equity)
        equity_high = item.get("equity_high", equity)
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value)) or not 0 <= float(value) <= 1
            for value in (equity_low, equity_high)
        ) or float(equity_low) > float(equity) or float(equity_high) < float(equity):
            raise ValueError("Progress equity bounds must contain the equity estimate")
        rows.append({
            "event": str(item.get("event") or STAGE_KOREAN[stage]),
            "stage": STAGE_KOREAN[stage],
            "stage_update": int(item.get("stage_update", 1)),
            "equity_pct": round(float(equity) * 100, 2),
            "equity_low_pct": round(float(equity_low) * 100, 2),
            "equity_high_pct": round(float(equity_high) * 100, 2),
            "samples": int(item.get("samples") or 0),
            "pot_odds_pct": round(float(pot_odds) * 100, 2),
            "pot_units": pot,
            "call_units": call,
            "action": str(item.get("action", "")),
        })
    return rows


def progress_model_signature(table_size: int, active_opponents: int, opponent_range: str) -> tuple[int, int, str]:
    """Identify the assumptions under which a progress-chart series was built."""
    if isinstance(table_size, bool) or not isinstance(table_size, int) or not 2 <= table_size <= 10:
        raise ValueError("table_size must be an integer from 2 to 10")
    if isinstance(active_opponents, bool) or not isinstance(active_opponents, int) or not 1 <= active_opponents < table_size:
        raise ValueError("active_opponents must be between 1 and table_size - 1")
    if opponent_range not in {"random", "strong", "typical", "loose"}:
        raise ValueError("Unknown opponent range preset")
    return table_size, active_opponents, opponent_range


def progress_signature_changed(previous: tuple[int, int, str] | None, current: tuple[int, int, str]) -> bool:
    """Return True when chart history would mix different table/opponent assumptions."""
    return previous is not None and tuple(previous) != tuple(current)


def next_stage(stage: str) -> str | None:
    if stage not in STAGE_ORDER:
        raise ValueError("Unknown poker stage")
    index = STAGE_ORDER.index(stage)
    return STAGE_ORDER[index + 1] if index + 1 < len(STAGE_ORDER) else None


def _nearest_five(value: float) -> int:
    return max(5, int(round(value / 5.0)) * 5)


def recommend_action(
    equity: float,
    pot: int,
    call: int,
    active_opponents: int,
) -> dict[str, Any]:
    """Return a simple, clearly-labeled action suggestion and sizing.

    When no bet is faced, the legal choices are check or bet (not raise).
    When facing a bet, compare fold/call using single-decision EV, with a
    raise candidate only at a strong estimated equity advantage. The raise
    size is a simple pot/call heuristic; fold equity and future streets are
    not modeled.
    """
    from poker_engine import decision_support

    if isinstance(equity, bool) or not isinstance(equity, (int, float)) or not math.isfinite(float(equity)) or not 0.0 <= float(equity) <= 1.0:
        raise ValueError("equity must be a finite probability between 0 and 1")
    if isinstance(pot, bool) or not isinstance(pot, int) or pot < 0 or pot % 5 != 0:
        raise ValueError("pot must be a non-negative integer in 5-point increments")
    if isinstance(call, bool) or not isinstance(call, int) or call < 0 or call % 5 != 0:
        raise ValueError("call must be a non-negative integer in 5-point increments")
    if isinstance(active_opponents, bool) or not isinstance(active_opponents, int) or not 1 <= active_opponents <= 9:
        raise ValueError("active_opponents must be an integer from 1 to 9")

    baseline = decision_support(float(equity), pot, call)
    if call == 0:
        bet_threshold = min(0.82, 0.64 + 0.035 * (active_opponents - 1))
        if pot > 0 and equity >= bet_threshold:
            bet_units = _nearest_five(pot * 0.50)
            return {
                "action": "BET",
                "amount": bet_units,
                "call_units": 0,
                "extra_raise_units": 0,
                "total_additional_units": bet_units,
                "reason": (
                    f"현재 상대 베팅이 없어 체크 또는 베팅할 수 있습니다. "
                    f"추정 승산이 간이 기준 {bet_threshold * 100:.0f}% 이상이라 "
                    "팟의 약 1/2 베팅을 공격적 후보로 제안합니다."
                ),
                "sizing_note": "현재 팟의 약 50%를 가장 가까운 5 포인트 단위로 반올림했습니다.",
                "model_limit": "상대가 베팅에 폴드할 확률·내 포지션·스택·향후 베팅은 계산하지 않은 간이 후보입니다.",
                "baseline": baseline,
            }
        return {
            "action": "CHECK",
            "amount": 0,
            "call_units": 0,
            "extra_raise_units": 0,
            "total_additional_units": 0,
            "reason": "현재 추가로 맞춰야 할 베팅이 없습니다. 간이 기준상 팟을 키우기보다 체크를 우선 제안합니다.",
            "sizing_note": "추가 포인트 없음.",
            "model_limit": "상대의 체크·베팅 반응과 포지션은 모델링하지 않습니다.",
            "baseline": baseline,
        }

    raise_threshold = min(0.88, 0.68 + 0.035 * (active_opponents - 1))
    strong_edge = baseline["equity_edge"] >= 0.18
    if baseline["ev"] > 0 and equity >= raise_threshold and strong_edge:
        # Amount above the call amount; total immediate addition = call + extra.
        size_base = max(call, min(pot * 0.50, call * 2.0))
        extra_raise = _nearest_five(size_base)
        return {
            "action": "RAISE",
            "amount": extra_raise,
            "call_units": call,
            "extra_raise_units": extra_raise,
            "total_additional_units": call + extra_raise,
            "reason": (
                f"추정 승산이 {raise_threshold * 100:.0f}% 간이 기준을 넘고 "
                "콜 기준 승산보다 18%p 이상 높아 레이즈 후보로 표시했습니다."
            ),
            "sizing_note": "콜 금액을 먼저 맞춘 뒤, 콜 금액과 팟의 약 1/2 중 작은 쪽(단, 최소 콜 금액)을 추가 레이즈하는 간이 규칙입니다.",
            "model_limit": "상대 폴드 확률을 추정하지 않으므로 수학적으로 최적이라고 보장하지 않습니다. 스택·최소 레이즈 규칙·포지션·레이크·향후 베팅은 제외합니다.",
            "baseline": baseline,
        }

    if baseline["action"] == "CALL":
        reason = "현재 단일 콜 계산에서는 콜의 기대값이 양수입니다. 레이즈할 만큼의 강한 우위 기준은 충족하지 않아 콜을 제안합니다."
    elif baseline["action"] == "FOLD":
        reason = "현재 승산이 콜에 필요한 최소 승산보다 낮아 폴드를 제안합니다. 상대 베팅이 있으므로 체크는 선택할 수 없습니다."
    else:
        reason = "콜과 폴드의 계산 차이가 거의 없어 경계 상황입니다. 상대 베팅이 있으므로 체크는 선택할 수 없습니다."
    return {
        "action": baseline["action"],
        "amount": 0,
        "call_units": call,
        "extra_raise_units": 0,
        "total_additional_units": call if baseline["action"] == "CALL" else 0,
        "reason": reason,
        "sizing_note": "레이즈 금액을 제안하지 않습니다. 현재 자료만으로 레이즈의 추가 기대값을 신뢰성 있게 계산할 수 없습니다.",
        "model_limit": "상대 반응·폴드 확률·스택·포지션·향후 베팅은 반영하지 않은 단일 콜/폴드 계산입니다.",
        "baseline": baseline,
    }


def append_equity_snapshot(
    history: Sequence[dict[str, Any]],
    *,
    stage: str,
    board_count: int,
    equity: float,
    pot_odds: float,
    pot: int,
    call: int,
    action: str,
    sampling_half_width: float = 0.0,
    samples: int | None = None,
) -> list[dict[str, Any]]:
    """Append a point when street or bet state changes; de-duplicate exact reruns."""
    if stage not in STAGE_KOREAN:
        raise ValueError("Unknown poker stage")
    for name, value in (("equity", equity), ("pot_odds", pot_odds)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be a finite probability between 0 and 1")
    for name, value in (("board_count", board_count), ("pot", pot), ("call", call)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if board_count not in (0, 3, 4, 5):
        raise ValueError("board_count must be 0, 3, 4, or 5")
    if (isinstance(sampling_half_width, bool) or not isinstance(sampling_half_width, (int, float))
            or not math.isfinite(float(sampling_half_width)) or not 0 <= float(sampling_half_width) <= 1):
        raise ValueError("sampling_half_width must be a finite value between 0 and 1")
    if samples is not None and (isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0):
        raise ValueError("samples must be a positive integer when supplied")
    if pot % 5 != 0 or call % 5 != 0:
        raise ValueError("pot and call must use 5-point increments")

    result = [dict(item) for item in history]
    equity_low = max(0.0, float(equity) - float(sampling_half_width))
    equity_high = min(1.0, float(equity) + float(sampling_half_width))
    signature = (stage, board_count, round(float(equity), 8), round(float(pot_odds), 8), pot, call, action,
                 round(float(sampling_half_width), 8), samples)
    if result:
        last = result[-1]
        previous = (
            last.get("stage"), last.get("board_count"), round(float(last.get("equity", -1)), 8),
            round(float(last.get("pot_odds", -1)), 8), last.get("pot"), last.get("call"), last.get("action"),
            round(float(last.get("sampling_half_width", 0.0)), 8), last.get("samples")
        )
        if signature == previous:
            return result
    stage_update = 1 + sum(1 for item in result if item.get("stage") == stage)
    stage_label = STAGE_KOREAN[stage]
    event = stage_label if stage_update == 1 else f"{stage_label} · 베팅 변경 {stage_update - 1}"
    result.append({
        "event": event,
        "stage": stage,
        "stage_update": stage_update,
        "board_count": board_count,
        "equity": round(float(equity), 8),
        "equity_low": round(equity_low, 8),
        "equity_high": round(equity_high, 8),
        "sampling_half_width": round(float(sampling_half_width), 8),
        "samples": samples,
        "pot_odds": round(float(pot_odds), 8),
        "pot": pot,
        "call": call,
        "action": action,
    })
    return result[-100:]


def truncate_progress_history(history: Sequence[dict[str, Any]], max_board_count: int) -> list[dict[str, Any]]:
    """Keep only snapshots that remain valid after editing the board.

    Removing a turn card should retain preflop/flop records, while removing a
    flop card should retain only preflop records. This is intentionally not a
    blanket reset: the user can edit a later street without erasing valid work.
    """
    if isinstance(max_board_count, bool) or not isinstance(max_board_count, int) or not 0 <= max_board_count <= 5:
        raise ValueError("max_board_count must be an integer from 0 to 5")
    result = []
    for item in history:
        board_count = item.get("board_count")
        if isinstance(board_count, int) and not isinstance(board_count, bool) and board_count <= max_board_count:
            result.append(dict(item))
    # Rebuild clear stage labels after truncation so re-analysis of the same
    # street does not look like a phantom duplicate caused by removed rows.
    stage_counts: dict[str, int] = {}
    for item in result:
        stage = item.get("stage")
        if stage not in STAGE_KOREAN:
            continue
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        item["stage_update"] = stage_counts[stage]
        item["event"] = STAGE_KOREAN[stage] if stage_counts[stage] == 1 else f"{STAGE_KOREAN[stage]} · 베팅 변경 {stage_counts[stage] - 1}"
    return result[-100:]
