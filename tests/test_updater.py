import unittest
from unittest.mock import MagicMock, patch


class TestUpdater(unittest.TestCase):
    def setUp(self):
        from src.updater import Updater
        self.updater = Updater()

    def _mock_response(self, version, url="https://example.com/natnest"):
        resp = MagicMock()
        resp.json.return_value = {"version": version, "url": url}
        return resp

    # --- check() ---

    def test_check_returns_false_on_network_error(self):
        with patch("src.updater.requests.get", side_effect=Exception("timeout")):
            available, url, version = self.updater.check()
        self.assertFalse(available)
        self.assertIsNone(url)
        self.assertIsNone(version)

    def test_check_returns_false_for_same_version(self):
        with patch("src.updater.requests.get", return_value=self._mock_response("0.5.0")):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertFalse(available)

    def test_check_returns_false_for_older_version(self):
        with patch("src.updater.requests.get", return_value=self._mock_response("0.4.9")):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertFalse(available)

    def test_check_returns_true_for_newer_patch(self):
        with patch("src.updater.requests.get", return_value=self._mock_response("0.5.1")):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertTrue(available)
        self.assertEqual(version, "0.5.1")

    def test_check_returns_true_for_newer_minor(self):
        with patch("src.updater.requests.get", return_value=self._mock_response("0.6.0")):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertTrue(available)

    def test_check_returns_true_for_newer_major(self):
        with patch("src.updater.requests.get", return_value=self._mock_response("1.0.0")):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertTrue(available)

    def test_check_returns_url_when_update_available(self):
        download_url = "https://example.com/natnest-new"
        with patch("src.updater.requests.get", return_value=self._mock_response("1.0.0", download_url)):
            with patch("src.updater.Config.VERSION", "0.5.0"):
                available, url, version = self.updater.check()
        self.assertEqual(url, download_url)

    def test_check_returns_false_when_no_version_in_response(self):
        resp = MagicMock()
        resp.json.return_value = {}
        with patch("src.updater.requests.get", return_value=resp):
            available, url, version = self.updater.check()
        self.assertFalse(available)
