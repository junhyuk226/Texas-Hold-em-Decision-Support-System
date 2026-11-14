# Windows: Publish this project to GitHub

This guide is for the v10.2.6 public-release source package. The repository contains source code and tests only; it does not include local hand history, virtual environments, or personal settings.

## Before using a shared or employer-managed computer

- Prefer a personal, trusted computer for signing in to GitHub.
- If this is a public/shared computer, do not save your password, enable browser password storage, or leave an authenticated session open. The safest choice is to download the release now and publish later from your own device.
- If this is an employer-managed computer, check the employer's acceptable-use and software-installation rules before installing GitHub Desktop or uploading personal code.
- Publish to your personal GitHub account, not an employer organization. Do not upload employer-owned code, data, credentials, or files.

## 1. Download and extract the release

1. Download `Poker_Texas_Holdem_Decision_Support_Tool_v10_2_6_Public_Release.zip` from the ChatGPT conversation.
2. In File Explorer, right-click the ZIP and choose **Extract All...**.
3. Open the extracted `poker_assistant_v10` folder. The repository root must contain `README.md`, `app.py`, `poker_engine.py`, `requirements.txt`, `.gitignore`, `.streamlit/config.toml`, `tests/`, and `docs/` directly. Do not upload the ZIP file itself and do not create an extra nested `poker_assistant_v10/poker_assistant_v10/` folder.
4. Before publishing, confirm the folder contains no `data/`, `.venv/`, `.env`, hand-history export files, or `.streamlit/secrets.toml`. Keep the included `.streamlit/config.toml`; it disables usage statistics and restricts the server to this computer.

## 2. Create an empty public repository

1. Sign in at https://github.com using your personal account.
2. Select **New repository**.
3. Repository name: `texas-holdem-decision-support-tool`.
4. Description: `An AI-assisted Python and Streamlit tool for Texas Hold'em probability and single-decision analysis.`
5. Select **Public** only when you are ready for anyone to view the source.
6. Leave **Add a README**, **Add .gitignore**, and **Choose a license** unselected. These are already handled in the release package or intentionally left undecided.
7. Create the repository.

## 3A. Recommended: upload through the GitHub website (no Git commands)

The release contains fewer than 100 files, so it fits GitHub's documented browser-upload limit.

1. On the empty repository page, select **Add file** > **Upload files** (or the **uploading an existing file** link).
2. In File Explorer, open the extracted `poker_assistant_v10` folder.
3. Select all items inside that folder (Ctrl+A) and drag them into the GitHub upload area. Include hidden files such as `.gitignore`. The result at the repository root should show `README.md`, `app.py`, `.gitignore`, `tests/`, and `docs/`.
4. Wait until all file uploads finish. Review the file list before committing.
5. Commit message: `Publish v10.2.6 public release`.
6. Select **Commit changes** to the `main` branch.
7. Do not upload the parent folder as an extra folder level; upload its contents so `README.md` appears at the repository root.

GitHub documents a maximum of 100 files per browser upload and 25 MiB per file. This package is below those limits. If the web page rejects a folder drag, use GitHub Desktop instead.

## 3B. Alternative: GitHub Desktop

Use this only on a trusted computer and only if installing it is permitted.

1. Install GitHub Desktop from https://desktop.github.com/ and sign in to your personal GitHub account.
2. In GitHub Desktop, select **File** > **New repository...**.
3. Name: `texas-holdem-decision-support-tool`.
4. Choose a local path you control, such as `Documents\GitHub`.
5. Do not initialize another README, .gitignore, or license; leave those options disabled if shown.
6. Before committing, open GitHub **Settings → Emails** and enable **Keep my email addresses private** so web-based commits use a GitHub noreply address. GitHub documents that this setting controls the commit email used for web-based operations.
7. Create the repository.
7. In GitHub Desktop, choose **Repository** > **Show in Explorer**.
8. Copy the *contents* of the extracted `poker_assistant_v10` folder into the new repository folder. Do not copy the parent folder itself. Include `.gitignore`.
9. Return to GitHub Desktop. Review the changed-file list. Confirm that `data/`, `.venv/`, `.env`, and personal files are absent.
10. Summary: `Publish v10.2.6 public release`.
11. Select **Commit to main**.
12. Select **Publish repository**. Set the repository name as above, choose your personal account (Organization: **None**), and turn off **Keep this code private** only if you intend a public release.
13. Select **Publish Repository**.

## 4. Verify the public repository

Open the repository page on GitHub and confirm:

- `README.md` renders on the repository front page.
- `app.py`, `poker_engine.py`, `decision_helpers.py`, `storage.py`, and `tests/` are at the repository root.
- `docs/` and `run_windows.bat` are present.
- `archive/`, `data/`, `.venv/`, `.env`, hand-history JSON/CSV exports, and `.streamlit/secrets.toml` are absent. The privacy-safe `.streamlit/config.toml` is present.
- The README correctly says AI-assisted development and accurately describes the single-call model and heuristic raise candidate.
- No license has been added unless you explicitly chose one.

## 5. Optional: run on Windows

The Windows launcher is `run_windows.bat`.

1. Install Python 3.10 or later from https://www.python.org/downloads/windows/.
2. Open the project folder and double-click `run_windows.bat`.
3. On first launch, the script creates a project-local `.venv`, installs the pinned dependencies, checks them, and starts Streamlit.
4. Open the local URL printed in the terminal (normally `http://127.0.0.1:8501`).
5. Press Ctrl+C in the terminal to stop the application.

Do not run the application on a locked-down computer if local software execution or dependency installation is prohibited.

## 6. License choice

This package intentionally does not include a `LICENSE` file. A public repository without a license allows people to view the source but does not grant general permission to reuse, modify, or redistribute it. Add MIT only if you consciously want to grant those permissions.
