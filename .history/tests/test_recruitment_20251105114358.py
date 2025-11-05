import unittest
from unittest.mock import MagicMock, patch

import requests

import recruitment


class TestRecruitment(unittest.TestCase):
    def test_send_tg_dry_run(self):
        session = requests.Session()
        resp = recruitment.send_tg(session, "nation_test", "client", "tgid", "secret", dry_run=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "dry-run")

    @patch("recruitment.requests.Session.post")
    def test_send_tg_network_call(self, mock_post):
        # simulate a real response object
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b"OK"
        mock_post.return_value = mock_response

        session = requests.Session()
        # Use the session.post via the session object; patch ensures it returns our mock
        resp = recruitment.send_tg(session, "nation_real", "client", "tgid", "secret", dry_run=False)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "OK")


if __name__ == "__main__":
    unittest.main()
