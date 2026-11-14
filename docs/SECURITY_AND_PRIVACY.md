# Security and Privacy Notes — v10.2.6 Public Release

## Findings from the release-package review

The reviewed release archive contains application source, tests, documentation, pinned direct dependencies, and a deterministic card-evaluation test fixture. The archive does not contain a Git history, personal hand-history records, `.env` files, Streamlit secrets, virtual environments, private keys, API tokens, personal email addresses, or user-specific absolute home-directory paths.

A static scan of the included application source found no custom network client, HTTP upload, socket connection, shell command execution, subprocess launch, dynamic `eval`/`exec`, account integration, payment flow, or automated wagering feature. External links in the source are limited to Python installation instructions in the launchers/documentation. This is a source review, not a formal security audit or proof that every dependency is vulnerability-free.

## Local-data handling

- Hand history is written only to `data/hand_history/hands.json` under this project directory.
- Saved records are whitelisted to game and calculation fields; no name, email, account ID, or payment field is collected by the app.
- JSON and CSV exports are generated only when the user clicks the download controls in the local interface.
- `.gitignore` excludes the local `data/` directory and the app's hand-history export filenames, along with `.venv/`, `.env*`, Streamlit secrets, and local caches.
- The committed `.streamlit/config.toml` disables Streamlit usage statistics, suppresses the first-run email prompt, and binds the server to `127.0.0.1` rather than the local network.

## Remaining considerations

- Initial dependency installation requires an internet connection to obtain the pinned packages. The application analysis itself runs locally after installation.
- The app uses third-party packages listed in `requirements.txt`; this package review does not constitute a supply-chain or vulnerability audit of those packages or their transitive dependencies.
- A user can still manually copy private files into the repository folder. Review the staged file list before committing; `.gitignore` reduces accidental inclusion but cannot identify every possible personal document.
- Public GitHub repository activity is associated with the GitHub account. Enable GitHub's **Keep my email addresses private** setting before committing, use a professional account profile, and do not publish from an employer-owned organization unless authorized.
- The tool provides poker action suggestions, including heuristic bet/raise candidates, but does not place bets or connect to a poker account. It is an educational analysis tool, not financial or gambling advice.

## Scope

This review covers only the contents of the supplied v10.2.6 Windows GitHub package. It does not inspect the user's computer, browser, GitHub account settings, employer network, or other files outside the archive. No software scan can guarantee zero risk.
