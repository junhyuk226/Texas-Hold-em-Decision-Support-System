"""Local, privacy-minimizing hand-history persistence for Poker Assistant v10.2.6."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
# Keep hand history local to this checkout. No sibling projects or user folders
# are read or written, which makes the public repository self-contained.
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "hand_history" / "hands.json"

# Deliberately whitelist game-analysis fields; no personal identifiers are stored.
_ALLOWED_FIELDS = (
    "hero_cards", "community_cards", "table_size", "active_opponents",
    "street", "pot_units", "call_units", "quality", "seed", "equity",
    "monte_carlo", "exact", "decision", "starting_hand_reference",
    "analysis_parameters", "opponent_range", "equity_history", "hand_session_id",
)


def _path(path: Optional[str | Path]) -> Path:
    return Path(path).expanduser() if path is not None else DEFAULT_HISTORY_PATH


def load_history(path: Optional[str | Path] = None) -> list[dict[str, Any]]:
    """Load saved records. A missing file is an empty history."""
    target = _path(path)
    if not target.exists():
        return []
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Hand history JSON is invalid: {target}") from exc
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError("Hand history must contain a JSON array of records.")
    return data


def _validate_record(record: dict[str, Any]) -> None:
    """Validate the public hand-history schema before writing any bytes."""
    hero = record.get("hero_cards")
    board = record.get("community_cards")
    if not isinstance(hero, list) or len(hero) != 2 or not all(isinstance(x, str) for x in hero):
        raise ValueError("hero_cards must contain exactly two card labels")
    if not isinstance(board, list) or len(board) not in (0, 3, 4, 5) or not all(isinstance(x, str) for x in board):
        raise ValueError("community_cards must contain 0, 3, 4, or 5 card labels")
    all_cards = hero + board
    if len(all_cards) != len(set(all_cards)):
        raise ValueError("Duplicate cards cannot be saved in hand history")

    for field in ("pot_units", "call_units"):
        if field in record:
            amount = record[field]
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                raise ValueError(f"{field} must be a non-negative integer in 5-point increments")
            if not float(amount).is_integer() or amount < 0 or int(amount) % 5 != 0:
                raise ValueError(f"{field} must be a non-negative integer in 5-point increments")
            record[field] = int(amount)  # Normalize legacy integral floats on write.

    table_size = record.get("table_size")
    active = record.get("active_opponents")
    if table_size is not None:
        if isinstance(table_size, bool) or not isinstance(table_size, int) or not 2 <= table_size <= 10:
            raise ValueError("table_size must be an integer from 2 to 10")
        if active is not None and (isinstance(active, bool) or not isinstance(active, int) or not 1 <= active < table_size):
            raise ValueError("active_opponents must be between 1 and table_size - 1")

    equity = record.get("equity")
    decision = record.get("decision")
    if not isinstance(equity, dict) or not isinstance(decision, dict):
        raise ValueError("equity and decision must be objects")
    value = equity.get("equity")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("equity.equity must be a finite probability between 0 and 1")
    for field in ("strict_win", "tie", "strict_loss"):
        if field in equity:
            probability = equity[field]
            if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError(f"equity.{field} must be a finite probability between 0 and 1")
    if all(field in equity for field in ("strict_win", "tie", "strict_loss")):
        outcome_sum = sum(float(equity[field]) for field in ("strict_win", "tie", "strict_loss"))
        if not math.isclose(outcome_sum, 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("strict_win + tie + strict_loss must equal 1")

    action = decision.get("action")
    if action not in {"CHECK", "CALL", "FOLD", "MARGINAL"}:
        raise ValueError("decision.action must be CHECK, CALL, FOLD, or MARGINAL")
    for field in ("pot_odds", "ev"):
        if field in decision:
            value = decision[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"decision.{field} must be a finite number")

    recommendation = decision.get("recommendation")
    if recommendation is not None:
        if not isinstance(recommendation, dict) or recommendation.get("action") not in {"CHECK", "BET", "CALL", "FOLD", "RAISE", "MARGINAL"}:
            raise ValueError("decision.recommendation.action is invalid")
        for field in ("amount", "call_units", "extra_raise_units", "total_additional_units"):
            if field in recommendation:
                amount = recommendation[field]
                if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 or amount % 5 != 0:
                    raise ValueError(f"decision.recommendation.{field} must be a non-negative integer in 5-point increments")

    equity_history = record.get("equity_history")
    if equity_history is not None and (not isinstance(equity_history, list) or any(not isinstance(point, dict) for point in equity_history)):
        raise ValueError("equity_history must be a list of point objects")


def save_hand_record(
    analysis: dict[str, Any], path: Optional[str | Path] = None
) -> dict[str, Any]:
    """Append one sanitized analysis record using an atomic file replacement."""
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")
    record = {key: analysis[key] for key in _ALLOWED_FIELDS if key in analysis}
    required = ("hero_cards", "community_cards", "equity", "decision")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"analysis is missing required fields: {', '.join(missing)}")

    _validate_record(record)
    record["schema_version"] = 1
    record["record_id"] = uuid.uuid4().hex
    record["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Ensure the data can be represented as portable JSON before touching disk.
    payload = json.dumps(record, ensure_ascii=False, allow_nan=False)

    target = _path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    history = load_history(target)
    history.append(json.loads(payload))
    serialized = json.dumps(history, ensure_ascii=False, indent=2, allow_nan=False)

    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return history[-1]


def history_to_csv(history: list[dict[str, Any]]) -> str:
    """Flatten records to a CSV suitable for spreadsheet review."""
    if not isinstance(history, list):
        raise TypeError("history must be a list")
    fields = [
        "record_id", "hand_session_id", "recorded_at", "hero_cards", "community_cards", "table_size",
        "active_opponents", "street", "pot_units", "call_units", "quality", "seed",
        "equity", "strict_win", "tie", "strict_loss", "method", "opponent_model",
        "samples", "ci_low", "ci_high", "ci_method", "pot_odds", "equity_edge",
        "call_ev", "action", "recommended_action", "recommended_amount_units",
        "recommended_raise_extra_units", "recommended_total_additional_units", "equity_history_json", "opponent_range",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in history:
        eq = record.get("equity") or {}
        ci = eq.get("confidence_interval") or {}
        decision = record.get("decision") or {}
        row = {
            "record_id": record.get("record_id", ""),
            "hand_session_id": record.get("hand_session_id", ""),
            "recorded_at": record.get("recorded_at", ""),
            "hero_cards": " ".join(record.get("hero_cards", [])),
            "community_cards": " ".join(record.get("community_cards", [])),
            "table_size": record.get("table_size", ""),
            "active_opponents": record.get("active_opponents", ""),
            "street": record.get("street", ""),
            "pot_units": record.get("pot_units", ""),
            "call_units": record.get("call_units", ""),
            "quality": record.get("quality", ""),
            "seed": record.get("seed", ""),
            "equity": eq.get("equity", ""),
            "strict_win": eq.get("strict_win", ""),
            "tie": eq.get("tie", ""),
            "strict_loss": eq.get("strict_loss", ""),
            "method": eq.get("method", ""),
            "opponent_model": eq.get("opponent_model", ""),
            "samples": eq.get("samples", ""),
            "ci_low": ci.get("equity_low", ""),
            "ci_high": ci.get("equity_high", ""),
            "ci_method": ci.get("method", ""),
            "pot_odds": decision.get("pot_odds", ""),
            "equity_edge": decision.get("equity_edge", ""),
            "call_ev": decision.get("ev", ""),
            "action": decision.get("action", ""),
            "recommended_action": (decision.get("recommendation") or {}).get("action", ""),
            "recommended_amount_units": (decision.get("recommendation") or {}).get("amount", ""),
            "recommended_raise_extra_units": (decision.get("recommendation") or {}).get("extra_raise_units", ""),
            "recommended_total_additional_units": (decision.get("recommendation") or {}).get("total_additional_units", ""),
            "equity_history_json": json.dumps(record.get("equity_history", []), ensure_ascii=False),
            "opponent_range": record.get("opponent_range", ""),
        }
        writer.writerow(row)
    return output.getvalue()
