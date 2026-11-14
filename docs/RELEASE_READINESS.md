# Public Release Readiness — v10.2.6

## Completed in this package

- [x] English portfolio-oriented README with project scope, methodology, installation, testing, limitations, privacy, and AI-assisted development disclosure.
- [x] Removed the v7 source archive from the public source tree.
- [x] Preserved the 1,000-case v7 evaluator comparison as frozen expected-output fixtures.
- [x] Removed the sibling `poker_assistant_v8` environment and hand-history path dependency.
- [x] Configured the launcher to create/reuse only this project's `.venv/`.
- [x] Expanded `.gitignore` to exclude local `data/`, hand-history exports, `.venv/`, Streamlit secrets, environment files, logs, and caches while allowing the reviewed privacy-safe config.
- [x] Added tests for project-local hand-history storage, export ignore rules, and localhost-only / no-telemetry Streamlit configuration.
- [x] Added a security and privacy review note; no credentials, personal contact details, user-specific paths, local data, or archive code found in the release package.
- [x] Updated app version labels to v10.2.6.
- [x] Automated test suite: 145 passed, 0 failed.
- [x] `python -m compileall -q .` passed.
- [x] `bash -n run_mac.command` passed.

## Still required before treating this as fully validated

- [ ] Launch the app on the maintainer's Mac using a clean project-local virtual environment.
- [ ] Verify light/dark mode, card input, heads-up table, analysis output, charts, and JSON/CSV export in a real browser.
- [ ] Capture two or three genuine screenshots from the running v10.2.6 app and add them to the README.
- [ ] Decide whether to grant an open-source license. No license is included by default.
- [ ] Create the GitHub repository and push the reviewed source.

## Test boundary

The 145 automated tests ran in the development container. UI smoke tests use a Streamlit API stub; they do not prove that native Streamlit widgets, browser downloads, or macOS theme switching work in the user's browser. Do not claim full end-to-end macOS validation until the local checklist above is completed.
