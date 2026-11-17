"""Automated test suite for 3-Layer Hierarchical Deduplication in TILIK.

Tests:
- Kasus A: New content by Akun X -> saved as ID A.
- Kasus B: Re-intake same content by Akun X (with tracking query and foryou feed with relative timestamp) -> deduplicated, returns ID A.
- Kasus C: Re-intake same content with > 1.5x more complete text by Akun X -> Smart Update on ID A.
- Kasus D: Re-intake same text by different author Akun Y -> saved as new record ID B.
"""

import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.report import Content, Report, Account
from app.models.evidence import Evidence
from app.models.intelligence import ContentAnalysis, IssueContent

client = TestClient(app)

def test_four_deduplication_cases():
    db = SessionLocal()
    clean_target_ids = []

    try:
        # =========================================================================
        # KASUS A: Konten 1 oleh Akun X -> Tersimpan sebagai ID: A
        # =========================================================================
        post_id_x = f"98765432{uuid.uuid4().hex[:6]}"
        url_x = f"https://www.tiktok.com/@akun_x/video/{post_id_x}"
        text_base = "Penyelidikan mendalam kasus insiden kebocoran data rahasia instansi pemerintah."

        payload_a = {
            "url": url_x,
            "source_channel": "BROWSER_EXTENSION",
            "username": "akun_x",
            "caption": text_base,
            "classification_mode": "baseline",
        }

        res_a = client.post("/api/v1/assistant/intake", json=payload_a)
        assert res_a.status_code == 200, f"Kasus A gagal: {res_a.text}"
        data_a = res_a.json()

        id_a = data_a["content_id"]
        clean_target_ids.append(id_a)
        assert data_a.get("deduplicated") is False, "Kasus A harusnya entri baru (deduplicated=False)"
        assert id_a is not None

        count_after_a = db.query(Content).count()
        print(f"\n[✓] KASUS A PASS: Konten baru Akun X berhasil tersimpan (ID: {id_a})")

        # =========================================================================
        # KASUS B: Kirim ulang Konten 1 oleh Akun X (URL tracking & feed foryou)
        # =========================================================================
        # Sub-kasus B1: URL permalink berparameter tracking
        url_x_tracked = f"{url_x}/?is_from_webapp=1&sender_device=pc&share_id=track123&utm_source=copy"
        payload_b1 = {
            "url": url_x_tracked,
            "source_channel": "BROWSER_EXTENSION",
            "username": "akun_x",
            "caption": text_base,
            "classification_mode": "baseline",
        }
        res_b1 = client.post("/api/v1/assistant/intake", json=payload_b1)
        assert res_b1.status_code == 200, f"Kasus B1 gagal: {res_b1.text}"
        data_b1 = res_b1.json()

        assert data_b1["content_id"] == id_a, "Kasus B1: content_id harus tetap ID A"
        assert data_b1.get("deduplicated") is True, "Kasus B1: harus terdeteksi deduplicated=True"
        assert data_b1.get("updated") is False, "Kasus B1: updated harus False"

        # Sub-kasus B2: URL feed /foryou dengan stempel waktu relatif dinamis
        payload_b2 = {
            "url": "https://www.tiktok.com/foryou",
            "source_channel": "BROWSER_EXTENSION",
            "username": "akun_x",
            "caption": f"{text_base} 5 jam yang lalu",
            "classification_mode": "baseline",
        }
        res_b2 = client.post("/api/v1/assistant/intake", json=payload_b2)
        assert res_b2.status_code == 200, f"Kasus B2 gagal: {res_b2.text}"
        data_b2 = res_b2.json()

        assert data_b2["content_id"] == id_a, "Kasus B2: fallback feed harus cocok ke ID A"
        assert data_b2.get("deduplicated") is True, "Kasus B2: harus terdeteksi deduplicated=True"

        count_after_b = db.query(Content).count()
        assert count_after_b == count_after_a, "Kasus B: Jumlah baris database TIDAK BOLEH bertambah"
        print(f"[✓] KASUS B PASS: Duplikat ditolak, tetap ID: {id_a} (deduplicated=True)")

        # =========================================================================
        # KASUS C: Teks lebih lengkap (> 1.5x) oleh Akun X -> Smart Update pada ID: A
        # =========================================================================
        text_long = (
            f"{text_base} Tim investigasi gabungan telah mengamankan barang bukti log server forensik "
            f"serta memverifikasi tanda tangan digital pelaku penyerangan siber secara menyeluruh."
        )
        assert len(text_long) > len(text_base) * 1.5, "Syarat uji > 1.5x panjang teks"

        payload_c = {
            "url": url_x,
            "source_channel": "BROWSER_EXTENSION",
            "username": "akun_x",
            "caption": text_long,
            "classification_mode": "baseline",
        }
        res_c = client.post("/api/v1/assistant/intake", json=payload_c)
        assert res_c.status_code == 200, f"Kasus C gagal: {res_c.text}"
        data_c = res_c.json()

        assert data_c["content_id"] == id_a, "Kasus C: Smart update harus memperbarui ID A"
        assert data_c.get("deduplicated") is True, "Kasus C: deduplicated=True"
        assert data_c.get("updated") is True, "Kasus C: updated=True (Smart Update)"

        count_after_c = db.query(Content).count()
        assert count_after_c == count_after_a, "Kasus C: Baris baru TIDAK BOLEH bertambah saat Smart Update"
        print(f"[✓] KASUS C PASS: Smart Update berhasil memperbarui ID: {id_a} tanpa menambah baris")

        # =========================================================================
        # KASUS D: Konten teks sama oleh Akun Y -> Tersimpan sebagai rekaman baru ID: B
        # =========================================================================
        post_id_y = f"11223344{uuid.uuid4().hex[:6]}"
        url_y = f"https://www.tiktok.com/@akun_y/video/{post_id_y}"

        payload_d = {
            "url": url_y,
            "source_channel": "BROWSER_EXTENSION",
            "username": "akun_y",
            "caption": text_base,
            "classification_mode": "baseline",
        }
        res_d = client.post("/api/v1/assistant/intake", json=payload_d)
        assert res_d.status_code == 200, f"Kasus D gagal: {res_d.text}"
        data_d = res_d.json()

        id_b = data_d["content_id"]
        clean_target_ids.append(id_b)
        assert id_b != id_a, "Kasus D: Akun berbeda harus menghasilkan ID baru (ID B != ID A)"
        assert data_d.get("deduplicated") is False, "Kasus D: deduplicated=False"

        count_after_d = db.query(Content).count()
        assert count_after_d == count_after_a + 1, "Kasus D: Baris database HARUS bertambah 1 untuk akun berbeda"
        print(f"[✓] KASUS D PASS: Konten sama oleh akun berbeda (Akun Y) disimpan sebagai entri baru (ID: {id_b})")

        print("\n" + "=" * 70)
        print("   [✓] SELURUH 4 KASUS HIERARCHICAL DEDUPLICATION LULUS 100% (4/4 PASS)")
        print("=" * 70 + "\n")

    finally:
        # Bersihkan data uji agar database tetap higienis
        for cid_str in clean_target_ids:
            try:
                cid = uuid.UUID(cid_str)
                db.query(IssueContent).filter_by(content_id=cid).delete()
                db.query(ContentAnalysis).filter_by(content_id=cid).delete()
                for r in db.query(Report).filter_by(content_id=cid).all():
                    db.query(Evidence).filter_by(report_id=r.report_id).delete()
                    db.delete(r)
                db.query(Content).filter_by(content_id=cid).delete()
            except Exception:
                pass
        db.commit()
        db.close()

if __name__ == "__main__":
    test_four_deduplication_cases()
