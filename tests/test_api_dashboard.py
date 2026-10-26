"""Tests for Dashboard API endpoints."""

import asyncio
import unittest
from httpx import ASGITransport, AsyncClient
from app.main import api


class TestDashboardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.database import init_db
        init_db()

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_health(self):
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                response = await client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ok")
        self.run_async(_test())

    def test_login_and_overview(self):
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                # 1. Login with seeded admin credentials
                login_resp = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                self.assertEqual(login_resp.status_code, 200)
                data = login_resp.json()
                self.assertIn("access_token", data)
                token = data["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 2. Get me
                me_resp = await client.get("/api/dashboard/auth/me", headers=headers)
                self.assertEqual(me_resp.status_code, 200)
                self.assertEqual(me_resp.json()["username"], "admin")

                # 3. Overview
                ov_resp = await client.get("/api/dashboard/overview", headers=headers)
                self.assertEqual(ov_resp.status_code, 200)
                ov_data = ov_resp.json()
                self.assertIn("total_contents", ov_data)
                self.assertIn("platforms", ov_data)
                self.assertIn("sentiments", ov_data)

                # 4. Trending list
                tr_resp = await client.get("/api/dashboard/trending", headers=headers)
                self.assertEqual(tr_resp.status_code, 200)
                self.assertIsInstance(tr_resp.json(), list)

                # 5. Contents list
                cnt_resp = await client.get("/api/dashboard/contents", headers=headers)
                self.assertEqual(cnt_resp.status_code, 200)
                self.assertIsInstance(cnt_resp.json(), list)

        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
