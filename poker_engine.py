"""Poker Probability & Decision Assistant v10.2.6 core engine.

Scope: offline Texas Hold'em probability and decision support only.
No account access, personal-data collection, payment, wagering, or bet execution.
"""
from __future__ import annotations

import bisect
import itertools
import math
import random
from collections import Counter
from typing import Any, Iterable, Optional, Sequence

Card = tuple[str, str]
HandResult = tuple[int, tuple[int, ...]]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}
SUIT_INDEX = {s: i for i, s in enumerate(SUITS)}
DECK: tuple[Card, ...] = tuple((r, s) for r in RANKS for s in SUITS)
DEFAULT_EXACT_MAX_STATES = 250_000

# Beginner-friendly opponent presets. These are broad, user-selected assumptions,
# not observations or predictions about a real player's cards.
OPPONENT_RANGE_PRESETS = {
    "random": "무작위 카드",
    "strong": "강한 카드 위주",
    "typical": "일반적인 플레이",
    "loose": "넓은 카드 범위",
}


def _range_combo_weight(pair: Sequence[int], preset: str) -> float:
    """Return a positive preflop-style weight for one two-card combination."""
    if preset == "random":
        return 1.0
    c1, c2 = pair
    r1, r2 = c1 // 4 + 2, c2 // 4 + 2
    high, low = max(r1, r2), min(r1, r2)
    suited = c1 % 4 == c2 % 4
    paired = high == low

    if preset == "strong":
        if paired:
            return 7.0 if high >= 11 else 3.2 if high >= 8 else 0.75
        if suited and high == 14 and low >= 10:
            return 5.5
        if high == 14 and low >= 12:
            return 3.8 if suited else 2.5
        if suited and high >= 11 and low >= 10:
            return 3.2
        if suited and high >= 10 and low >= 9:
            return 1.7
        return 0.06

    if preset == "typical":
        if paired:
            return 4.0 if high >= 10 else 2.0 if high >= 6 else 1.15
        if high == 14:
            return 2.8 if low >= 10 else 2.1 if low >= 7 else 1.2
        if high >= 12 and low >= 10:
            return 2.0 if suited else 1.35
        if suited and high >= 10 and high - low <= 4:
            return 1.35
        if suited and high >= 8 and high - low <= 3:
            return 0.95
        return 0.48

    if preset == "loose":
        base = 1.0
        if paired:
            base += 0.7
        if suited:
            base += 0.35
        if high >= 12:
            base += 0.3
        if low >= 10:
            base += 0.25
        if high - low <= 2:
            base += 0.15
        return base
    raise ValueError("opponent_range must be random, strong, typical, or loose")


def _weighted_pair_sampler(deck: Sequence[int], preset: str):
    """Precompute a blocker-aware weighted two-card sampler for Monte Carlo."""
    candidates = list(itertools.combinations(deck, 2))
    weights = [_range_combo_weight(pair, preset) for pair in candidates]
    cumulative = []
    total = 0.0
    for weight in weights:
        total += weight
        cumulative.append(total)
    if not candidates or total <= 0:
        raise ValueError("No opponent card combinations remain")

    def draw(rng: random.Random, blocked: set[int]) -> tuple[int, int]:
        # Rejection sampling conditions the preset distribution on cards not
        # already visible or dealt to another player.
        for _ in range(5000):
            index = bisect.bisect_left(cumulative, rng.random() * total)
            pair = candidates[min(index, len(candidates) - 1)]
            if pair[0] not in blocked and pair[1] not in blocked:
                return pair
        raise RuntimeError("Could not sample a non-conflicting opponent hand")

    return draw


def card_to_int(card: Card) -> int:
    if not isinstance(card, (tuple, list)) or len(card) != 2:
        raise ValueError(f"Invalid card: {card!r}")
    rank, suit = str(card[0]).upper(), str(card[1])
    if rank == "10":
        rank = "T"
    if rank not in RANK_VALUE or suit not in SUIT_INDEX:
        raise ValueError(f"Invalid card: {card!r}")
    return (RANK_VALUE[rank] - 2) * 4 + SUIT_INDEX[suit]


def int_to_card(value: int) -> Card:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 52:
        raise ValueError("Card integer must be in [0, 51]")
    return RANKS[value // 4], SUITS[value % 4]


def cards_to_ints(cards: Sequence[Card]) -> list[int]:
    return [card_to_int(c) for c in cards]


def card_label(card: Card) -> str:
    return f"{card[0]}{card[1]}"


def validate_cards(hole_cards: Sequence[Card], community: Sequence[Card]) -> None:
    if len(hole_cards) != 2:
        raise ValueError("Exactly two player hole cards are required.")
    if len(community) not in (0, 3, 4, 5):
        raise ValueError("Community cards must be 0, 3, 4, or 5 cards (preflop/flop/turn/river).")
    all_cards = list(hole_cards) + list(community)
    ints = cards_to_ints(all_cards)
    if len(ints) != len(set(ints)):
        raise ValueError("Duplicate cards are not allowed.")


def _straight_high(ranks: Iterable[int]) -> Optional[int]:
    values = set(ranks)
    if 14 in values:
        values.add(1)
    for high in range(14, 4, -1):
        if all(r in values for r in range(high - 4, high + 1)):
            return high
    return None


def evaluate_five(cards: Sequence[int]) -> HandResult:
    """Evaluate exactly five valid, distinct card integers.

    Category ordering: 0 high-card ... 8 straight-flush.
    """
    if len(cards) != 5:
        raise ValueError("evaluate_five requires exactly five cards")
    if any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < 52 for c in cards):
        raise ValueError("evaluate_five cards must be integers in [0, 51]")
    if len(set(cards)) != 5:
        raise ValueError("evaluate_five requires five distinct cards")
    ranks = [c // 4 + 2 for c in cards]
    suits = [c % 4 for c in cards]
    counts = Counter(ranks)
    groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    is_flush = len(set(suits)) == 1
    straight = _straight_high(ranks)
    if is_flush and straight:
        return 8, (straight,)
    if groups[0][0] == 4:
        quad = groups[0][1]
        kicker = max(r for r in ranks if r != quad)
        return 7, (quad, kicker)
    if groups[0][0] == 3 and groups[1][0] == 2:
        return 6, (groups[0][1], groups[1][1])
    if is_flush:
        return 5, tuple(sorted(ranks, reverse=True))
    if straight:
        return 4, (straight,)
    if groups[0][0] == 3:
        trip = groups[0][1]
        kickers = sorted((r for r in ranks if r != trip), reverse=True)
        return 3, (trip, *kickers[:2])
    pairs = sorted((r for r, n in counts.items() if n == 2), reverse=True)
    if len(pairs) >= 2:
        kicker = max(r for r in ranks if r not in pairs[:2])
        return 2, (pairs[0], pairs[1], kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((r for r in ranks if r != pair), reverse=True)
        return 1, (pair, *kickers[:3])
    return 0, tuple(sorted(ranks, reverse=True))


def best_hand_from_seven(cards: Sequence[int]) -> HandResult:
    """Evaluate best five-card hand from 5-7 valid, distinct card integers."""
    if not 5 <= len(cards) <= 7:
        raise ValueError("best_hand_from_seven requires 5-7 cards")
    if any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < 52 for c in cards):
        raise ValueError("best_hand_from_seven cards must be integers in [0, 51]")
    if len(set(cards)) != len(cards):
        raise ValueError("best_hand_from_seven requires distinct cards")
    rank_counts = [0] * 15
    suit_ranks: list[list[int]] = [[], [], [], []]
    ranks: list[int] = []
    for c in cards:
        if not isinstance(c, int) or not 0 <= c < 52:
            raise ValueError("Invalid card integer")
        rank = c // 4 + 2
        suit = c % 4
        rank_counts[rank] += 1
        suit_ranks[suit].append(rank)
        ranks.append(rank)

    # Straight flush
    for suited in suit_ranks:
        if len(suited) >= 5:
            high = _straight_high(suited)
            if high:
                return 8, (high,)

    quads = [r for r in range(14, 1, -1) if rank_counts[r] == 4]
    if quads:
        q = quads[0]
        return 7, (q, max(r for r in ranks if r != q))

    trips = [r for r in range(14, 1, -1) if rank_counts[r] >= 3]
    pairs_or_better = [r for r in range(14, 1, -1) if rank_counts[r] >= 2]
    if trips:
        trip = trips[0]
        other_pair = next((r for r in pairs_or_better if r != trip), None)
        if other_pair is not None:
            return 6, (trip, other_pair)

    flushes = [sorted(s, reverse=True) for s in suit_ranks if len(s) >= 5]
    if flushes:
        return 5, tuple(max(flushes, key=lambda s: tuple(s))[:5])

    straight = _straight_high(ranks)
    if straight:
        return 4, (straight,)

    if trips:
        trip = trips[0]
        kickers = sorted((r for r in ranks if r != trip), reverse=True)
        return 3, (trip, *kickers[:2])

    pairs = [r for r in range(14, 1, -1) if rank_counts[r] >= 2]
    if len(pairs) >= 2:
        p1, p2 = pairs[:2]
        kicker = max(r for r in ranks if r not in (p1, p2))
        return 2, (p1, p2, kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((r for r in ranks if r != pair), reverse=True)
        return 1, (pair, *kickers[:3])
    return 0, tuple(sorted(set(ranks), reverse=True)[:5])


def classify_showdown(hero_score: HandResult, opponent_scores: Sequence[HandResult]) -> tuple[str, float]:
    best = max([hero_score, *opponent_scores])
    if hero_score < best:
        return "strict_loss", 0.0
    winners = 1 + sum(score == best for score in opponent_scores)
    if winners == 1:
        return "strict_win", 1.0
    return "tie", 1.0 / winners


def _state_count(deck_size: int, cards_to_come: int, unknown_opponents: int) -> Optional[int]:
    if unknown_opponents > 1:
        return None
    board_count = math.comb(deck_size, cards_to_come)
    if unknown_opponents == 0:
        return board_count
    return board_count * math.comb(deck_size - cards_to_come, 2)


def _stats_result(wins: int, ties: int, losses: int, equity_sum: float,
                  equity_sq_sum: float, samples: int, method: str,
                  opponent_model: str) -> dict[str, Any]:
    if samples <= 0:
        raise ValueError("At least one sample is required")
    win_p, tie_p, loss_p = wins / samples, ties / samples, losses / samples
    # Round the three mutually exclusive outcomes while preserving a displayed
    # sum of exactly 1.0 (rounding drift is assigned to the largest bucket).
    rounded = [round(win_p, 8), round(tie_p, 8), round(loss_p, 8)]
    drift = round(1.0 - sum(rounded), 8)
    if drift:
        largest = max(range(3), key=lambda index: rounded[index])
        rounded[largest] = round(rounded[largest] + drift, 8)
    equity = equity_sum / samples
    if method == "exact_enumeration":
        low = high = equity
        half = 0.0
        ci_method = "exact enumeration; zero sampling error"
    else:
        # Distribution-free 95% Hoeffding bound for equity observations in [0, 1].
        # Keep the theoretical half-width unchanged even when the displayed
        # interval is clipped at 0% or 100%; clipping must not imply greater
        # precision than the bound actually provides.
        half = math.sqrt(math.log(2 / 0.05) / (2 * samples))
        low, high = max(0.0, equity - half), min(1.0, equity + half)
        ci_method = "95% Hoeffding bound; sampling uncertainty only"
    return {
        "strict_win": rounded[0],
        "tie": rounded[1],
        "strict_loss": rounded[2],
        "probability_sum": round(sum(rounded), 8),
        "outcome_counts": {"strict_win": int(wins), "tie": int(ties), "strict_loss": int(losses)},
        "equity": round(equity, 8),
        "samples": samples,
        "method": method,
        "opponent_model": opponent_model,
        "convergence": [],
        "confidence_interval": {
            "level": 0.95,
            "equity_low": round(low, 8),
            "equity_high": round(high, 8),
            "half_width": round(half, 8),
            "method": ci_method,
        },
        "model_note": "Opponent cards are sampled from the selected broad range assumption; no real-player behavior is observed or inferred.",
    }


def calculate_equity(
    hole_cards: Sequence[Card], community: Sequence[Card], num_opponents: int,
    *, opponent_holes: Optional[Sequence[Sequence[Card]]] = None,
    method: str = "auto", samples: int = 25_000, seed: Optional[int] = 2026,
    exact_max_states: int = DEFAULT_EXACT_MAX_STATES,
    opponent_range: str = "random",
) -> dict[str, Any]:
    """Calculate showdown outcome probabilities and expected pot share.

    `num_opponents` means opponents still contesting the pot (1-9).
    Known opponent hole cards are optional; unknown opponents are uniform random.
    """
    validate_cards(hole_cards, community)
    if isinstance(num_opponents, bool) or not isinstance(num_opponents, int) or not 1 <= num_opponents <= 9:
        raise ValueError("Active opponents must be an integer from 1 to 9")
    if method not in {"auto", "exact", "monte_carlo"}:
        raise ValueError("method must be auto, exact, or monte_carlo")
    if opponent_range not in OPPONENT_RANGE_PRESETS:
        raise ValueError("opponent_range must be random, strong, typical, or loose")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        raise ValueError("samples must be a positive integer")
    if isinstance(exact_max_states, bool) or not isinstance(exact_max_states, int) or exact_max_states < 1:
        raise ValueError("exact_max_states must be a positive integer")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")

    known = [list(h) for h in (opponent_holes or [])]
    if len(known) > num_opponents:
        raise ValueError("More known opponent hands than active opponents")
    used_cards = list(hole_cards) + list(community)
    for i, hand in enumerate(known):
        if len(hand) != 2:
            raise ValueError(f"Opponent {i + 1} must have exactly two cards")
        used_cards.extend(hand)
    used_ints = cards_to_ints(used_cards)
    if len(used_ints) != len(set(used_ints)):
        raise ValueError("Duplicate cards across hero, board, and opponent hands")

    hero = cards_to_ints(hole_cards)
    board = cards_to_ints(community)
    known_ints = [cards_to_ints(h) for h in known]
    unknown = num_opponents - len(known_ints)
    used_set = set(used_ints)
    deck = [c for c in range(52) if c not in used_set]
    cards_to_come = 5 - len(board)
    draw_required = cards_to_come + 2 * unknown
    if draw_required > len(deck):
        raise ValueError("Not enough unseen cards for this table and board")

    range_label = OPPONENT_RANGE_PRESETS[opponent_range]
    opponent_model = ("uniform_random" if opponent_range == "random" else f"user_weighted_ranges:{opponent_range}") if not known else (
        "known_holes" if unknown == 0 else f"{len(known)} known + {unknown} {range_label}"
    )
    states = _state_count(len(deck), cards_to_come, unknown)
    can_exact = opponent_range == "random" and states is not None and states <= exact_max_states
    if method == "exact" and not can_exact:
        raise ValueError("Exact enumeration is available only for random opponent cards and within the configured state limit")
    use_exact = method == "exact" or (method == "auto" and can_exact)

    wins = ties = losses = 0
    equity_sum = equity_sq_sum = 0.0

    if use_exact:
        board_iter = [()] if cards_to_come == 0 else itertools.combinations(deck, cards_to_come)
        for added_board in board_iter:
            full_board = board + list(added_board)
            hero_score = best_hand_from_seven(hero + full_board)
            remaining = [c for c in deck if c not in added_board]
            if unknown == 0:
                opponent_scores = [best_hand_from_seven(hand + full_board) for hand in known_ints]
                category, share = classify_showdown(hero_score, opponent_scores)
                if category == "strict_win": wins += 1
                elif category == "tie": ties += 1
                else: losses += 1
                equity_sum += share
                equity_sq_sum += share * share
            else:
                for opp_hole in itertools.combinations(remaining, 2):
                    opponent_scores = [best_hand_from_seven(list(opp_hole) + full_board)]
                    opponent_scores.extend(best_hand_from_seven(hand + full_board) for hand in known_ints)
                    category, share = classify_showdown(hero_score, opponent_scores)
                    if category == "strict_win": wins += 1
                    elif category == "tie": ties += 1
                    else: losses += 1
                    equity_sum += share
                    equity_sq_sum += share * share
        total = wins + ties + losses
        return _stats_result(wins, ties, losses, equity_sum, equity_sq_sum, total,
                             "exact_enumeration", opponent_model)

    rng = random.Random(seed)
    weighted_draw = _weighted_pair_sampler(deck, opponent_range) if opponent_range != "random" and unknown else None
    convergence: list[dict[str, float | int]] = []
    checkpoint = max(1, math.ceil(samples / 100))
    for sample_index in range(1, samples + 1):
        if weighted_draw is None:
            drawn = rng.sample(deck, draw_required)
            full_board = board + drawn[:cards_to_come]
            idx = cards_to_come
            opponent_scores: list[HandResult] = []
            for _opp in range(unknown):
                opponent_scores.append(best_hand_from_seven(drawn[idx:idx + 2] + full_board))
                idx += 2
        else:
            added_board = rng.sample(deck, cards_to_come)
            full_board = board + added_board
            blocked = set(hero + full_board)
            opponent_scores = []
            for _opp in range(unknown):
                hand = weighted_draw(rng, blocked)
                blocked.update(hand)
                opponent_scores.append(best_hand_from_seven(list(hand) + full_board))
        opponent_scores.extend(best_hand_from_seven(hand + full_board) for hand in known_ints)
        hero_score = best_hand_from_seven(hero + full_board)
        category, share = classify_showdown(hero_score, opponent_scores)
        if category == "strict_win": wins += 1
        elif category == "tie": ties += 1
        else: losses += 1
        equity_sum += share
        equity_sq_sum += share * share
        if sample_index == 1 or sample_index % checkpoint == 0 or sample_index == samples:
            running_equity = equity_sum / sample_index
            # Pointwise 95% Hoeffding interval for the running mean. The
            # interval narrows with the number of simulated deals and is used
            # to visualize sampling uncertainty at each checkpoint.
            running_half_width = math.sqrt(math.log(2 / 0.05) / (2 * sample_index))
            convergence.append({
                "samples": sample_index,
                # Match the public result precision so the final chart point
                # is exactly equal to the displayed final equity.
                "equity": round(running_equity, 8),
                "equity_low": max(0.0, running_equity - running_half_width),
                "equity_high": min(1.0, running_equity + running_half_width),
                "half_width": running_half_width,
                "strict_win": wins / sample_index,
                "tie": ties / sample_index,
                "strict_loss": losses / sample_index,
            })
    result = _stats_result(wins, ties, losses, equity_sum, equity_sq_sum, samples,
                           "monte_carlo", opponent_model)
    result["convergence"] = convergence
    return result


def pot_odds(pot: float, call: float) -> float:
    _validate_nonnegative_finite("pot", pot)
    _validate_nonnegative_finite("call", call)
    if call == 0:
        return 0.0
    if pot + call == 0:
        raise ValueError("Pot plus call must be positive")
    return call / (pot + call)


def call_ev(equity: float, pot: float, call: float) -> float:
    if not math.isfinite(equity) or not 0 <= equity <= 1:
        raise ValueError("Equity must be between 0 and 1")
    _validate_nonnegative_finite("pot", pot)
    _validate_nonnegative_finite("call", call)
    return equity * pot - (1 - equity) * call


def _validate_nonnegative_finite(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def decision_support(equity: float, pot: float, call: float) -> dict[str, Any]:
    required = pot_odds(pot, call)
    ev = call_ev(equity, pot, call)
    if call == 0:
        action = "CHECK"
        explanation = "No additional amount is required to continue."
    elif ev > 0:
        action = "CALL"
        explanation = "Estimated equity is above break-even pot odds under the selected opponent model."
    elif ev < 0:
        action = "FOLD"
        explanation = "Estimated equity is below break-even pot odds under the selected opponent model."
    else:
        action = "MARGINAL"
        explanation = "The estimated call EV is approximately break-even."
    return {
        "action": action,
        "pot_odds": required,
        "equity": equity,
        "ev": ev,
        "equity_edge": equity - required,
        "explanation": explanation,
        "assumption": "Single decision, no future betting, no rake, and current pot excludes the hero's call.",
    }


def starting_hand_reference(hole_cards: Sequence[Card]) -> dict[str, Any]:
    """Exact preflop class frequencies among 1,326 unordered starting hands."""
    if len(hole_cards) != 2:
        raise ValueError("Exactly two hole cards are required")
    cards = cards_to_ints(hole_cards)
    if cards[0] == cards[1]:
        raise ValueError("Duplicate hole cards")
    r1 = "T" if str(hole_cards[0][0]).upper() == "10" else str(hole_cards[0][0]).upper()
    r2 = "T" if str(hole_cards[1][0]).upper() == "10" else str(hole_cards[1][0]).upper()
    same_rank = RANK_VALUE.get(r1, 0) == RANK_VALUE.get(r2, 0)
    suited = hole_cards[0][1] == hole_cards[1][1]
    total = math.comb(52, 2)
    if same_rank:
        class_name, combos = "Specific pocket pair (e.g. AA)", math.comb(4, 2)
        broad_name, broad_combos = "Any pocket pair", 13 * math.comb(4, 2)
    else:
        class_name, combos = ("Specific suited non-pair (e.g. AKs)", 4) if suited else ("Specific offsuit non-pair (e.g. AKo)", 12)
        broad_name, broad_combos = "This rank matchup (suited + offsuit)", 16
    return {
        "class_name": class_name,
        "class_combinations": combos,
        "class_probability": combos / total,
        "broad_name": broad_name,
        "broad_combinations": broad_combos,
        "broad_probability": broad_combos / total,
        "all_starting_combinations": total,
        "note": "Frequency of receiving this starting-hand class in a random deal; not a win probability.",
    }


def common_preflop_references() -> list[dict[str, Any]]:
    total = math.comb(52, 2)
    # These three rows are mutually exclusive and exhaustive.
    rows = [
        ("Any pocket pair", 78),
        ("Any two non-pair suited cards", 312),
        ("Any two non-pair offsuit cards", 936),
    ]
    return [{"event": name, "combinations": count, "total": total, "probability": count / total}
            for name, count in rows]


def draw_odds_from_outs(outs: int, street: str) -> dict[str, Any]:
    """Exact clean-out hit probability, assuming all outs are live and disjoint."""
    if isinstance(outs, bool) or not isinstance(outs, int):
        raise ValueError("Outs must be an integer")
    max_outs = 47 if street == "flop" else 46 if street == "turn" else -1
    if not 0 <= outs <= max_outs:
        raise ValueError(f"Outs must be an integer from 0 to {max_outs} for {street}")
    if street == "flop":
        denominator = math.comb(47, 2)
        exact = 1 - (math.comb(47 - outs, 2) / denominator) if 47 - outs >= 2 else 1.0
        approximate = min(1.0, outs * 0.04)
        next_card = outs / 47
    elif street == "turn":
        exact = outs / 46
        approximate = min(1.0, outs * 0.02)
        next_card = exact
    else:
        raise ValueError("street must be 'flop' or 'turn'")
    return {
        "outs": outs,
        "street": street,
        "exact_probability": exact,
        "rule_of_2_and_4_approximation": approximate,
        "next_card_probability": next_card,
        "assumption": "All listed outs are clean and each hit produces the target improvement.",
    }


def common_draw_reference_table() -> list[dict[str, Any]]:
    result = []
    for outs, label in [(4, "Gutshot straight draw"), (8, "Open-ended straight draw"),
                        (9, "Flush draw"), (12, "Flush draw + gutshot"),
                        (15, "Open-ended straight + flush draw")]:
        result.append({
            "draw": label,
            "outs": outs,
            "flop_to_river": draw_odds_from_outs(outs, "flop")["exact_probability"],
            "turn_to_river": draw_odds_from_outs(outs, "turn")["exact_probability"],
            "rule_of_4": draw_odds_from_outs(outs, "flop")["rule_of_2_and_4_approximation"],
            "rule_of_2": draw_odds_from_outs(outs, "turn")["rule_of_2_and_4_approximation"],
        })
    return result


def sample_quality_samples(quality: str) -> int:
    values = {"Fast": 5_000, "Standard": 25_000, "Accurate": 75_000}
    if quality not in values:
        raise ValueError("Unknown sample quality")
    return values[quality]
