# Publishing to GitHub

For Windows upload instructions (GitHub website and GitHub Desktop), see [WINDOWS_GITHUB_UPLOAD.md](WINDOWS_GITHUB_UPLOAD.md).

The repository should be created empty before uploading. Do not add a second README, .gitignore, or license during repository creation. The release intentionally contains no `LICENSE` file; choose a license only after deciding what reuse permissions to grant.

Before publishing, verify that `data/`, `.venv/`, `.env`, `.streamlit/secrets.toml`, hand-history exports, and employer-owned or personal files are absent. The repository root should contain the app files and `README.md` directly, not an extra nested project directory.


Before your first public web-based commit, check GitHub **Settings → Emails** and enable **Keep my email addresses private**. GitHub uses the selected commit email to attribute web-based commits; with email privacy enabled, web commits use a GitHub-provided noreply address. See <https://docs.github.com/en/account-and-profile/concepts/email-addresses>.
