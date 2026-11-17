"""Tests for Dashboard API endpoints."""

import os
import sys
import unittest
import asyncio
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, SessionLocal
from app.main import health
from app.models.intelligence import DashboardUser
from app.schemas.dashboard import LoginRequest
from app.api.dashboard.auth import login, get_current_user_profile
from app.api.dashboard.overview import get_dashboard_overview
from app.api.dashboard.trending import list_trending_topics
from app.api.dashboard.contents import list_contents


class TestDashboardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_health(self):
        coro = health()
        try:
            coro.send(None)
            res = {}
        except StopIteration as e:
            res = e.value
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("service"), "cyber-patrol-assistant")

    def test_login_and_overview(self):
        # 1. Login with seeded admin credentials
        req = MagicMock()
        req.client.host = "127.0.0.1"
        payload = LoginRequest(username="admin", password="patroladmin2026")
        token_res = login(payload=payload, request=req, db=self.db)
        self.assertTrue(token_res.access_token)
        self.assertEqual(token_res.user.username, "admin")

        # 2. Get me profile
        admin_user = self.db.query(DashboardUser).filter(DashboardUser.username == "admin").first()
        self.assertIsNotNone(admin_user)
        me_res = get_current_user_profile(current_user=admin_user)
        self.assertEqual(me_res.username, "admin")
        self.assertEqual(me_res.role, "ADMIN")

        # 3. Overview stats
        ov_res = get_dashboard_overview(db=self.db, current_user=admin_user)
        self.assertIsNotNone(ov_res.total_contents)
        self.assertIsInstance(ov_res.platforms, list)
        self.assertIsInstance(ov_res.sentiments, list)

        # 4. Trending list
        tr_res = list_trending_topics(
            category=None,
            search=None,
            status="ALL",
            limit=50,
            db=self.db,
            current_user=admin_user,
        )
        self.assertIsInstance(tr_res, list)

        # 5. Contents list
        cnt_res = list_contents(
            platform=None,
            category=None,
            sentiment=None,
            risk_level=None,
            status=None,
            search=None,
            skip=0,
            limit=25,
            db=self.db,
            current_user=admin_user,
        )
        self.assertIsInstance(cnt_res, list)


if __name__ == "__main__":
    unittest.main()

