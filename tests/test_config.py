import re
import unittest
from pathlib import Path


class TestConfig(unittest.TestCase):
    def setUp(self):
        from src.config import Config
        self.Config = Config

    def test_version_is_valid_semver(self):
        self.assertRegex(self.Config.VERSION, r"^\d+\.\d+\.\d+$")

    def test_version_matches_version_file(self):
        version_file = Path(__file__).parent.parent / "VERSION"
        self.assertEqual(self.Config.VERSION, version_file.read_text(encoding="utf-8").strip())

    def test_config_dir_name(self):
        self.assertEqual(self.Config.CONFIG_DIR.name, ".natnest")

    def test_key_file_is_under_config_dir(self):
        self.assertTrue(str(self.Config.KEY_FILE).startswith(str(self.Config.CONFIG_DIR)))

    def test_is_windows_is_bool(self):
        self.assertIsInstance(self.Config.IS_WINDOWS, bool)

    def test_server_url_has_scheme(self):
        self.assertTrue(
            self.Config.SERVER_URL.startswith("http://")
            or self.Config.SERVER_URL.startswith("https://")
        )


class TestBumpVersionScript(unittest.TestCase):
    def _bump(self, current, part):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.bump_version import bump
        return bump(current, part)

    def test_bump_patch(self):
        self.assertEqual(self._bump("0.5.0", "patch"), "0.5.1")

    def test_bump_minor(self):
        self.assertEqual(self._bump("0.5.0", "minor"), "0.6.0")

    def test_bump_major(self):
        self.assertEqual(self._bump("0.5.0", "major"), "1.0.0")

    def test_bump_minor_resets_patch(self):
        self.assertEqual(self._bump("1.2.9", "minor"), "1.3.0")

    def test_bump_major_resets_minor_and_patch(self):
        self.assertEqual(self._bump("1.9.9", "major"), "2.0.0")
