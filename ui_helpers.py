"""Pure helpers for the beginner-friendly Poker Assistant wizard."""
from __future__ import annotations

import math
import re
from html import escape
from typing import Iterable, Sequence

from poker_engine import Card, card_label

RANK_INPUT_ORDER = ("A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2")
# Beginner-first picker order follows familiar card rank counting: A, 2 ... K.
RANK_PICKER_OPTIONS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUIT_PICKER_OPTIONS = ("♣ 클럽", "♦ 다이아", "♠ 스페이드", "♥ 하트")
SUIT_PICKER_OPTIONS_EN = ("♣ Club", "♦ Diamond", "♠ Spade", "♥ Heart")
SUIT_PICKER_MAP = {
    "♠ 스페이드": "♠", "♥ 하트": "♥", "♦ 다이아": "♦", "♣ 클럽": "♣",
    "♣ Club": "♣", "♦ Diamond": "♦", "♠ Spade": "♠", "♥ Heart": "♥",
}
SUIT_INPUT_MAP = {
    "S": "♠", "♠": "♠", "ㅅ": "♠",
    "H": "♥", "♥": "♥", "ㅎ": "♥",
    "D": "♦", "♦": "♦", "ㄷ": "♦",
    "C": "♣", "♣": "♣", "ㅋ": "♣",
}
RANK_TOKEN_RE = re.compile(r"^(10|[2-9TJQKA])$", re.IGNORECASE)


def picker_card(rank_label: str, suit_label: str) -> Card:
    """Convert the two dropdown labels into one canonical internal card."""
    if rank_label not in RANK_PICKER_OPTIONS:
        raise ValueError("Select a valid card rank")
    if suit_label not in SUIT_PICKER_MAP:
        raise ValueError("Select a valid card suit")
    rank = "T" if rank_label == "10" else rank_label
    return (rank, SUIT_PICKER_MAP[suit_label])


def _parse_card_pair(first: str, second: str) -> Card | None:
    """Parse one card's rank and suit in either order, including Korean K-key.

    On a Korean keyboard, typing the Latin letter K produces ``ㅋ``. Because
    ``ㅋ`` is also the Korean initial used for Club, context resolves the
    ambiguity: ``ㅋH`` / ``ㅋㅎ`` means K-Heart; ``Aㅋ`` / ``ㅋA`` means
    Ace-Club. A pair of two different suit initials with ``ㅋ`` first is
    interpreted as K plus the second suit, which is a valid, useful shortcut.
    """
    a, b = first.strip().upper(), second.strip().upper()

    # Korean keyboard K + suit (e.g. ㅋㅎ, ㅋH, ㅋㅅ, ㅋㄷ).
    if a == "ㅋ" and b in SUIT_INPUT_MAP:
        rank, suit = "K", SUIT_INPUT_MAP[b]
    # Suit + Korean keyboard K (e.g. ㅎㅋ, Hㅋ).
    elif b == "ㅋ" and a in SUIT_INPUT_MAP:
        rank, suit = "K", SUIT_INPUT_MAP[a]
    elif RANK_TOKEN_RE.fullmatch(a) and b in SUIT_INPUT_MAP:
        rank, suit = a, SUIT_INPUT_MAP[b]
    elif a in SUIT_INPUT_MAP and RANK_TOKEN_RE.fullmatch(b):
        rank, suit = b, SUIT_INPUT_MAP[a]
    else:
        return None
    return ("T" if rank == "10" else rank, suit)


def parse_card_tokens(value: str) -> list[Card]:
    """Parse compact cards in either order, with English/Korean suit shortcuts.

    Examples: AS/SA, Aㅋ/ㅋA, 10D/D10, ㅎJ/Jㅎ, and spaced pairs "A S".
    Suit shortcuts: C/D/S/H or ㅋ/ㄷ/ㅅ/ㅎ, plus suit symbols.
    """
    if not isinstance(value, str):
        raise TypeError("Card input must be text")
    tokens = [token.strip().upper() for token in re.split(r"[\s,;/]+", value.strip()) if token.strip()]
    if not tokens:
        return []

    cards: list[Card] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        parsed: Card | None = None
        # Compact tokens, with rank first or suit first.
        if token.startswith("10"):
            parsed = _parse_card_pair("10", token[2:])
        elif token.endswith("10"):
            parsed = _parse_card_pair(token[:-2], "10")
        elif len(token) == 2:
            parsed = _parse_card_pair(token[0], token[1])

        # Also accept spaced pairs, e.g. "A S", "S A", "10 D", "ㄷ 10".
        if parsed is None and index + 1 < len(tokens):
            parsed = _parse_card_pair(token, tokens[index + 1])
            if parsed is not None:
                index += 1
        if parsed is None:
            raise ValueError(
                f"'{token}' 형식을 읽지 못했습니다. 예: AS 또는 SA, Aㅋ 또는 ㅋA, 10D 또는 D10"
            )
        cards.append(parsed)
        index += 1

    if len(cards) != len(set(cards)):
        raise ValueError("같은 입력 안에 중복 카드가 있습니다.")
    return cards


def card_color(suit: str) -> str:
    return "red" if suit in ("♥", "♦") else "black"


def display_rank(rank: str) -> str:
    """Return a human-facing rank label (the engine stores ten as T)."""
    return "10" if str(rank).upper() in {"T", "10"} else str(rank).upper()


def display_card_label(card: Card) -> str:
    rank, suit = card
    return f"{display_rank(rank)}{suit}"


def card_html(cards: Sequence[Card], empty_text: str, slot_count: int = 0) -> str:
    parts = []
    for rank, suit in cards:
        parts.append(
            f'<div class="p-card {card_color(suit)}"><span>{display_rank(rank)}</span><b>{suit}</b></div>'
        )
    for _ in range(max(0, slot_count - len(cards))):
        parts.append('<div class="p-card empty"><span>?</span><b>＋</b></div>')
    if not parts:
        parts.append(f'<div class="empty-hint">{empty_text}</div>')
    return "".join(parts)


def table_seat_positions(players: int) -> list[tuple[float, float]]:
    """Return opponent seat centers on the upper table arc."""
    if isinstance(players, bool) or not isinstance(players, int) or not 2 <= players <= 10:
        raise ValueError("players must be an integer from 2 to 10")

    opponents = players - 1
    if opponents == 1:
        return [(50.0, 12.0)]
    if opponents == 2:
        return [(25.0, 25.0), (75.0, 25.0)]

    span = 64.0 if opponents == 3 else 68.0 if opponents == 4 else 72.0 if opponents == 5 else 76.0
    left_edge = 50.0 - span / 2.0
    step = span / (opponents - 1)
    positions: list[tuple[float, float]] = []
    for index in range(opponents):
        left = left_edge + step * index
        distance = abs(left - 50.0) / (span / 2.0)
        top = 14.0 + 26.0 * distance * distance
        positions.append((round(left, 2), round(top, 2)))
    return positions


def poker_table_html(
    players: int,
    hero_cards: Sequence[Card],
    community_cards: Sequence[Card],
    board_slots: int = 5,
    subtitle: str = "",
    language: str = "KOR",
) -> str:
    """Build a count-aware table with exactly one visible seat per participant."""
    positions = table_seat_positions(players)
    if isinstance(board_slots, bool) or not isinstance(board_slots, int) or not 0 <= board_slots <= 5:
        raise ValueError("board_slots must be an integer from 0 to 5")
    if len(hero_cards) > 2 or len(community_cards) > board_slots:
        raise ValueError("Displayed cards exceed the available table slots")

    language = "EN" if str(language).upper() == "EN" else "KOR"
    opponents = players - 1
    opponent_label = "Opponent" if language == "EN" else "상대"
    you_label = "You" if language == "EN" else "나"
    total_label = "Players" if language == "EN" else "전체"
    table_aria = (f"Poker table, {players} players: 1 You and {opponents} opponents" if language == "EN"
                  else f"포커 테이블, 총 {players}명: 나 1명과 상대 {opponents}명")
    hero_empty = "Your 2 cards appear here" if language == "EN" else "내 카드 2장을 여기에 놓아요"
    board_empty = "Community cards appear here" if language == "EN" else "공용 카드가 여기에 공개돼요"
    seats: list[str] = []
    for index, (left, top) in enumerate(positions, start=1):
        seats.append(
            f'<div class="seat opponent" data-seat-index="{index}" aria-label="{opponent_label} {index}" '
            f'style="left:{left:.2f}%;top:{top:.2f}%">'
            f'<span class="seat-icon">👤</span><small>{opponent_label} {index}</small></div>'
        )
    seats.append(
        f'<div class="seat you" data-seat-index="you" aria-label="{you_label}">'
        f'<span class="seat-icon">🙂</span><small>{you_label}</small></div>'
    )
    hero_html = card_html(hero_cards, hero_empty, 2)
    board_html = card_html(community_cards, board_empty, board_slots)
    safe_subtitle = escape(str(subtitle)[:100])
    return f"""
    <div class="table-scene" data-player-count="{players}" data-opponent-count="{opponents}"
         role="img" aria-label="{table_aria}">
      <div class="table-count-badge">{(f"{total_label} {players}" if language == "EN" else f"{total_label} {players}명")}</div>
    <div class="felt">
        <div class="felt-title">{safe_subtitle}</div>
        <div class="board-row">{board_html}</div>
        <div class="pot-label">{"POT · ANALYSIS TABLE" if language == "EN" else "POT · 분석용 테이블"}</div>
        <div class="hero-row">{hero_html}</div>
      </div>
      {''.join(seats)}
    </div>
    """

def make_card_snapshot(hero_cards: Sequence[Card], community_cards: Sequence[Card]) -> dict[str, list[Card]]:
    """Return an isolated snapshot for undo history."""
    return {"hero_cards": list(hero_cards), "community_cards": list(community_cards)}


def restore_card_snapshot(stack: list[dict[str, list[Card]]]) -> tuple[list[Card], list[Card]] | None:
    """Pop and restore the last card snapshot; return None when history is empty."""
    if not stack:
        return None
    snapshot = stack.pop()
    return list(snapshot["hero_cards"]), list(snapshot["community_cards"])


def is_five_multiple(value: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0 and value % 5 == 0


def remove_card(cards: list[Card], index: int) -> list[Card]:
    if not 0 <= index < len(cards):
        raise IndexError("Card index is out of range")
    return cards[:index] + cards[index + 1:]
