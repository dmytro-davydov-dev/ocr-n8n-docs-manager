import unittest

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


class InternalApiAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_internal_ping_requires_api_key(self) -> None:
        response = self.client.get("/api/internal/ping")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid internal API key")

    def test_internal_ping_accepts_valid_api_key(self) -> None:
        response = self.client.get(
            "/api/internal/ping",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "scope": "internal"})


if __name__ == "__main__":
    unittest.main()