import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestTunnelManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tunnels_file = Path(self.tmpdir.name) / "tunnels.json"
        from src.tunnel import TunnelManager
        self.manager = TunnelManager()

    def tearDown(self):
        self.tmpdir.cleanup()

    # --- load / save ---

    def test_load_returns_empty_dict_when_file_missing(self):
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            result = self.manager.load()
        self.assertEqual(result, {})

    def test_save_and_load_roundtrip(self):
        data = {"1234": {"local_port": 8080, "url": "https://test.natnest.site"}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            result = self.manager.load()
        self.assertEqual(result, data)

    def test_load_handles_corrupt_json(self):
        self.tunnels_file.write_text("corrupted", encoding="utf-8")
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            result = self.manager.load()
        self.assertEqual(result, {})

    def test_save_writes_valid_json(self):
        data = {"99": {"local_port": 3000}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
        stored = json.loads(self.tunnels_file.read_text())
        self.assertEqual(stored, data)

    # --- is_pid_running ---

    def test_is_pid_running_for_current_process(self):
        self.assertTrue(self.manager.is_pid_running(os.getpid()))

    def test_is_pid_running_for_nonexistent_pid(self):
        self.assertFalse(self.manager.is_pid_running(99999999))

    # --- clean_dead ---

    def test_clean_dead_keeps_running_pids(self):
        data = {str(os.getpid()): {"local_port": 8080, "url": "https://a.natnest.site"}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            result = self.manager.clean_dead()
        self.assertIn(str(os.getpid()), result)

    def test_clean_dead_removes_dead_pids(self):
        data = {
            str(os.getpid()): {"local_port": 8080, "url": "https://a.natnest.site"},
            "99999999": {"local_port": 9090, "url": "https://b.natnest.site"},
        }
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            result = self.manager.clean_dead()
        self.assertIn(str(os.getpid()), result)
        self.assertNotIn("99999999", result)

    def test_clean_dead_saves_after_removing_dead(self):
        data = {"99999999": {"local_port": 9090, "url": "https://b.natnest.site"}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            self.manager.clean_dead()
            result = self.manager.load()
        self.assertEqual(result, {})

    def test_clean_dead_empty_tunnels(self):
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            result = self.manager.clean_dead()
        self.assertEqual(result, {})

    # --- stop ---

    def test_stop_prints_no_tunnels_when_empty(self):
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            with patch("builtins.print") as mock_print:
                self.manager.stop("all")
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No active", printed)

    def test_stop_all_kills_all_tunnels(self):
        data = {"99999999": {"local_port": 8080, "url": "https://a.natnest.site"}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            with patch("src.tunnel._kill_process") as mock_kill:
                self.manager.stop("all")
            result = self.manager.load()
        self.assertEqual(result, {})

    def test_stop_by_port_kills_matching_tunnel(self):
        data = {
            "11111": {"local_port": 8080, "url": "https://a.natnest.site"},
            "22222": {"local_port": 9090, "url": "https://b.natnest.site"},
        }
        # Patch clean_dead so fake PIDs are not removed before stop() acts on them
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            with patch.object(self.manager, "clean_dead", return_value=data):
                with patch("src.tunnel._kill_process"):
                    self.manager.stop("8080")
            result = self.manager.load()
        self.assertNotIn("11111", result)
        self.assertIn("22222", result)

    def test_stop_nonexistent_port_prints_warning(self):
        data = {"11111": {"local_port": 8080, "url": "https://a.natnest.site"}}
        with patch("src.tunnel.Config.TUNNELS_FILE", self.tunnels_file):
            self.manager.save(data)
            with patch.object(self.manager, "clean_dead", return_value=data):
                with patch("src.tunnel._kill_process"):
                    with patch("builtins.print") as mock_print:
                        self.manager.stop("3000")
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No tunnel", printed)
