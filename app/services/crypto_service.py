import hashlib
import os
import logging

logger = logging.getLogger(__name__)


class CryptoService:
    """Kriptografi untuk pembuktian integritas bukti digital.

    Setiap tangkapan layar yang diambil oleh scraper akan di-hash menggunakan
    SHA-256 sehingga dapat diverifikasi keasliannya di kemudian hari.
    """

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Compute SHA-256 digest of a file.

        Args:
            file_path: Absolute or relative path to the evidence file.

        Returns:
            Lowercase hex string of the SHA-256 hash.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Bukti digital tidak ditemukan di: {file_path}")

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65_536):
                hasher.update(chunk)

        digest = hasher.hexdigest()
        logger.info("SHA-256 computed for %s: %s", file_path, digest[:16])
        return digest

    @staticmethod
    def verify_integrity(file_path: str, expected_hash: str) -> bool:
        """Verify that a file still matches its recorded hash.

        Args:
            file_path: Path to the evidence file.
            expected_hash: The SHA-256 hash recorded at capture time.

        Returns:
            True if the file's current hash matches the expected hash.
        """
        current_hash = CryptoService.calculate_sha256(file_path)
        is_valid = current_hash.lower() == expected_hash.lower()
        if not is_valid:
            logger.warning(
                "Integrity check FAILED for %s — expected %s, got %s",
                file_path,
                expected_hash[:16],
                current_hash[:16],
            )
        return is_valid

    @staticmethod
    def sign_evidence(sha256_hash: str, ticket_number: str, url: str) -> str:
        """Generate HMAC-SHA256 digital signature to guarantee authenticity without encrypting image data."""
        import hmac
        from app.config import settings

        key = (settings.SECRET_KEY or "cyber-patrol-forensic-secret").encode("utf-8")
        msg = f"{sha256_hash}:{ticket_number}:{url}".encode("utf-8")
        signature = hmac.new(key, msg, hashlib.sha256).hexdigest()
        logger.info("Digital signature generated for ticket %s: %s", ticket_number, signature[:16])
        return signature

    @staticmethod
    def verify_signature(sha256_hash: str, ticket_number: str, url: str, signature: str) -> bool:
        """Verify HMAC-SHA256 digital signature."""
        import hmac

        expected = CryptoService.sign_evidence(sha256_hash, ticket_number, url)
        return hmac.compare_digest(expected.lower(), signature.strip().lower())
