# Texas Hold'em Decision-Support Tool

**Python · Streamlit · Monte Carlo Simulation · AI-Assisted Development**

An offline Texas Hold'em analysis application that estimates showdown equity and compares it with pot odds to support a single, immediate call decision. It combines a weighted opponent-range baseline, 25,000-trial Monte Carlo simulation, expected-value calculations, and an interactive Streamlit interface.

> **Educational use only.** This application uses abstract points and simulated cards. It does not connect to poker accounts, handle money, place bets, automate online play, or guarantee profitable decisions.

## Project overview

The project translates a card-game decision problem into a small quantitative workflow:

1. Enter the hero's cards, community cards, number of players, and current pot/call amounts.
2. Estimate showdown outcomes under an explicitly stated opponent-card assumption.
3. Compare estimated pot-share equity with the break-even equity implied by pot odds.
4. Review the calculation, uncertainty display, and decision-support output.

The tool is designed for offline learning and analysis, not as a professional poker solver.

## Features

- **52-card visual picker** with duplicate-card prevention, undo, and flexible keyboard shortcuts.
- **2–10 player tables** with responsive seat layouts and heads-up handling.
- **Weighted opponent baseline:** a fixed `typical` weighted range for beginner-facing use. It is a modeling assumption, not an observed or empirically calibrated population range.
- **Monte Carlo equity estimation:** 25,000 simulated deals by default in the application, using a reproducible seed.
- **Win / tie / loss and pot-share equity:** ties contribute a fractional share of the pot.
- **Pot odds and single-call EV:** transparent calculations for one immediate call decision.
- **Decision-support guidance:** CHECK / BET candidates when no call is due, and FOLD / CALL with a heuristic RAISE candidate when facing a bet. Bet/raise sizing is not optimized.
- **Four analytical views:** equity versus pot odds over the hand, pot/additional-call amounts, Monte Carlo convergence, and win/tie/loss counts.
- **Light and dark chart palettes**, Korean/English interface toggle, local JSON hand history, and JSON/CSV export.

## Analytical methodology

### Monte Carlo equity

Each simulated deal samples unseen cards without replacement for the remaining board and opponent hands. The evaluator compares the best five-card hand available to each player. A strict win contributes 1 to equity, a loss contributes 0, and a tie contributes the hero's fractional share of the pot.

The application uses a fixed weighted `typical` opponent baseline and 25,000 trials per analysis. The model does not infer actual opponent behavior. Results are conditional on this assumed distribution.

### Sampling uncertainty

For observations bounded in `[0, 1]`, the app reports a conservative two-sided 95% Hoeffding half-width:

\[
\epsilon = \sqrt{\frac{\ln(2/0.05)}{2n}}
\]

At 25,000 trials, the half-width is approximately **±0.858939 percentage points (±0.86 pp)**. This quantifies Monte Carlo sampling uncertainty only. It does not measure whether the opponent-range assumption matches real players, and it is not a 95% probability that a recommendation is correct.

### Pot odds and call EV

For current pot `P`, additional call amount `C`, and estimated pot-share equity `E`:

- `Pot Odds = C / (P + C)` (0 when `C = 0`)
- `Call EV = E × P − (1 − E) × C`

This is a **single immediate call** model. It excludes later betting rounds, rake, implied odds, side pots, stack constraints, and tournament ICM.

### Action suggestions and limitations

When no amount is due, the interface can show CHECK or a small BET candidate. When facing a bet, the call calculation supports FOLD/CALL guidance; a RAISE candidate can appear when simple equity thresholds are met. BET/RAISE sizing is heuristic rather than EV-optimal. The model does not calculate fold equity, opponent response probabilities, position effects, or a multi-street game tree. This is **not a GTO solver** or an opponent tracker.

## Technology

- Python 3.10+
- Streamlit 1.65.0
- pandas 2.3.3
- Plotly 6.9.0
- Python standard library for card evaluation, simulation, probability calculations, and local persistence

## Run locally (Windows)

1. Install Python 3.10 or later.
2. Open the project folder in File Explorer.
3. Double-click `run_windows.bat`.

The first run creates a project-local `.venv/` if needed, installs the pinned requirements, checks dependencies, and launches Streamlit. Open the local URL printed in the terminal (normally `http://127.0.0.1:8501`). Press `Ctrl+C` in the terminal to stop the app.

Alternatively, open Command Prompt in the project folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## Run locally (macOS)

1. Install Python 3.10 or later.
2. Download or clone this repository.
3. From the project directory, run:

```bash
bash run_mac.command
```

The first run requires internet access to download the pinned Python packages. The script creates a project-local `.venv/` only if one does not exist, installs the pinned requirements, checks dependencies, and launches Streamlit. It does not reuse another project's environment or data directory. Once dependencies are installed, the app performs its analysis locally.

Alternatively, run the commands manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://127.0.0.1:8501` if the browser does not open automatically. Press `Control+C` in the terminal to stop the app.

## Run automated tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

The included suite covers hand-ranking edge cases, 400 randomized comparisons against exhaustive five-card evaluation, 1,000 frozen regression cases based on the v7 evaluator, Monte Carlo reproducibility and bounds, multiway simulations, heads-up input boundaries, session progression, chart construction, theme contrast, storage validation, and UI branch smoke tests.

**Latest development-container result:** 145 tests passed; Python compilation passed. The UI smoke tests use a Streamlit API stub. A final launch and native-widget/theme check in a real macOS browser is still required before claiming full end-to-end UI validation.

## Data and privacy

Hand history is stored locally at `data/hand_history/hands.json` and can be exported from the app. The application stores card selections, abstract point amounts, table settings, and calculation results. Do not add names, account details, or other personal information to saved records.

The repository's `.gitignore` excludes the complete `data/` directory, hand-history JSON/CSV exports, `.venv/`, Streamlit secrets, environment files, caches, and OS/editor artifacts. The committed `.streamlit/config.toml` disables Streamlit usage statistics, turns off the first-run email prompt, and binds the app to `127.0.0.1` so it is not exposed to other devices on the local network. No personal hand history or local virtual environment is included in the release source. See [Security and Privacy Notes](docs/SECURITY_AND_PRIVACY.md) for the release-package review scope and remaining considerations. The application code contains no account login, payment, bet execution, opponent tracking, or hand-history upload feature. Installing Python dependencies requires an internet connection; application analysis runs locally after installation.

## AI-assisted development and contributor role

AI-assisted coding tools were used to support implementation, debugging, and iterative refinement. The project developer directed product requirements and feature priorities, reviewed analytical outputs, identified issues, and guided changes to the user flow and visualizations. The code should therefore be described as an **AI-assisted development project**, not as software written entirely independently by the developer.

## Project structure

```text
.
├── app.py
├── poker_engine.py
├── decision_helpers.py
├── storage.py
├── i18n.py
├── ui_helpers.py
├── theme_helpers.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── run_mac.command
├── run_windows.bat
├── CHANGELOG.md
├── docs/
│   ├── acceptance_matrix.md
│   ├── code_metrics.md
│   ├── methodology.md
│   ├── portfolio_summary.md
│   └── validation_report.md
└── tests/
    ├── fixtures/
    └── test_*.py
```

## License

No open-source license is currently included. Unless a license is added, the source is viewable but reuse, modification, and redistribution are not granted by this repository. Add an explicit license only after the copyright holder chooses the intended permissions.
