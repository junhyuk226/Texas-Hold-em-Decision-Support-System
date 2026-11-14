# Acceptance Matrix — v10.2.6

| Requirement | Automated / local verification | Mac browser acceptance |
|---|---|---|
| Six-step same-hand flow | All six screen branches execute under Streamlit API stub | Real widgets and state continuity |
| 2–10 participant slider and table | State wiring, numeric ticks and responsive seat geometry tests | Confirm slider alignment and seat visuals |
| Order-independent bilingual card shortcuts | Exhaustive rank/suit/order parser tests | Keyboard submission |
| Card suit/rank picker, remove and Undo | Mapping, duplicate rejection and timeline restoration tests | Click/select/Undo sequence |
| EN/KOR state preservation | Six-screen render smoke and state tests | Manual toggle |
| Dark-mode custom surfaces | CSS uses Streamlit theme tokens; no forced root color-scheme | Confirm labels, inputs and result cards in dark mode |
| Dark/light Plotly palette | Light/dark figure templates, backgrounds, labels and contrast tests | Switch appearance and refresh if chart palette is stale |
| 25k sample error explanation | Formula and 25,000-sample precision tests | Verify displayed ±0.86%p and range |
| Equity/Pot Odds history chart | Four Plotly traces including per-street sampling band; legacy history compatibility | Inspect hover and uncertainty band |
| Pot/additional-call chart | Plotly grouped-bar structure and theme colors | Inspect labels and values |
| Monte Carlo convergence chart | Running equity, pointwise Hoeffding band, final marker and focused y-axis | Check readability with real 25k result |
| Win/tie/loss distribution | Horizontal bar chart, counts sum to samples | Confirm no pie/donut and values visible |
| Recommendation panel and sizing | Decision-helper boundary, action and amount tests | Verify wording and amount clarity |
| Hand history JSON/CSV | Storage schema, legacy reads, JSON/CSV serialization | Browser downloads |
| Five-point integer amounts | Input and storage validation tests | Real widget entry |
| Actual app server / native widgets | Not available in isolated test container | Required final Mac acceptance |

**Automated status:** 142 tests passed; `compileall` passed. Streamlit render branches were exercised via an API stub; actual Mac browser appearance and widget interaction remain open.
