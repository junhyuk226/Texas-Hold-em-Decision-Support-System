# Portfolio Summary — Texas Hold'em Decision-Support Tool (v10.2.6)

## Overview

An offline Python/Streamlit application that estimates Texas Hold'em showdown equity and supports a single immediate call decision using Monte Carlo simulation, a weighted opponent baseline, pot odds, and expected value.

## Developer contribution

- Defined product requirements and prioritized the user workflow and analysis features.
- Directed AI-assisted implementation and iterative refinements to the Python/Streamlit prototype.
- Reviewed analytical outputs, identified functional issues, and guided fixes and usability improvements.
- Evaluated model assumptions and documented sampling uncertainty and methodological limitations.

## Technical components

- Five-card / seven-card hand evaluation.
- Weighted opponent-range sampling and 25,000-trial Monte Carlo equity estimation.
- Win / tie / loss probabilities and fractional pot-share equity.
- Two-sided 95% Hoeffding sampling-error bound.
- Pot odds and single-call expected value.
- Heuristic action suggestions and non-optimized bet/raise sizing.
- Streamlit interface with 2–10 player table layout, session progression, visualizations, and local history export.

## Validation evidence

- 144 automated tests passed in the development-container run.
- 400 randomized seven-card hands compared with exhaustive five-card-subset evaluation.
- 1,000 deterministic golden regression cases preserved from the v7 hand evaluator.
- Seed reproducibility, multiway simulations, input validation, session state, chart construction, theme contrast, and storage behavior covered.
- Python compilation passed.
- Native Streamlit widget rendering and final macOS browser acceptance remain to be performed by the user.

## Scope and limitations

This is not a GTO solver, player-behavior model, or investment model. Unknown opponents are represented by a fixed weighted baseline. The Monte Carlo interval measures sampling error conditional on that assumption, not model accuracy. EV covers one immediate call decision and excludes later streets, rake, implied odds, side pots, stack constraints, and tournament ICM.
