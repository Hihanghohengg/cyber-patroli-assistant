"""Unit tests for RAG Knowledge Base, Entity Normalization, and v1 Dashboard & Admin APIs."""

import asyncio
import unittest
from uuid import uuid4
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from app.main import api
from app.database import SessionLocal, init_db
from app.models.report import Report, Content, Account
from app.services.entity_service import EntityService
from app.services.rag_service import RAGService


class TestRAGAndEntityServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.entity_svc = EntityService()
        self.rag_svc = RAGService()

    def tearDown(self):
        self.db.close()

    def test_entity_normalization_and_exact_match(self):
        """Test entity creation and exact matching via aliases."""
        topic1 = self.entity_svc.get_or_create_topic(self.db, "Judi Slot Gacor")
        self.assertIsNotNone(topic1)
        self.assertEqual(topic1.entity_type, "TOPIC")

        # Second lookup with different casing/spacing should match exact canonical alias
        topic2 = self.entity_svc.get_or_create_topic(self.db, "  judi slot gacor  ")
        self.assertEqual(topic1.entity_id, topic2.entity_id)

    def test_entity_fuzzy_match(self):
        """Test fuzzy matching for minor typographic variations."""
        ent1 = self.entity_svc.get_or_create_actor(self.db, "Kementerian Komunikasi dan Digital")
        self.assertIsNotNone(ent1)

        # Slight variation (> 0.85 similarity)
        ent2 = self.entity_svc.get_or_create_actor(self.db, "Kementrian Komunikasi dan Digital")
        self.assertEqual(ent1.entity_id, ent2.entity_id)

    def test_entity_approval_and_merge(self):
        """Test approving and merging duplicate entities."""
        source = self.entity_svc.get_or_create_topic(self.db, "Kasino Online 88")
        target = self.entity_svc.get_or_create_topic(self.db, "Judi Kasino Daring")

        # Approve target
        self.entity_svc.approve_entity(self.db, target.entity_id)
        self.db.refresh(target)
        self.assertEqual(target.status, "APPROVED")

        # Merge source into target
        merged = self.entity_svc.merge_entities(self.db, source.entity_id, target.entity_id)
        self.assertEqual(merged.entity_id, target.entity_id)

        self.db.refresh(source)
        self.assertEqual(source.status, "MERGED")
        self.assertEqual(source.merged_into_id, target.entity_id)

    def test_rag_fail_open_when_empty(self):
        """Test RAG similarity search returns empty string gracefully when no cases exist."""
        context = self.rag_svc.retrieve_similar_cases(
            db=self.db,
            text="Temuan konten baru yang mencurigakan",
            top_k=3,
        )
        self.assertEqual(context, "")

    def test_rag_prompt_block_formatting(self):
        """Test prompt block formatting with reference cases and strict disclaimer."""
        cases = [
            {
                "ticket": "PS-20261023-A01",
                "similarity": 0.88,
                "verified_label": "JUDI_ONLINE",
                "verified_risk": "TINGGI",
                "analyst_notes": "Promosi situs judi via bio",
                "content_snippet": "Main slot modal receh menang jutaan rupiah",
            }
        ]
        block = self.rag_svc.format_rag_prompt_block(cases)
        self.assertIn("KASUS PRESEDEN HISTORIS", block)
        self.assertIn("PS-20261023-A01", block)
        self.assertIn("JUDI_ONLINE", block)
        self.assertIn("PENTING:", block)

    def test_create_knowledge_entry(self):
        """Test creating knowledge entry from a validated report."""
        uname = f"user_{uuid4().hex[:6]}"
        account = Account(
            platform="tiktok",
            username=uname,
            profile_url=f"https://tiktok.com/@{uname}",
        )
        self.db.add(account)
        self.db.flush()

        content = Content(
            account_id=account.account_id,
            platform="tiktok",
            canonical_url=f"https://tiktok.com/@user/video/{uuid4().hex[:8]}",
            caption_text="Main slot modal receh menang puluhan juta",
        )
        self.db.add(content)
        self.db.flush()

        # Create a valid report
        report = Report(
            ticket_number=f"PS-TEST-{uuid4().hex[:6]}",
            reporter_telegram_id=123456789,
            content_id=content.content_id,
            ai_predicted_label="JUDI_ONLINE",
            ai_risk_level="TINGGI",
            final_label="JUDI_ONLINE",
            final_risk="TINGGI",
            review_decision="APPROVED",
            analyst_notes="Terbukti mempromosikan situs slot",
            status="VALIDATED",
        )
        self.db.add(report)
        self.db.commit()

        fake_vector = [0.05] * 768
        with patch.object(self.rag_svc, "generate_embedding", return_value=fake_vector):
            entry = self.rag_svc.create_knowledge_entry(self.db, report)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.ticket_number, report.ticket_number)
            self.assertEqual(entry.verified_category, "JUDI_ONLINE")


class TestV1APIEndpoints(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def test_v1_dashboard_and_admin_endpoints(self):
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                # 1. Login
                login_resp = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                self.assertEqual(login_resp.status_code, 200)
                token = login_resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 2. GET /api/v1/dashboard/summary
                sum_resp = await client.get("/api/v1/dashboard/summary", headers=headers)
                self.assertEqual(sum_resp.status_code, 200)
                sum_data = sum_resp.json()
                self.assertIn("total_laporan", sum_data)
                self.assertIn("distribusi_kategori", sum_data)
                self.assertIn("distribusi_risiko", sum_data)
                self.assertIn("rasio_persetujuan_ai", sum_data)

                # 3. GET /api/v1/dashboard/timeseries
                ts_resp = await client.get("/api/v1/dashboard/timeseries", headers=headers)
                self.assertEqual(ts_resp.status_code, 200)
                ts_data = ts_resp.json()
                self.assertIn("series", ts_data)

                # 4. GET /api/v1/dashboard/breakdown
                bk_resp = await client.get("/api/v1/dashboard/breakdown?dimension=category", headers=headers)
                self.assertEqual(bk_resp.status_code, 200)
                self.assertIn("items", bk_resp.json())

                # 5. GET /api/v1/dashboard/top
                top_topics_resp = await client.get("/api/v1/dashboard/top?dimension=topics", headers=headers)
                self.assertEqual(top_topics_resp.status_code, 200)
                top_data = top_topics_resp.json()
                self.assertIn("disclaimer", top_data)
                self.assertIn("items", top_data)

                top_actors_resp = await client.get("/api/v1/dashboard/top?dimension=actors", headers=headers)
                self.assertEqual(top_actors_resp.status_code, 200)
                self.assertIn("disclaimer", top_actors_resp.json())

                top_sources_resp = await client.get("/api/v1/dashboard/top?dimension=sources", headers=headers)
                self.assertEqual(top_sources_resp.status_code, 200)
                self.assertIn("disclaimer", top_sources_resp.json())

                # 6. GET /api/v1/dashboard/reports
                rep_resp = await client.get("/api/v1/dashboard/reports", headers=headers)
                self.assertEqual(rep_resp.status_code, 200)
                self.assertIn("items", rep_resp.json())

                # 7. GET /api/v1/dashboard/export (CSV)
                exp_resp = await client.get("/api/v1/dashboard/export?format=csv", headers=headers)
                self.assertEqual(exp_resp.status_code, 200)
                self.assertEqual(exp_resp.headers["content-type"], "text/csv; charset=utf-8")
                self.assertIn("Ticket Number", exp_resp.text)

                # 8. Admin Knowledge Base
                kn_resp = await client.get("/api/v1/admin/knowledge", headers=headers)
                self.assertEqual(kn_resp.status_code, 200)
                self.assertIn("items", kn_resp.json())

                # 9. Admin Entities
                ent_resp = await client.get("/api/v1/admin/entities", headers=headers)
                self.assertEqual(ent_resp.status_code, 200)
                self.assertIn("items", ent_resp.json())

                # 10. Admin Users
                usr_resp = await client.get("/api/v1/admin/users", headers=headers)
                self.assertEqual(usr_resp.status_code, 200)
                self.assertIsInstance(usr_resp.json(), list)

                # 11. Admin Audit
                aud_resp = await client.get("/api/v1/admin/audit", headers=headers)
                self.assertEqual(aud_resp.status_code, 200)
                self.assertIn("items", aud_resp.json())

        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
