# Opponent model methodology — v10.2.6

The beginner-facing application uses one fixed `typical` weighted baseline so users do not have to choose among several abstract opponent types. It blends stronger and ordinary starting-hand combinations using positive weights. This is a convenience baseline, not an empirically calibrated population model and not an inference about any real opponent.

The calculation uses 25,000 Monte Carlo samples by default. The Monte Carlo confidence interval quantifies sampling uncertainty conditional on this assumed distribution; it does not quantify whether the assumed range matches real opponents. Historical saved records from earlier releases retain their original `random`, `strong`, `typical`, or `loose` model identifiers.

The engine still retains its other opponent-range presets for backward compatibility and controlled testing, but the beginner UI no longer exposes them.

# Methodology — Poker Assistant v10.2

## Showdown equity

The hand evaluator scores the best 5-card hand from each player's available seven cards. Monte Carlo samples unseen board cards and opponent hole cards, evaluates each showdown, and records strict win, tie and loss outcomes. Equity is the expected share of the pot; split pots contribute fractional equity.

## Opponent assumptions

Four presets define a positive weight for each unseen two-card combination:

- `strong`: higher weights for premium pairs and high-card combinations; weak combinations receive a small non-zero weight.
- `typical`: broader weighting across pairs, aces, broadway and suited connected hands.
- `loose`: most combinations remain plausible, with mild boosts for pairs, suited and high cards.
- `random`: equal weight for every available two-card combination.

For weighted presets, opponent hands are drawn from the weighted distribution conditional on no card conflicts with the hero, visible board, future board cards, or other opponents. The model does not infer actual opponent behavior.

Exact enumeration is retained only for supported uniform-random opponent cases. Weighted presets use Monte Carlo.

## Decision support

For current pot `P`, additional call `C`, and equity `E`:

- Pot odds = `C / (P + C)` (zero when `C = 0`).
- Call EV = `E × P − (1 − E) × C`.
- If `C = 0`, display CHECK. Otherwise, positive EV maps to CALL and negative EV maps to FOLD.

This is a single-decision model and excludes later betting rounds, rake and stack/side-pot constraints.

## Hand progression and charts

A browser session retains the same hole cards, already exposed board cards, opponent assumption and progression history when the user advances from preflop to flop, turn and river. Only the newly exposed community card(s) are entered at each next street. Each completed analysis appends a point to the hand's local equity history. Equity is primarily changed by newly revealed cards and opponent assumptions; pot odds and call EV can change when pot/call inputs change even if the cards stay the same.

## Action suggestion and sizing

The UI distinguishes legal action contexts: with no amount to call, the suggestion is CHECK or a small BET candidate; when facing a bet it is FOLD/CALL, with a RAISE candidate only when estimated equity and its edge over pot odds exceed simple thresholds. BET sizing is approximately half pot. RAISE sizing is expressed as the amount added above the call. These sizing rules are transparent heuristics, not expected-value-optimal sizing: fold equity, position, stack sizes, minimum-raise history, rake, opponent response and future betting are not modeled. The output is educational guidance, not a GTO solution.

## Point amount validation

UI and new hand-history writes use non-negative integers in 5-point increments. Legacy integral floats are normalized to integers when saved; fractional or non-5-point values are rejected.


## Monte Carlo sampling precision

Each simulated showdown contributes a pot-share observation between 0 and 1 (ties contribute a fractional share). For `n` independent simulations, the app reports a conservative two-sided 95% Hoeffding bound:

`epsilon = sqrt(ln(2 / 0.05) / (2 * n))`

At 25,000 samples this is approximately 0.00858939, or ±0.858939 percentage points. The interval is clipped to the feasible 0%–100% equity range, but the reported half-width remains the theoretical value and is not artificially reduced by clipping. This measures only random Monte Carlo sampling error conditional on the fixed opponent model; it does not measure whether that model matches real opponents.

## Chart interpretation

- **Equity / Pot Odds trend:** Each point is an analysis snapshot. The green line is expected pot share; the amber line is the break-even equity needed to call. Each street can carry its own pointwise Monte Carlo sampling band.
- **Pot / additional-call bars:** These show the recorded pot and the additional amount needed to continue; they are amounts, not probabilities.
- **Monte Carlo convergence:** The line is the cumulative running estimate as simulated deals are added. The shaded band is the pointwise Hoeffding sampling bound; it narrows as the sample count increases. The vertical axis is focused around the final estimate, so early wide bounds can extend beyond the visible plot window.
- **Outcome distribution:** Horizontal bars show strict wins, ties and losses counted in the same simulation run. This chart is not the equity calculation itself; ties contribute partial pot share to equity.

The application uses Streamlit theme tokens for custom HTML surfaces and separate Plotly palettes for light and dark appearances. Streamlit's `st.context.theme.type` can be temporarily stale during first load or immediately after a settings change; refresh the browser if the Plotly palette does not follow a just-changed appearance.
