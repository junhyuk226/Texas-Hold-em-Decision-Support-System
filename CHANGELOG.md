# Changelog

## v10.2.6 — dark theme, sampling ranges and chart polish

- Removed the app's forced root `color-scheme`; Streamlit now owns native widget appearance. HTML surfaces use live Streamlit theme tokens, while Plotly charts use dedicated, high-contrast light/dark palettes.
- Added 95% pointwise Monte Carlo sampling bounds to each recorded street in the Equity / Pot Odds history chart. Legacy snapshots without sampling metadata remain displayable with a zero-width band.
- Focused the Monte Carlo convergence chart around the final estimate so the running estimate and final ±0.86pp interval are readable. The chart explicitly notes that early wide bounds can extend beyond the visible y-axis.
- Standardized chart section headers, card borders, plot surfaces, hover labels, axis typography and semantic colors across the equity trend, pot/call, convergence and outcome charts. The win/tie/loss view is a horizontal bar chart, not a pie/donut.
- Clarified the 25,000-sample precision: a conservative two-sided 95% Hoeffding sampling-error bound of approximately ±0.85894 percentage points. This is not model accuracy and does not include opponent-range mismatch.
- Automated validation: 142 tests passed; `compileall` passed. Live macOS / Streamlit dark-theme rendering remains user acceptance testing.

## v10.2.5 — numbered player slider, single opponent baseline and visual polish

- Restored a horizontal player-count slider from 2 to 10. Each slider position has a visible numeric tick beneath it, and the selected total plus opponent count is shown immediately.
- Replaced the four beginner-facing opponent presets with one fixed `typical` weighted Monte Carlo baseline. The player no longer needs to choose between strong/typical/loose/random assumptions.
- The baseline is explicitly described as an assumption rather than inferred opponent behavior. Legacy saved results retain their original model label in the detailed results view.
- Kept Monte Carlo at 25,000 samples. Development-container timing: about 0.42s (1 opponent), 0.62s (2), 1.29s (5), 2.16s (9); environment-specific, not a Mac performance guarantee.
- Refined the visual design with an ivory canvas, dark-green accents, cleaner step chips, primary buttons, metric surfaces and a compact opponent-model panel.
- Automated validation: 130 tests passed; Python compilation passed; all six screen branches passed the Streamlit API smoke harness. Actual macOS widget interaction remains user acceptance testing.

## v10.2.4 — card-entry polish, timeline retention and Monte Carlo convergence visualization

- Added contextual Korean-keyboard card aliases: `ㅋㅎ` / `ㅋH` / `ㅎㅋ` resolve to K♥; `ㅋㄷ`, `ㅋㅅ`, and `ㅋㅋ` resolve to K♦, K♠, and K♣. Rank/suit order remains flexible.
- Ensured ten is shown as `10` (not the engine's internal `T`) in table cards, selected-card faces, and newly saved hand records.
- Kept hearts and diamonds red in the selected private/community card display; corrected the adjacent instruction to point to the visible `×` remove button.
- Made the compact keyboard-entry form directly visible; Enter submits card tokens. The suit/rank picker deals the card immediately after the second selection, without an extra Add action.
- Replaced ambiguous global Flop/Turn numbering with street labels and explicit same-street bet-update labels. Community-card edits now truncate only invalid later-street snapshots; Undo restores the previous card state and its full valid timeline.
- Moved EN/KOR beside the app title. Clarified participant count choices (2 heads-up, 3–5 short-handed, 6-max, 7–10 full ring).
- Added actual-run Monte Carlo convergence checkpoints with cumulative equity, pointwise 95% Hoeffding bounds, and strict win/tie/loss counts. The confidence band narrows with sample count instead of showing the final interval across the whole simulation history.
- Validation: 126 automated tests passed; Python compilation passed; the seeded 25,000-sample result has 25,000 matching outcome counts and the final convergence point exactly matches final equity. Full Streamlit/macOS interaction still requires user acceptance.


## v10.2.3 — flexible card shortcuts, bilingual UI and heads-up slider fix

- Fixed the heads-up boundary crash: with exactly two total players, the remaining-opponent count is fixed at one and the app no longer creates an invalid slider whose minimum and maximum are both 1.
- Added order-independent compact card parsing: `AS` and `SA`, `10D` and `D10`, suit symbols in either order, and spaced rank/suit pairs are accepted.
- Added English suit initials `C/D/S/H` and Korean initial consonants `ㅋ/ㄷ/ㅅ/ㅎ`; uppercase/lowercase English input is normalized.
- Added a persistent `EN / KOR` language toggle at the top of every screen. Language changes preserve the current hand, participant count and card selections.
- Localized all six wizard screens, result guidance, recommendation reasoning/sizing notes and graph hover labels.
- Removed duplicated community-card progress copy and corrected the table's bilingual accessible player-count label.
- Added exhaustive shortcut tests across all 13 ranks, 8 English/Korean suit shortcuts and both input orders (224 cases), nine table-size slider-bound tests, a stale heads-up widget-key test, and EN rendering checks for all six screens plus the results chart.
- Validation: 111 automated tests passed; Python compilation passed. Streamlit is not installed in the isolated development container, so real macOS widget/browser interaction remains user acceptance testing.

## v10.2.2 — table layout and analysis-history hotfix

- Fixed opponent-seat collisions with the hero seat in the previous circular layout. Added an upper-arc layout for all table sizes from 2 to 10, one visible seat per participant, explicit player-count markup, and responsive seat sizing.
- Added table-layout tests for every supported player count, mobile/desktop seat geometry, duplicate positions, visible count badges, invalid inputs and subtitle escaping.
- Fixed equity-history contamination: changing private cards, removing/replacing a card, or truncating the community board clears old snapshots. Adding the next street's new board cards preserves valid previous snapshots.
- Added a progress-series signature; changing table size, active opponents or opponent-range assumptions starts a fresh chart series. Legacy active sessions with no signature start a clean series.
- Added a Streamlit API stub smoke harness covering all six screen branches, participant counts 2/3/5/9, result chart construction, and card-edit history behaviour.
- Chromium browser rendering verified the actual table HTML/CSS at 980px, 390px and 360px widths for every supported table size (27 cases): exact seat counts, no seat overlap and no clipped seats.
- Full Monte Carlo matrix covered 96 combinations of four streets, six opponent counts (1/2/3/5/7/9), and four opponent presets. All outputs were finite, reproducible and normalized. 25,000-sample performance smoke: 0.69s (1 opponent), 2.03s (5), 3.37s (9) in this development container; environment-specific.

## v10.2.1 — Conditional widget state persistence hotfix

- Fixed a Streamlit state-lifecycle bug where participant count could reset to six when leaving the participant step. Durable game values now use separate keys from conditional widgets.
- Separated durable state for active opponents, opponent style, betting mode and bet amounts from their conditional widget keys.

## v10.2 — Beginner card picker and clearer result dashboard

- Added separate suit and rank dropdowns with live card preview; retained optional compact card entry.
- Added an interactive Plotly Equity vs Pot Odds chart with hover details and a prominent recommended-move panel.

## v10.1 — Continuous hand progression and decision guidance

- Added next-street continuation, progress chart, contextual action guidance and heuristic bet sizing.

## v10.0 — Beginner-oriented interface

- Added six-step beginner flow, table visualization, four opponent presets and five-point integer bet inputs.
