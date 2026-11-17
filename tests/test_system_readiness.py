"""Comprehensive System Readiness and End-to-End Logic Verification Test Suite.

Verifies:
1. System Health & Database Initialisation
2. Authentication (JWT token issuance, user roles, invalid credentials rejection)
3. Omnichannel Intake Pipeline (/api/v1/assistant/intake) with rich metadata, 5W+1H extraction,
   forensic evidence acquisition, smart trending clustering, and audit logging
4. SSRF & Malicious URL Prevention (RFC 1918 private IPs, loopback, file/ftp schemes)
5. Content Explorer & Forensic Evidence Verification
6. Human-in-the-Loop (HITL) Validation/Curation & Knowledge Base Indexing
7. Radar Trending Topics & Issue Cluster Detail synthesis
8. Analytics Aggregation & CSV Export
9. Security Headers & Path Traversal Protections
"""

import asyncio
import base64
import os
import unittest
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.main import api
from app.database import SessionLocal, init_db
from app.models.report import Report, Content, Account
from app.models.intelligence import ContentAnalysis, IssueCluster, IssueContent
from app.models.evidence import Evidence
from app.models.audit import AuditLog
from app.models.knowledge import KnowledgeEntry


class TestSystemReadiness(unittest.TestCase):
    """End-to-End verification of operational readiness."""

    @classmethod
    def setUpClass(cls):
        init_db()

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_01_system_health(self):
        """Verify API health check endpoint responds with 200 OK and expected structure."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                resp = await client.get("/health")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["status"], "ok")
                self.assertEqual(data["service"], "cyber-patrol-assistant")
                self.assertIn("timestamp", data)
        self.run_async(_test())

    def test_02_authentication_and_authorization(self):
        """Verify login, token generation, user profile, and invalid credential handling."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                # 1. Valid login
                login_resp = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                self.assertEqual(login_resp.status_code, 200)
                auth_data = login_resp.json()
                self.assertIn("access_token", auth_data)
                self.assertEqual(auth_data["token_type"], "bearer")

                token = auth_data["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 2. Authenticated /me endpoint
                me_resp = await client.get("/api/dashboard/auth/me", headers=headers)
                self.assertEqual(me_resp.status_code, 200)
                me_data = me_resp.json()
                self.assertEqual(me_data["username"], "admin")
                self.assertEqual(me_data["role"], "ADMIN")

                # 3. Invalid login rejection
                bad_login = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "wrongpassword!"},
                )
                self.assertEqual(bad_login.status_code, 401)
                self.assertIn("detail", bad_login.json())

                # 4. Unauthorized access rejection
                unauth_resp = await client.get("/api/dashboard/overview")
                self.assertEqual(unauth_resp.status_code, 401)
        self.run_async(_test())

    def test_03_ssrf_and_malicious_url_prevention(self):
        """Verify that SSRF attempts and illegal URL schemes are blocked at intake."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                malicious_urls = [
                    "http://127.0.0.1:8000/api/dashboard",
                    "http://localhost:5432/patrol_db",
                    "http://169.254.169.254/latest/meta-data/",
                    "http://10.0.0.1/admin",
                    "http://192.168.1.1/router",
                    "file:///etc/passwd",
                    "ftp://malicious.com/payload",
                ]
                for bad_url in malicious_urls:
                    resp = await client.post(
                        "/api/v1/assistant/intake",
                        json={
                            "url": bad_url,
                            "source_channel": "BROWSER_EXTENSION",
                            "reporter_identifier": "Sec-Test",
                        },
                    )
                    self.assertEqual(
                        resp.status_code,
                        400,
                        f"Expected 400 Bad Request for SSRF probe {bad_url}, got {resp.status_code}",
                    )
                    self.assertIn("detail", resp.json())
        self.run_async(_test())

    def test_04_intake_pipeline_end_to_end(self):
        """Verify end-to-end intake with rich metadata, 5W+1H synthesis, evidence, and trending cluster."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                # 1x1 transparent PNG base64 for test evidence
                dummy_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

                payload = {
                    "url": "https://www.youtube.com/watch?v=k_integration_test_mbg_001",
                    "source_channel": "BROWSER_EXTENSION",
                    "reporter_identifier": "Inspector-Clouseau",
                    "title": "Evaluasi Program MBG Nasional: BGN Tindak Tegas Penyelewengan Dana",
                    "caption": "Badan Gizi Nasional (BGN) menindaklanjuti dugaan penyelewengan dana pengadaan MBG di berbagai daerah karena adanya indikasi markup harga dan kualitas makanan tidak sesuai standar.",
                    "transcript": "Kepala BGN menegaskan bahwa kami tidak akan mentolerir adanya pemotongan dana makan bergizi gratis. Semua titik distribusi harus diawasi ketat oleh aparat penegak hukum dan inspektorat jenderal.",
                    "username": "portal_berita_resmi",
                    "display_name": "Portal Berita Terpercaya",
                    "followers_count": 500000,
                    "likes_count": 1250,
                    "views_count": 45000,
                    "comments_count": 320,
                    "screenshot_base64": dummy_png_b64,
                }

                resp = await client.post("/api/v1/assistant/intake", json=payload)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["status"], "QUEUED")
                self.assertTrue(data["ticket_number"].startswith("PS-"))
                self.assertIn("content_id", data)
                self.assertIn("dashboard_url", data)

                content_id = UUID(data["content_id"])

                # Verify database records
                db = SessionLocal()
                try:
                    # Content
                    c = db.query(Content).filter(Content.content_id == content_id).first()
                    self.assertIsNotNone(c)
                    self.assertEqual(c.platform, "youtube")
                    self.assertEqual(c.likes_count, 1250)
                    self.assertEqual(c.views_count, 45000)

                    # Report
                    r = db.query(Report).filter(Report.content_id == content_id).first()
                    self.assertIsNotNone(r)
                    self.assertEqual(r.ticket_number, data["ticket_number"])
                    self.assertEqual(r.source_channel, "BROWSER_EXTENSION")
                    self.assertEqual(r.status, Report.STATUS_WAITING_VALIDATION)

                    # 5W+1H ContentAnalysis
                    a = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == content_id).first()
                    self.assertIsNotNone(a)
                    self.assertIn("MBG", a.what)
                    self.assertIn("portal_berita_resmi", a.who)
                    self.assertTrue(a.when_info.startswith("Dipublikasikan"))
                    self.assertTrue(a.where_info.startswith("Platform YOUTUBE"))
                    self.assertTrue(len(a.why) > 15)  # Substantive why from caption/transcript
                    self.assertTrue(len(a.how) > 15)  # Substantive how from transcript
                    # Smart trending topic check (Twitter/Threads style)
                    self.assertIn("MBG", a.main_topic)

                    # Evidence
                    ev = db.query(Evidence).filter(Evidence.report_id == r.report_id).first()
                    self.assertIsNotNone(ev)
                    self.assertEqual(ev.source_type, "POST_SCREENSHOT")
                    self.assertTrue(os.path.exists(ev.storage_path))
                    self.assertEqual(len(ev.sha256), 64)

                    # IssueCluster assignment
                    junction = db.query(IssueContent).filter(IssueContent.content_id == content_id).first()
                    self.assertIsNotNone(junction)
                    cluster = db.query(IssueCluster).filter(IssueCluster.issue_id == junction.issue_id).first()
                    self.assertIsNotNone(cluster)
                    self.assertTrue(len(cluster.canonical_name) > 0)
                    # Check that slug is clean (no spaces, all lowercase/dashes)
                    self.assertEqual(cluster.canonical_name, cluster.canonical_name.lower())
                    self.assertNotIn(" ", cluster.canonical_name)

                    # AuditLog
                    audit = db.query(AuditLog).filter(
                        AuditLog.action == "REPORT_INTAKE_SUBMITTED",
                        AuditLog.entity_id == str(r.report_id),
                    ).first()
                    self.assertIsNotNone(audit)
                finally:
                    db.close()

        self.run_async(_test())

    def test_05_content_explorer_and_detail(self):
        """Verify content listing, detailed 5W+1H view, and evidence verification."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                # Login
                login = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                token = login.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 1. List contents
                list_resp = await client.get("/api/dashboard/contents?limit=10", headers=headers)
                self.assertEqual(list_resp.status_code, 200)
                items = list_resp.json()
                self.assertIsInstance(items, list)
                self.assertGreater(len(items), 0)

                target_item = items[0]
                target_id = target_item["content_id"]

                # 2. Get content detail
                det_resp = await client.get(f"/api/dashboard/contents/{target_id}", headers=headers)
                self.assertEqual(det_resp.status_code, 200)
                det = det_resp.json()
                self.assertEqual(det["content_id"], target_id)
                self.assertIn("analysis_5w1h", det)
                self.assertIn("author", det)
                self.assertIn("interaction", det)
                self.assertIn("evidences", det)

                # 3. Get content screenshot
                img_resp = await client.get(f"/api/dashboard/contents/{target_id}/screenshot")
                self.assertEqual(img_resp.status_code, 200)
                self.assertEqual(img_resp.headers["content-type"], "image/png")

                # 4. Verify forensic evidence hash
                ver_resp = await client.get(f"/api/dashboard/contents/{target_id}/verify-evidence")
                self.assertEqual(ver_resp.status_code, 200)
                ver_data = ver_resp.json()
                self.assertIn("status", ver_data)
                self.assertIn("registered_sha256", ver_data)
                self.assertIn("current_file_sha256", ver_data)
                self.assertEqual(ver_data["registered_sha256"], ver_data["current_file_sha256"])
        self.run_async(_test())

    def test_06_human_in_the_loop_validation_and_rag_sync(self):
        """Verify analyst validation decisions, mandatory notes constraints, and Knowledge Base ingestion."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                login = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                token = login.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # Get a pending content
                db = SessionLocal()
                pending_rep = db.query(Report).filter(Report.status == Report.STATUS_WAITING_VALIDATION).first()
                self.assertIsNotNone(pending_rep, "Expected at least one pending report for validation test")
                content_id = str(pending_rep.content_id)
                db.close()

                # Constraint check: REJECTED without notes must fail with 400
                bad_val = await client.post(
                    f"/api/dashboard/contents/{content_id}/validate",
                    headers=headers,
                    json={
                        "status": "REJECTED",
                        "notes": "",
                    },
                )
                self.assertEqual(bad_val.status_code, 400)
                self.assertIn("Catatan analis", bad_val.json()["detail"])

                # Valid decision: VALIDATED
                val_resp = await client.post(
                    f"/api/dashboard/contents/{content_id}/validate",
                    headers=headers,
                    json={
                        "status": "VALIDATED",
                        "category_override": "Politik",
                        "risk_level_override": "SEDANG",
                        "notes": "Terbukti terdapat perbincangan publik signifikan terkait evaluasi program.",
                    },
                )
                self.assertEqual(val_resp.status_code, 200)
                self.assertEqual(val_resp.json()["status"], "success")

                # Verify database update
                db = SessionLocal()
                try:
                    rep_updated = db.query(Report).filter(Report.content_id == UUID(content_id)).first()
                    self.assertEqual(rep_updated.status, "MODIFIED")  # Overrode category/risk -> MODIFIED
                    self.assertEqual(rep_updated.final_label, "Politik")
                    self.assertEqual(rep_updated.final_risk, "SEDANG")
                    self.assertIsNotNone(rep_updated.validated_at)

                    # Verify RAG Knowledge Base entry was automatically created
                    kb_entry = db.query(KnowledgeEntry).filter(
                        KnowledgeEntry.report_id == rep_updated.report_id,
                        KnowledgeEntry.is_active.is_(True),
                    ).first()
                    self.assertIsNotNone(kb_entry)
                    self.assertEqual(kb_entry.final_label, "Politik")
                finally:
                    db.close()
        self.run_async(_test())

    def test_07_radar_trending_and_detail(self):
        """Verify trending topics radar listing and aggregated issue synthesis."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                login = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                token = login.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 1. Trending list
                tr_resp = await client.get("/api/dashboard/trending?status=ACTIVE", headers=headers)
                self.assertEqual(tr_resp.status_code, 200)
                clusters = tr_resp.json()
                self.assertIsInstance(clusters, list)
                self.assertGreater(len(clusters), 0)

                # Check Twitter/Threads-like properties
                first_cluster = clusters[0]
                self.assertIn("canonical_name", first_cluster)
                self.assertIn("trending_score", first_cluster)
                self.assertIn("top_keywords", first_cluster)
                issue_id = first_cluster["issue_id"]

                # 2. Issue detail
                det_resp = await client.get(f"/api/dashboard/trending/{issue_id}", headers=headers)
                self.assertEqual(det_resp.status_code, 200)
                issue_det = det_resp.json()
                self.assertIn("issue", issue_det)
                self.assertEqual(issue_det["issue"]["issue_id"], issue_id)
                self.assertIn("w5h1_summary", issue_det)
                self.assertIn("timeline", issue_det)
                self.assertIn("keywords", issue_det)
                self.assertIn("sources", issue_det)

                # 3. Issue contents list
                cnt_resp = await client.get(f"/api/dashboard/trending/{issue_id}/contents", headers=headers)
                self.assertEqual(cnt_resp.status_code, 200)
                self.assertIsInstance(cnt_resp.json(), list)
        self.run_async(_test())

    def test_08_analytics_timeseries_and_export(self):
        """Verify timeseries chart APIs, summary breakdown, and CSV data export."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                login = await client.post(
                    "/api/dashboard/auth/login",
                    json={"username": "admin", "password": "patroladmin2026"},
                )
                token = login.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 1. Timeseries (dashboard analytics endpoint returns a list of data points)
                ts_resp = await client.get("/api/dashboard/analytics/timeseries?interval=day", headers=headers)
                self.assertEqual(ts_resp.status_code, 200)
                ts_data = ts_resp.json()
                self.assertIsInstance(ts_data, list)
                if ts_data:
                    self.assertIn("date", ts_data[0])
                    self.assertIn("total", ts_data[0])

                # 2. Timeseries v1 endpoint (returns object with series key)
                ts_v1 = await client.get("/api/v1/dashboard/timeseries?interval=day", headers=headers)
                self.assertEqual(ts_v1.status_code, 200)
                self.assertIn("series", ts_v1.json())

                # 3. Platform breakdown
                plt_resp = await client.get("/api/dashboard/analytics/platforms", headers=headers)
                self.assertEqual(plt_resp.status_code, 200)
                plt_data = plt_resp.json()
                self.assertIsInstance(plt_data, list)
                if plt_data:
                    self.assertIn("platform", plt_data[0])
                    self.assertIn("content_count", plt_data[0])

                # 4. Excel Pro (.xlsx) Export
                xlsx_resp = await client.get("/api/v1/dashboard/export?format=xlsx", headers=headers)
                self.assertEqual(xlsx_resp.status_code, 200)
                self.assertEqual(
                    xlsx_resp.headers["content-type"],
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                self.assertGreater(len(xlsx_resp.content), 2000)

                # 5. CSV Export (clean without `'-`)
                exp_resp = await client.get("/api/v1/dashboard/export?format=csv", headers=headers)
                self.assertEqual(exp_resp.status_code, 200)
                self.assertEqual(exp_resp.headers["content-type"], "text/csv; charset=utf-8")
                self.assertIn("Nomor Tiket", exp_resp.text)
                self.assertNotIn("'-", exp_resp.text)
        self.run_async(_test())

    def test_09_supported_channels_list(self):
        """Verify supported intake channels list endpoint for pure extension agent."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/assistant/channels")
                self.assertEqual(resp.status_code, 200)
                channels = resp.json()["channels"]
                channel_ids = [c["id"] for c in channels]
                self.assertIn("browser_extension", channel_ids)
                self.assertIn("web_dashboard", channel_ids)
                self.assertNotIn("whatsapp", channel_ids)
                self.assertNotIn("telegram", channel_ids)
        self.run_async(_test())

    def test_10_security_hardening_headers(self):
        """Verify OWASP recommended security headers are present on all responses."""
        async def _test():
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://testserver") as client:
                resp = await client.get("/health")
                self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
                self.assertEqual(resp.headers.get("X-XSS-Protection"), "1; mode=block")
                self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
