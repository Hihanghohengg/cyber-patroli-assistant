"""Test script to verify audit logging and security by design across backend APIs."""

import os
import sys
from datetime import datetime

# Add cyber-patrol-assistant to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.audit import AuditLog
from app.models.intelligence import DashboardUser
from app.api.dashboard.auth import login, _record_failed_attempt, _clear_failed_attempts
from app.schemas.dashboard import LoginRequest
from app.api.v1.integrity import simulate_tamper_test, TamperTestRequest
from app.api.v1.report_export import _log_audit_safe
from app.api.v1.admin import list_audit_logs


def test_audit_trail_flow():
    db = SessionLocal()
    try:
        print("[TEST] 1. Testing Failed Login Audit Logging...")
        # Clean old audit logs for clean test
        initial_count = db.query(AuditLog).count()

        class MockRequest:
            class MockClient:
                host = "192.168.1.100"
            client = MockClient()

        req = MockRequest()

        # Trigger failed login
        try:
            login(payload=LoginRequest(username="nonexistent_user", password="badpassword"), request=req, db=db)
        except Exception:
            pass

        failed_log = db.query(AuditLog).filter(AuditLog.action == "AUTH_LOGIN_FAILED").order_by(AuditLog.timestamp.desc()).first()
        assert failed_log is not None, "AUTH_LOGIN_FAILED audit log not found!"
        assert failed_log.ip_address == "192.168.1.100"
        assert failed_log.actor_username == "nonexistent_user"
        print("  [✓] Failed login recorded with IP:", failed_log.ip_address)

        print("[TEST] 2. Testing Successful Login Audit Logging...")
        # Default admin login
        admin_login_res = login(payload=LoginRequest(username="admin", password="patroladmin2026"), request=req, db=db)
        assert admin_login_res.access_token is not None

        success_log = db.query(AuditLog).filter(AuditLog.action == "AUTH_LOGIN_SUCCESS").order_by(AuditLog.timestamp.desc()).first()
        assert success_log is not None, "AUTH_LOGIN_SUCCESS audit log not found!"
        assert success_log.actor_username == "admin"
        assert success_log.ip_address == "192.168.1.100"
        print("  [✓] Successful login recorded for:", success_log.actor_username)

        print("[TEST] 3. Testing Integrity Tamper Test Audit Logging...")
        tamper_req = TamperTestRequest(tamper_type="IMAGE_BIT_FLIP", dry_run=True)
        res = simulate_tamper_test(request=tamper_req, raw_request=req, db=db)
        assert res["status"] == "SUCCESS"

        tamper_log = db.query(AuditLog).filter(AuditLog.action == "INTEGRITY_TAMPER_TEST_EXECUTED").order_by(AuditLog.timestamp.desc()).first()
        assert tamper_log is not None, "INTEGRITY_TAMPER_TEST_EXECUTED audit log not found!"
        assert tamper_log.details["tamper_type"] == "IMAGE_BIT_FLIP"
        print("  [✓] Tamper test audit recorded, type:", tamper_log.details["tamper_type"])

        print("[TEST] 4. Testing Report Dossier Export Audit Logging...")
        _log_audit_safe(
            db=db,
            action="REPORT_DOSSIER_EXPORTED",
            actor_username="admin",
            entity_type="ReportDossier",
            entity_id="daily-2026-11-19",
            details={"type": "daily_patrol_report", "format": "pdf"},
            ip_address="192.168.1.100",
        )
        dossier_log = db.query(AuditLog).filter(AuditLog.action == "REPORT_DOSSIER_EXPORTED").order_by(AuditLog.timestamp.desc()).first()
        assert dossier_log is not None, "REPORT_DOSSIER_EXPORTED audit log not found!"
        print("  [✓] Report dossier export recorded successfully")

        print("[TEST] 5. Testing Admin Audit Logs API Mapping...")
        admin_user = db.query(DashboardUser).filter(DashboardUser.username == "admin").first()
        audit_res = list_audit_logs(page=1, limit=10, action=None, db=db, admin=admin_user)
        assert "items" in audit_res
        assert len(audit_res["items"]) > 0
        first_item = audit_res["items"][0]
        assert "actor_username" in first_item, "actor_username must be mapped in audit log API items!"
        assert "ip_address" in first_item, "ip_address must be mapped in audit log API items!"
        print("  [✓] Audit Log API correctly surfaces actor_username and ip_address:", first_item["actor_username"], first_item["ip_address"])

        print("\n[SUCCESS] ALL AUDIT & SECURITY TESTS PASSED!")

    finally:
        # Clean up test audit logs to keep clean DB state
        db.query(AuditLog).filter(AuditLog.ip_address == "192.168.1.100").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_audit_trail_flow()
