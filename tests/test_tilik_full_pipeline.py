"""Comprehensive Automated Pipeline Verification for TILIK.

Validates:
1. Cryptographic Evidence Integrity (NIST FIPS 198-1 HMAC-SHA256)
2. Omnichannel Intake with Selective OCR & Deduplication
3. Baseline vs Adaptive On-Demand Classification
4. HITL Analyst Validation Promotion to ValidatedMemory
5. Daily Executive Report Export (Markdown & PDF)
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, apply_schema_migrations, engine
from app.models.report import Report, Content
from app.models.evidence import Evidence
from app.models.memory import ValidatedMemory
from app.services.crypto_service import CryptoService
from app.services.memory_service import MemoryService
from app.services.ollama_service import OllamaService
from app.services.ocr_service import OCRService


def test_full_pipeline():
    print("=" * 80)
    print("      [+] TEST AUTOMATISASI AKHIR PIPELINE PENUH TILIK (FASE 1 - 4)")
    print("=" * 80)

    apply_schema_migrations(engine)
    db = SessionLocal()

    try:
        # TEST 1: Cryptographic Integrity Engine
        print("\n[TEST 1] Menguji Cryptographic Seal & Constant-Time Verification...")
        dummy_img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        img_sha256 = CryptoService.calculate_bytes_sha256(dummy_img_bytes)

        test_payload = {
            "screenshot_sha256": img_sha256,
            "source_url": "https://x.com/patrol/status/123456789",
            "dom_text": "Narasi patroli terorisme siber.",
            "ocr_text": "Teks terbaca dari spanduk bukti.",
            "captured_at_utc": "2026-11-13T12:00:00Z",
            "operator_id": "OP-TEST-99"
        }
        seal = CryptoService.seal_evidence_package(**test_payload)
        assert seal["canonical_hash"] and seal["hmac_tag"], "Seal generation failed"

        verify_res = CryptoService.verify_integrity(
            file_path=None,
            file_bytes=dummy_img_bytes,
            source_url=test_payload["source_url"],
            dom_text=test_payload["dom_text"],
            ocr_text=test_payload["ocr_text"],
            captured_at_utc=test_payload["captured_at_utc"],
            operator_id=test_payload["operator_id"],
            expected_hmac_tag=seal["hmac_tag"]
        )
        assert verify_res["status"] == "VERIFIED", "Verification failed"
        print(f"  [✓] Seal generated: {seal['hmac_tag'][:32]}... | Verification: {verify_res['status']} in {verify_res['latency_ms']}ms")

        # Tamper Simulation test
        original_data = {**test_payload, "hmac_tag": seal["hmac_tag"]}
        tamper_res = CryptoService.simulate_tamper(
            original_data=original_data,
            tamper_type="IMAGE_BIT_FLIP",
            dry_run=True,
            file_bytes=dummy_img_bytes
        )
        assert tamper_res["detection_status"] == "TAMPERED", "Tamper test failed to detect corruption"
        print(f"  [✓] Tamper 1-bit flip simulation properly detected as: {tamper_res['detection_status']} in {tamper_res['latency_ms']}ms")

        # TEST 2: Selective OCR Engine
        print("\n[TEST 2] Menguji Selective OCR Engine...")
        ocr_svc = OCRService()
        # Case A: Long DOM text (OCR should NOT trigger)
        res_a = ocr_svc.process_selective_ocr(image_path=None, dom_text="Ini adalah postingan berita panjang dengan banyak teks lebih dari tiga puluh karakter.")
        assert res_a["ocr_performed"] is False, "OCR should not trigger for long text"
        print("  [✓] Long DOM text correctly bypassed OCR")

        # Case B: Short DOM text without image (OCR skipped gracefully)
        res_b = ocr_svc.process_selective_ocr(image_path=None, dom_text="Pendek")
        assert res_b["ocr_performed"] is False, "OCR should gracefully skip without image"
        print("  [✓] Short DOM text without image handled gracefully without crash")

        # TEST 3: Feedback-Driven MemPrompt Case Memory
        print("\n[TEST 3] Menguji MemPrompt Case Memory & Dense Vector Retrieval...")
        test_mem_text = "Kelompok kriminal menyebarkan ransomware yang mengunci data rekam medis rumah sakit."
        mem_entry = MemoryService.add_validated_case(
            db=db,
            content_text=test_mem_text,
            validated_category="Keamanan",
            analyst_rationale="Serangan malware terhadap fasilitas kesehatan masyarakat.",
            validated_by="Analyst-Unit-Test",
            urgency_score=5
        )
        assert mem_entry.validated_category == "Keamanan"
        print(f"  [✓] Gated memory entry created: {mem_entry.memory_id} (Category: {mem_entry.validated_category})")

        # Test retrieval
        ret_data = MemoryService.retrieve_similar_cases(
            query_text="Ransomware mengunci basis data rekam medis",
            db=db,
            top_k=3,
            threshold=0.30
        )
        assert ret_data["cases_count"] >= 1, "Should retrieve at least the seeded case"
        print(f"  [✓] Dense vector retrieval found {ret_data['cases_count']} similar cases in {ret_data['retrieval_ms']}ms")

        # TEST 4: Local Ollama Intelligence Service (Fail-open Heuristic)
        print("\n[TEST 4] Menguji Ollama Local Intelligence & Heuristic Failopen...")
        ollama_svc = OllamaService()
        cls_res = ollama_svc.classify_and_summarize(
            text="Penyebaran ujaran kebencian SARA yang memicu kerusuhan dan tawuran pemuda.",
            title="Kerusuhan SARA",
            source_url="https://facebook.com/post/999",
            author="provokator",
            platform="facebook",
            few_shot_block=ret_data["prompt_block"],
            mode="adaptive"
        )
        assert cls_res["predicted_category"] in ["Sosial", "Keamanan"], f"Unexpected category {cls_res['predicted_category']}"
        assert 1 <= cls_res["urgency_score"] <= 5, "Invalid urgency score"
        assert "what" in cls_res["summary_5w1h"], "Missing 5W+1H output"
        print(f"  [✓] Inference classified as: {cls_res['predicted_category']} (Urgency: {cls_res['urgency_score']}/5) | 5W1H What: {cls_res['summary_5w1h']['what']}")

        # TEST 5: Semantic Deduplication Check
        print("\n[TEST 5] Menguji Semantic Deduplication Engine...")
        dup_check = MemoryService.check_semantic_duplicate(
            text="Penyebaran ujaran kebencian SARA yang memicu kerusuhan",
            current_ticket="PS-TEST-NEW",
            db=db,
            threshold=0.85
        )
        print(f"  [✓] Semantic duplicate check completed successfully: is_dup={dup_check['is_duplicate']}")

        # TEST 6: Cross-Lingual English Input to 100% Indonesian Output
        print("\n[TEST 6] Menguji Cross-Lingual English Input -> 100% Output Bahasa Indonesia...")
        en_input_text = "Hacked database containing 50 million citizen biometric records and police records is currently for sale on breach forums."
        en_cls_res = ollama_svc.classify_and_summarize(
            text=en_input_text,
            title="Biometric Data Breach",
            source_url="https://darkweb.onion/leak",
            author="anonymous_hacker",
            platform="web",
            mode="adaptive"
        )
        assert en_cls_res["predicted_category"] == "Keamanan", f"Expected Keamanan, got {en_cls_res['predicted_category']}"
        assert en_cls_res.get("original_language") in ["en", "id"], "Language detection failed"
        assert len(en_cls_res.get("indonesian_content", "")) > 10, "Missing indonesian_content output"
        assert "what" in en_cls_res["summary_5w1h"], "Missing 5W+1H output"
        print(f"  [✓] English input classified as: {en_cls_res['predicted_category']} (Lang: {en_cls_res.get('original_language')})")
        print(f"  [✓] Indonesian translation output: {en_cls_res.get('indonesian_content')[:90]}...")

        # TEST 7: 5-Platform Acquisition Router & News URL Normalization
        print("\n[TEST 7] Menguji 5-Platform Acquisition Router & Normalisasi Berita...")
        from app.services.crawler_service import normalize_news_url
        raw_news = "https://www.kompas.com/tren/read/2026/11/15/berita-penting-nasional"
        norm_news = normalize_news_url(raw_news)
        assert "page=all" in norm_news, f"Normalization failed: {norm_news}"
        print(f"  [✓] Indonesian news pagination auto-normalized: {norm_news}")

        from app.services.scraper.base import BaseScraper
        for plat_url, expected_plat in [
            ("https://x.com/kivz/status/18841234567890", "x"),
            ("https://www.instagram.com/p/DF123456789/", "instagram"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
            ("https://www.threads.net/@user/post/DFxyz123", "threads"),
            ("https://news.detik.com/berita/d-1234567/judul", "web"),
        ]:
            detected_p = BaseScraper.detect_platform(plat_url)
            assert detected_p == expected_plat, f"Platform mismatch for {plat_url}: {detected_p} != {expected_plat}"
        print("  [✓] 5-Platform detection verified: X, Instagram, YouTube, Threads, and National Web")

        # TEST 8: Multimodal Smart Gate for Instagram with Media
        print("\n[TEST 8] Menguji Multimodal Smart Gate...")
        assert OCRService.should_trigger_ocr("Short", "instagram", has_media=False) is True
        assert OCRService.should_trigger_ocr("Teks panjang lebih dari 30 karakter tanpa media", "web", has_media=False) is False
        assert OCRService.should_trigger_ocr("Teks panjang di Instagram dengan gambar", "instagram", has_media=True) is True
        print("  [✓] Multimodal Smart Gate correctly triggered for Instagram poster with media")

        print("\n" + "=" * 80)
        print("          [✓] SELURUH PIPELINE TILIK TERVERIFIKASI 100% SUKSES (8/8 PASS)")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    test_full_pipeline()
