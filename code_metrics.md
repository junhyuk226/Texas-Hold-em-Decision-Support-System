# Code Metrics — v10.2.6

| File | Purpose |
|---|---|
| `app.py` | Streamlit wizard, durable session state, EN/KOR language switch, 2–10 participant slider, theme-aware premium UI, same-hand progression, Plotly analytics and recommendation panel |
| `poker_engine.py` | Hand evaluation, Monte Carlo equity, weighted opponent sampling, 95% Hoeffding bounds and pot/call math |
| `decision_helpers.py` | Street progression, equity-history snapshots with per-stage sampling ranges, model-signature validation, chart rows and action heuristics |
| `theme_helpers.py` | Light/dark theme resolution and high-contrast Plotly palettes |
| `storage.py` | Local JSON hand history and CSV export |
| `ui_helpers.py` | Order-independent card parsing, Korean shortcuts, card labels/colors, two-box picker, adaptive table seats, card removal and Undo |
| `tests/` | Engine regression, state transitions, statistical precision, theme contrast, chart structure, storage and UI render smoke tests |

## Validation status

- 145 automated tests passed; `python -m compileall -q .` passed.
- All six wizard screen branches render through the Streamlit API stub harness.
- Light/dark Plotly templates and text contrast are tested; Streamlit CSS variables drive custom app surfaces.
- Four analytical figures are checked: equity trend (with per-stage sampling bands), pot/additional call, Monte Carlo convergence and horizontal outcome distribution.
- The 25,000-sample 95% Hoeffding half-width is 0.858939 percentage points; the sample count and outcome-count sum are tested.
- Streamlit is not installed in the development container, so actual native widget rendering, macOS theme changes and browser file downloads remain Mac acceptance tasks.
