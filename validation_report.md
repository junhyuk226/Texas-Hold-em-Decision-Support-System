# Validation Report — Texas Hold'em Decision-Support Tool v10.2.6

## Automated tests

Commands:

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

**145 tests passed; 0 failures.** Python compilation passed in the development container.

Coverage includes:

- Hand-ranking edge cases and 400 randomized seven-card comparisons against exhaustive five-card subset evaluation.
- 1,000 deterministic seven-card golden cases generated from the prior v7 evaluator; the public release includes expected outputs, not the archived v7 implementation.
- Exact state counts, seeded Monte Carlo reproducibility, confidence bounds, and up to nine unknown opponents.
- Heads-up slider boundaries, flexible card input, Korean/English language switching, and session progression.
- Chart structures, convergence data, light/dark Plotly palettes, and contrast checks.
- Local history schema validation, field whitelisting, JSON persistence, and CSV serialization.

## Monte Carlo precision

For each simulated deal, the hero's pot share is in `[0, 1]`. The two-sided 95% Hoeffding half-width is:

`epsilon = sqrt(ln(2 / 0.05) / (2 * n))`

At 25,000 trials, the half-width is approximately **0.858939 percentage points**. This is a sampling-only bound conditional on the fixed weighted opponent model; it does not quantify opponent-model misspecification or recommendation correctness.

## UI verification boundary

The six wizard branches and Plotly figures were tested with a Streamlit API stub. Two additional public-release tests verify project-local history storage and repository ignore rules. Streamlit's native widgets, browser file downloads, macOS appearance switching, and the updated `run_mac.command` have **not** been executed in a real macOS browser in this environment. A final local acceptance test is required before claiming full end-to-end UI validation.

## Performance boundary

Any recorded runtime measurements are development-environment observations, not performance guarantees for other hardware.
