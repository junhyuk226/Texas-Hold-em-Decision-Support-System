from pathlib import Path
import unittest

import storage


class TestPublicReleaseIsolation(unittest.TestCase):
    def test_default_hand_history_is_inside_this_project(self):
        project_root = Path(storage.__file__).resolve().parent
        self.assertEqual(
            storage.DEFAULT_HISTORY_PATH,
            project_root / "data" / "hand_history" / "hands.json",
        )

    def test_gitignore_excludes_local_history_and_environment(self):
        project_root = Path(storage.__file__).resolve().parent
        ignore_text = (project_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/data/", ignore_text)
        self.assertIn(".venv/", ignore_text)
        self.assertIn(".streamlit/", ignore_text)
        self.assertIn(".env", ignore_text)
        self.assertIn("poker_hand_history.json", ignore_text)
        self.assertIn("poker_hand_history.csv", ignore_text)

    def test_committed_streamlit_config_is_local_and_disables_telemetry(self):
        project_root = Path(storage.__file__).resolve().parent
        config_text = (project_root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn('address = "127.0.0.1"', config_text)
        self.assertIn('serverAddress = "127.0.0.1"', config_text)
        self.assertIn("gatherUsageStats = false", config_text)
        self.assertIn("showEmailPrompt = false", config_text)
