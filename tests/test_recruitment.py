import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import requests
from requests.adapters import HTTPAdapter

import recruitment


class TestRecruitment(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures with required environment variables."""
        self.env_patcher = patch.dict(
            os.environ,
            {
                "NS_CLIENT_KEY": "test_client",
                "NS_TGID": "test_tgid",
                "NS_SECRET_KEY": "test_secret",
            },
        )
        self.env_patcher.start()
        # Reload the module to pick up patched environment variables
        import importlib
        importlib.reload(recruitment)

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    def test_send_tg_dry_run(self):
        session = requests.Session()
        resp = recruitment.send_tg(session, "nation_test", dry_run=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"dry-run")

    @patch("recruitment.requests.Session.post")
    def test_send_tg_network_call(self, mock_post):
        # Simulate a real response object
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b"OK"
        mock_post.return_value = mock_response

        session = requests.Session()
        # Call send_tg with correct signature (no client/tgid/secret args)
        resp = recruitment.send_tg(session, "nation_real", dry_run=False)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "OK")

    def test_make_session_creates_adapter(self):
        """Test that make_session creates a session with HTTPAdapter configured."""
        session = recruitment.make_session(retries=3, backoff_factor=0.5)
        
        self.assertIsInstance(session, requests.Session)
        # Check that HTTPS adapter is an HTTPAdapter with retries
        adapter = session.get_adapter("https://www.example.com")
        self.assertIsInstance(adapter, HTTPAdapter)
        # Verify max_retries is set (it's a Retry object)
        self.assertIsNotNone(adapter.max_retries)

    def test_make_session_user_agent_header(self):
        """Test that make_session sets the User-Agent header."""
        session = recruitment.make_session()
        user_agent = session.headers.get("User-Agent")
        self.assertIsNotNone(user_agent)
        # Default should be WalbardRecruitBot unless env var is set
        self.assertIn("Recruit", user_agent)

    def test_send_tg_missing_env_vars(self):
        """Test that send_tg returns None when env vars are missing."""
        with patch.dict(os.environ, {"NS_CLIENT_KEY": "", "NS_TGID": "", "NS_SECRET_KEY": ""}):
            import importlib
            importlib.reload(recruitment)
            session = requests.Session()
            resp = recruitment.send_tg(session, "nation_test", dry_run=False)
            self.assertIsNone(resp)

    @patch("recruitment.requests.Session.post")
    def test_send_tg_request_exception(self, mock_post):
        """Test that send_tg handles network exceptions gracefully."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        session = requests.Session()
        resp = recruitment.send_tg(session, "nation_error", dry_run=False)
        self.assertIsNone(resp)

    @patch("recruitment.requests.Session.post")
    def test_send_tg_http_error(self, mock_post):
        """Test that send_tg handles HTTP errors (non-2xx status codes)."""
        mock_response = requests.Response()
        mock_response.status_code = 500
        mock_response._content = b"Internal Server Error"
        mock_post.return_value = mock_response
        
        session = requests.Session()
        resp = recruitment.send_tg(session, "nation_error", dry_run=False)
        # send_tg calls raise_for_status() which raises on 5xx
        self.assertIsNone(resp)

    def test_load_targets_basic(self):
        """Test that load_targets reads lines correctly."""
        with patch("recruitment.os.path.exists", return_value=True):
            with patch("builtins.open", unittest.mock.mock_open(read_data="nation1\nnation2\n")):
                targets = recruitment.load_targets()
                self.assertEqual(targets, ["nation1", "nation2"])

    def test_load_targets_with_comments(self):
        """Test that load_targets filters comment lines."""
        with patch("recruitment.os.path.exists", return_value=True):
            content = "# Comment\nnation1\n# Another comment\nnation2\n"
            with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
                targets = recruitment.load_targets()
                self.assertEqual(targets, ["nation1", "nation2"])

    def test_load_targets_with_whitespace(self):
        """Test that load_targets strips whitespace."""
        with patch("recruitment.os.path.exists", return_value=True):
            content = "  nation1  \n\n  nation2\t\n"
            with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
                targets = recruitment.load_targets()
                self.assertEqual(targets, ["nation1", "nation2"])

    def test_load_targets_file_not_found(self):
        """Test that load_targets returns empty list if file doesn't exist."""
        with patch("recruitment.os.path.exists", return_value=False):
            targets = recruitment.load_targets()
            self.assertEqual(targets, [])

    def test_normalize_region_name(self):
        self.assertEqual(recruitment.normalize_region_name(" New United Kingdom "), "new_united_kingdom")
        self.assertEqual(recruitment.normalize_region_name(None), "")

    def test_load_region_campaigns_active(self):
        payload = {
            "campaigns": [
                {
                    "tag": "britannia_push",
                    "regions": ["Britannia", "New United Kingdom"],
                    "starts_at": "2025-11-22T00:00:00Z",
                    "ends_at": "2025-11-30T23:59:59Z",
                }
            ]
        }
        tmp = tempfile.NamedTemporaryFile("w", delete=False)
        try:
            tmp.write(json.dumps(payload))
            tmp.flush()
            tmp.close()
            with patch("recruitment.REGION_CAMPAIGNS_FILE", tmp.name):
                campaigns = recruitment.load_region_campaigns(now=datetime(2025, 11, 25, tzinfo=timezone.utc))
        finally:
            os.remove(tmp.name)

        self.assertEqual(campaigns.get("britannia"), "britannia_push")
        self.assertEqual(campaigns.get("new_united_kingdom"), "britannia_push")

    def test_load_region_campaigns_expired(self):
        payload = {
            "campaigns": [
                {
                    "tag": "old_campaign",
                    "regions": ["Kingdom of Britannia"],
                    "ends_at": "2025-11-01T00:00:00Z",
                }
            ]
        }
        tmp = tempfile.NamedTemporaryFile("w", delete=False)
        try:
            tmp.write(json.dumps(payload))
            tmp.flush()
            tmp.close()
            with patch("recruitment.REGION_CAMPAIGNS_FILE", tmp.name):
                campaigns = recruitment.load_region_campaigns(now=datetime(2025, 11, 25, tzinfo=timezone.utc))
        finally:
            os.remove(tmp.name)

        self.assertEqual(campaigns, {})


if __name__ == "__main__":
    unittest.main()
