"""Cryptographic Evidence Integrity Engine (NIST FIPS 198-1).

Provides deterministic ambiguity-free canonicalization, HMAC-SHA256 generation,
constant-time cryptographic verification, and in-memory tamper simulation
for digital evidence chain of custody.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class CryptoService:
    """Cryptographic Evidence Integrity Engine complying with NIST FIPS 198-1 & RFC 2104."""

    @staticmethod
    def _get_hmac_key(key: Optional[str] = None) -> bytes:
        """Resolve HMAC secret key from parameter or environment configuration."""
        raw_key = key or getattr(settings, "SECRET_HMAC_KEY", None) or settings.SECRET_KEY or "tilik_fips198_default_secret_key"
        return raw_key.encode("utf-8")

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Compute SHA-256 digest of a physical file in 64KB blocks.

        Args:
            file_path: Absolute or relative path to the evidence file.

        Returns:
            Lowercase 64-character hexadecimal SHA-256 digest.

        Raises:
            FileNotFoundError: If the file does not exist on disk.
        """
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Bukti digital tidak ditemukan di path: {file_path}")

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65_536):
                hasher.update(chunk)

        digest = hasher.hexdigest().lower()
        return digest

    @staticmethod
    def calculate_bytes_sha256(data: bytes) -> str:
        """Compute SHA-256 digest of raw byte content."""
        if not data:
            return hashlib.sha256(b"").hexdigest().lower()
        return hashlib.sha256(data).hexdigest().lower()

    @staticmethod
    def build_canonical_payload(
        screenshot_sha256: str,
        source_url: str,
        dom_text: str,
        ocr_text: Optional[str],
        captured_at_utc: str,
        operator_id: str,
    ) -> str:
        """Construct ambiguity-free deterministic canonical JSON representation of the evidence package.

        Uses strict lexicographical key sorting, standard compact separators (',', ':'),
        and unescaped UTF-8 characters to prevent delimiter collision attacks.

        Schema bound in canonical payload:
        {
            "captured_at_utc": str (ISO 8601 UTC),
            "dom_text": str,
            "ocr_text": str,
            "operator_id": str,
            "screenshot_sha256": str (64 hex lowercase),
            "source_url": str
        }
        """
        payload = {
            "captured_at_utc": (captured_at_utc or "").strip(),
            "dom_text": (dom_text or "").strip(),
            "ocr_text": (ocr_text or "").strip(),
            "operator_id": (operator_id or "OP-DEFAULT").strip(),
            "screenshot_sha256": (screenshot_sha256 or "").strip().lower(),
            "source_url": (source_url or "").strip(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def calculate_canonical_hash(canonical_payload: str) -> str:
        """Compute SHA-256 hash of the canonical JSON payload string."""
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest().lower()

    @classmethod
    def generate_hmac_tag(cls, canonical_payload: str, key: Optional[str] = None) -> str:
        """Generate HMAC-SHA256 message authentication tag for a canonical payload.

        Conforms strictly to NIST FIPS 198-1 / RFC 2104.
        """
        hmac_key = cls._get_hmac_key(key)
        tag = hmac.new(hmac_key, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest().lower()
        return tag

    @classmethod
    def seal_evidence_package(
        cls,
        screenshot_sha256: str,
        source_url: str,
        dom_text: str,
        ocr_text: Optional[str],
        captured_at_utc: str,
        operator_id: str,
        key: Optional[str] = None,
    ) -> Dict[str, str]:
        """Convenience method to construct canonical payload, hash, and HMAC tag in one call."""
        canonical_payload = cls.build_canonical_payload(
            screenshot_sha256=screenshot_sha256,
            source_url=source_url,
            dom_text=dom_text,
            ocr_text=ocr_text,
            captured_at_utc=captured_at_utc,
            operator_id=operator_id,
        )
        canonical_hash = cls.calculate_canonical_hash(canonical_payload)
        hmac_tag = cls.generate_hmac_tag(canonical_payload, key=key)

        return {
            "canonical_payload": canonical_payload,
            "canonical_hash": canonical_hash,
            "hmac_tag": hmac_tag,
        }

    @classmethod
    def verify_integrity(
        cls,
        file_path: Optional[str],
        source_url: str,
        dom_text: str,
        ocr_text: Optional[str],
        captured_at_utc: str,
        operator_id: str,
        expected_hmac_tag: str,
        expected_screenshot_sha256: Optional[str] = None,
        key: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Perform constant-time cryptographic integrity and authenticity verification.

        Args:
            file_path: Path to screenshot file on disk (or None if file_bytes provided).
            source_url: Captured post URL.
            dom_text: Text extracted from DOM.
            ocr_text: Text extracted via OCR.
            captured_at_utc: Capture timestamp in ISO 8601 UTC.
            operator_id: Operator identifier who executed the intake.
            expected_hmac_tag: Pre-recorded HMAC-SHA256 authentication tag.
            expected_screenshot_sha256: Optional recorded file SHA-256 for dual-check.
            key: Optional override HMAC key.
            file_bytes: Optional raw bytes if verifying in-memory.

        Returns:
            Dict containing status ("VERIFIED" or "TAMPERED"), constant-time match flag,
            latency in milliseconds, and component hashes.
        """
        start_time = time.perf_counter()

        # 1. Compute screenshot hash from bytes or disk file
        if file_bytes is not None:
            current_screenshot_sha256 = cls.calculate_bytes_sha256(file_bytes)
        elif file_path and os.path.exists(file_path):
            current_screenshot_sha256 = cls.calculate_sha256(file_path)
        else:
            current_screenshot_sha256 = ""

        file_match = True
        if expected_screenshot_sha256:
            file_match = hmac.compare_digest(
                current_screenshot_sha256.lower(),
                expected_screenshot_sha256.strip().lower(),
            )

        # 2. Reconstruct canonical JSON payload from current state
        current_canonical_payload = cls.build_canonical_payload(
            screenshot_sha256=current_screenshot_sha256,
            source_url=source_url,
            dom_text=dom_text,
            ocr_text=ocr_text,
            captured_at_utc=captured_at_utc,
            operator_id=operator_id,
        )
        current_canonical_hash = cls.calculate_canonical_hash(current_canonical_payload)

        # 3. Compute HMAC-SHA256 tag on reconstructed canonical payload
        computed_hmac_tag = cls.generate_hmac_tag(current_canonical_payload, key=key)

        # 4. Constant-time digest comparison (prevents timing attacks)
        is_tag_valid = hmac.compare_digest(
            computed_hmac_tag.lower(),
            (expected_hmac_tag or "").strip().lower(),
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
        is_authentic = is_tag_valid and file_match and bool(current_screenshot_sha256)

        status = "VERIFIED" if is_authentic else "TAMPERED"

        return {
            "status": status,
            "is_valid": is_authentic,
            "latency_ms": latency_ms,
            "computed_tag": computed_hmac_tag,
            "expected_tag": (expected_hmac_tag or "").strip().lower(),
            "canonical_hash": current_canonical_hash,
            "current_screenshot_sha256": current_screenshot_sha256,
            "expected_screenshot_sha256": (expected_screenshot_sha256 or "").strip().lower(),
            "file_integrity_match": file_match,
            "canonical_payload": current_canonical_payload,
        }

    @classmethod
    def simulate_tamper(
        cls,
        original_data: Dict[str, Any],
        tamper_type: str,
        dry_run: bool = True,
        file_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Simulate single-bit or content tampering to evaluate cryptographic sensitivity.

        Supported tamper_type values:
        - "IMAGE_BIT_FLIP": Flips exactly 1 bit in the screenshot binary data.
        - "TEXT_MUTATION": Mutates 1 character in dom_text.
        - "METADATA_SPOOF": Modifies operator_id or capture timestamp.

        When dry_run=True, all operations execute in-memory with zero disk/DB side effects.
        """
        start_time = time.perf_counter()

        source_url = original_data.get("source_url", "")
        dom_text = original_data.get("dom_text", "")
        ocr_text = original_data.get("ocr_text", "")
        captured_at_utc = original_data.get("captured_at_utc", "")
        operator_id = original_data.get("operator_id", "OP-01")
        original_hmac_tag = original_data.get("hmac_tag", "")

        # Default dummy bytes if none provided
        bytes_to_tamper = bytearray(file_bytes or b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtilik_test_payload_bytes")
        original_img_hash = cls.calculate_bytes_sha256(bytes_to_tamper)

        tampered_img_hash = original_img_hash
        tampered_dom = dom_text
        tampered_ocr = ocr_text
        tampered_op = operator_id
        tampered_utc = captured_at_utc
        mutation_description = ""

        if tamper_type.upper() == "IMAGE_BIT_FLIP":
            # Invert the least significant bit (LSB) of byte at index 8
            target_idx = min(8, len(bytes_to_tamper) - 1)
            original_byte = bytes_to_tamper[target_idx]
            bytes_to_tamper[target_idx] ^= 0x01
            tampered_byte = bytes_to_tamper[target_idx]
            tampered_img_hash = cls.calculate_bytes_sha256(bytes_to_tamper)
            mutation_description = f"Bit flip pada byte index {target_idx}: 0x{original_byte:02X} -> 0x{tampered_byte:02X}"

        elif tamper_type.upper() == "TEXT_MUTATION":
            if tampered_dom:
                tampered_dom = tampered_dom[:-1] + ("X" if tampered_dom[-1] != "X" else "Y")
            else:
                tampered_dom = "Konten termutasi 1 bit."
            mutation_description = "Mutasi 1 karakter pada teks DOM laporan."

        elif tamper_type.upper() == "METADATA_SPOOF":
            tampered_op = f"{operator_id}_TAMPERED"
            mutation_description = f"Pemalsuan operator_id dari '{operator_id}' menjadi '{tampered_op}'."

        else:
            raise ValueError(f"Tipe simulasi tamper tidak dikenal: '{tamper_type}'. Gunakan IMAGE_BIT_FLIP, TEXT_MUTATION, atau METADATA_SPOOF.")

        # Reconstruct canonical payload with tampered element
        tampered_canonical = cls.build_canonical_payload(
            screenshot_sha256=tampered_img_hash,
            source_url=source_url,
            dom_text=tampered_dom,
            ocr_text=tampered_ocr,
            captured_at_utc=tampered_utc,
            operator_id=tampered_op,
        )
        tampered_canonical_hash = cls.calculate_canonical_hash(tampered_canonical)
        computed_tampered_tag = cls.generate_hmac_tag(tampered_canonical)

        # Constant-time comparison against original valid tag
        is_tag_valid = hmac.compare_digest(
            computed_tampered_tag.lower(),
            original_hmac_tag.strip().lower(),
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return {
            "simulation": "COMPLETED",
            "tamper_type": tamper_type.upper(),
            "dry_run": dry_run,
            "mutation_details": mutation_description,
            "detection_status": "TAMPERED" if not is_tag_valid else "VERIFIED",
            "is_tampered_detected": not is_tag_valid,
            "latency_ms": latency_ms,
            "original_hmac_tag": original_hmac_tag,
            "tampered_computed_tag": computed_tampered_tag,
            "original_screenshot_sha256": original_img_hash,
            "tampered_screenshot_sha256": tampered_img_hash,
            "tampered_canonical_hash": tampered_canonical_hash,
            "tampered_canonical_payload": tampered_canonical,
        }
