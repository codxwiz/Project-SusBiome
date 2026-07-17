from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.api.routers.contact import (
    ContactRequest,
    SMTPConfiguration,
    _email_message,
    router,
)

app = FastAPI()
app.include_router(router, prefix="/api")


class ContactAPITest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.payload = {
            "name": "Test Farmer",
            "phone": "+91 98765 43210",
            "email": "farmer@example.com",
            "address": "Imphal East, Manipur",
            "message": "Please contact me about a farm assessment.",
            "website": "",
        }

    def test_message_targets_susbiome_inbox(self) -> None:
        config = SMTPConfiguration(
            host="smtp.gmail.com",
            port=587,
            username="susbiome098@gmail.com",
            password="test-password",
            sender="susbiome098@gmail.com",
            recipient="susbiome098@gmail.com",
            use_ssl=False,
        )
        message = _email_message(ContactRequest(**self.payload), config)

        self.assertEqual(message["To"], "susbiome098@gmail.com")
        self.assertEqual(message["Reply-To"], "farmer@example.com")
        self.assertIn("Test Farmer", message.get_content())

    def test_invalid_email_is_rejected(self) -> None:
        response = self.client.post(
            "/api/contact",
            json={**self.payload, "email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 422)

    def test_missing_smtp_configuration_is_unavailable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/api/contact", json=self.payload)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Contact service is unavailable.")

    @patch("scripts.api.routers.contact._send_email")
    def test_successful_submission_is_accepted(self, send_email) -> None:
        environment = {
            "SUSBIOME_SMTP_USERNAME": "susbiome098@gmail.com",
            "SUSBIOME_SMTP_PASSWORD": "test-app-password",
            "SUSBIOME_CONTACT_TO": "susbiome098@gmail.com",
        }
        with patch.dict(os.environ, environment, clear=False):
            response = self.client.post("/api/contact", json=self.payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"accepted": True})
        send_email.assert_called_once()

    @patch("scripts.api.routers.contact._send_email")
    def test_spam_trap_is_silently_accepted(self, send_email) -> None:
        response = self.client.post(
            "/api/contact",
            json={**self.payload, "website": "https://spam.example"},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"accepted": True})
        send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
