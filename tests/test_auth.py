import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAuthManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.session_file = Path(self.tmpdir.name) / "session.json"
        from src.auth import AuthManager
        self.auth = AuthManager()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_get_session_returns_none_when_file_missing(self):
        with patch("src.auth.Config.SESSION_FILE", self.session_file):
            result = self.auth.get_session()
        self.assertIsNone(result)

    def test_save_and_get_session_roundtrip(self):
        data = {"email": "test@example.com", "token": "abc123", "username": "testuser"}
        with patch("src.auth.Config.SESSION_FILE", self.session_file):
            self.auth.save_session(data)
            result = self.auth.get_session()
        self.assertEqual(result, data)

    def test_get_session_handles_corrupt_json(self):
        self.session_file.write_text("not valid json", encoding="utf-8")
        with patch("src.auth.Config.SESSION_FILE", self.session_file):
            result = self.auth.get_session()
        self.assertIsNone(result)

    def test_save_session_creates_file(self):
        data = {"token": "tok"}
        with patch("src.auth.Config.SESSION_FILE", self.session_file):
            self.auth.save_session(data)
        self.assertTrue(self.session_file.exists())
        stored = json.loads(self.session_file.read_text())
        self.assertEqual(stored["token"], "tok")

    def test_authenticate_exits_on_server_error(self):
        with patch("src.auth.requests.post", side_effect=Exception("connection refused")):
            with self.assertRaises(SystemExit):
                self.auth.authenticate("ssh-ed25519 AAAA...")

    def test_authenticate_polls_until_success(self):
        device_resp = MagicMock()
        device_resp.json.return_value = {
            "device_code": "dc123",
            "verification_url": "https://accounts.google.com/device",
            "user_code": "ABCD-1234",
            "interval": 0,
        }
        pending_resp = MagicMock()
        pending_resp.status_code = 202
        pending_resp.json.return_value = {"error": "authorization_pending"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"email": "user@example.com", "token": "tok99"}

        with patch("src.auth.requests.post", side_effect=[device_resp, pending_resp, success_resp]):
            with patch("src.auth.Config.SESSION_FILE", self.session_file):
                with patch("src.auth.time.sleep"):
                    result = self.auth.authenticate("ssh-ed25519 AAAA...")

        self.assertEqual(result["email"], "user@example.com")

    def test_authenticate_exits_on_auth_failure(self):
        device_resp = MagicMock()
        device_resp.json.return_value = {
            "device_code": "dc123",
            "verification_url": "https://accounts.google.com/device",
            "user_code": "ABCD-1234",
            "interval": 0,
        }
        fail_resp = MagicMock()
        fail_resp.status_code = 400
        fail_resp.json.return_value = {"error": "access_denied"}

        with patch("src.auth.requests.post", side_effect=[device_resp, fail_resp]):
            with patch("src.auth.Config.SESSION_FILE", self.session_file):
                with self.assertRaises(SystemExit):
                    self.auth.authenticate("ssh-ed25519 AAAA...")
