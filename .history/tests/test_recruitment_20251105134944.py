import os
import unittest
from unittest.mock import MagicMock, patch

import requests

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


if __name__ == "__main__":
    unittest.main()
