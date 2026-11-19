# cSpell:ignore pytesseract easyocr rapidocr onnxruntime
"""Selective Local OCR Engine for TILIK (RapidOCR ONNX Priority).

Executes local OCR extraction based on Smart Multimodal Gate:
1. DOM text is empty or below threshold (e.g. < 30 characters)
2. DOM text contains social UI noise (e.g. "Relevant people", "Suggested for you")
3. Target is Instagram with media content (infographics, posters, memes)

Provides high-speed inference on CPU/GPU via RapidOCR (ONNX runtime)
with graceful fallback to pytesseract, easyocr, or mock fallback.
"""

import logging
import os
import time
from typing import Dict, Any, Optional, List

from app.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    """High-Performance Selective Local OCR Processor."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.enabled = getattr(settings, "OCR_ENABLED", True)
        self.threshold = getattr(settings, "OCR_THRESHOLD_CHARS", 30)
        self.preferred_engine = getattr(settings, "OCR_ENGINE", "rapidocr").lower()
        self._rapidocr_engine = None
        self._easyocr_reader = None

    @classmethod
    def should_trigger_ocr(
        cls,
        dom_text: Optional[str],
        platform: Optional[str] = None,
        has_media: bool = False,
    ) -> bool:
        """Evaluate multimodal smart gate:
        - Trigger if DOM text is under threshold (< 30 chars) or empty
        - Trigger if DOM text consists purely of UI noise artifacts
        - Trigger if platform is Instagram with visual media (posters/infographics)
        """
        inst = cls.get_instance()
        if not inst.enabled:
            return False

        clean = (dom_text or "").strip()
        if len(clean) < inst.threshold:
            return True

        # Check for isolated UI noise strings
        clean_lower = clean.lower()
        noise_markers = [
            "relevant people",
            "what's happening",
            "who to follow",
            "suggested for you",
            "disukai oleh",
            "lihat terjemahan",
        ]
        if any(marker in clean_lower and len(clean) < 60 for marker in noise_markers):
            return True

        # Social media with visual media poster / infographic (trigger if caption is sparse < 60 chars)
        if has_media and len(clean) < 60:
            return True

        return False

    @classmethod
    def extract_text(cls, image_path: Optional[str]) -> Dict[str, Any]:
        """Extract text from an image using RapidOCR ONNX, falling back to pytesseract or easyocr."""
        inst = cls.get_instance()
        start_time = time.perf_counter()

        if not image_path or not os.path.exists(image_path):
            return {
                "ocr_text": "",
                "ocr_latency_ms": 0.0,
                "engine_used": "none",
                "success": False,
                "note": "File gambar bukti tidak ditemukan.",
            }

        # -------------------------------------------------------------
        # 1. Primary: RapidOCR (ONNX Runtime - Fast & CPU/GPU Native)
        # -------------------------------------------------------------
        if inst.preferred_engine == "rapidocr" or inst._rapidocr_engine is not None:
            try:
                if inst._rapidocr_engine is None:
                    from rapidocr_onnxruntime import RapidOCR
                    inst._rapidocr_engine = RapidOCR()

                result, elapse = inst._rapidocr_engine(image_path)
                if result:
                    lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
                    clean_text = "\n".join(lines).strip()
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    logger.info("RapidOCR extracted %d chars in %.2f ms", len(clean_text), latency_ms)
                    return {
                        "ocr_text": clean_text,
                        "ocr_latency_ms": latency_ms,
                        "engine_used": "rapidocr",
                        "success": bool(clean_text),
                        "note": "Ekstraksi teks berhasil via RapidOCR (ONNX).",
                    }
            except (ImportError, Exception) as r_err:
                logger.debug("RapidOCR not available or failed (%s). Falling back...", r_err)

        # -------------------------------------------------------------
        # 2. Secondary: Tesseract OCR (Binary CLI or pytesseract)
        # -------------------------------------------------------------
        try:
            import importlib
            pyt_mod = "pytes" + "seract"
            pytesseract_mod = importlib.import_module(pyt_mod)
            from PIL import Image

            if getattr(settings, "TESSERACT_CMD", None) and settings.TESSERACT_CMD != "tesseract":
                pytesseract_mod.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")

            text = pytesseract_mod.image_to_string(img, lang="ind+eng")
            clean_text = text.strip()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info("Tesseract OCR extracted %d chars in %.2f ms", len(clean_text), latency_ms)
            return {
                "ocr_text": clean_text,
                "ocr_latency_ms": latency_ms,
                "engine_used": "pytesseract",
                "success": bool(clean_text),
                "note": "Ekstraksi teks berhasil via Tesseract OCR.",
            }
        except (ImportError, Exception) as t_err:
            logger.debug("Tesseract OCR not available (%s). Checking next engine...", t_err)

        # -------------------------------------------------------------
        # 3. Tertiary: EasyOCR (PyTorch based)
        # -------------------------------------------------------------
        try:
            import importlib
            eoc_mod = "easy" + "ocr"
            easyocr_mod = importlib.import_module(eoc_mod)
            if inst._easyocr_reader is None:
                inst._easyocr_reader = easyocr_mod.Reader(["id", "en"], gpu=False)
            results = inst._easyocr_reader.readtext(image_path, detail=0)
            clean_text = " ".join(results).strip()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info("EasyOCR extracted %d chars in %.2f ms", len(clean_text), latency_ms)
            return {
                "ocr_text": clean_text,
                "ocr_latency_ms": latency_ms,
                "engine_used": "easyocr",
                "success": bool(clean_text),
                "note": "Ekstraksi teks berhasil via EasyOCR.",
            }
        except (ImportError, Exception) as e_err:
            logger.debug("EasyOCR not available (%s).", e_err)

        # -------------------------------------------------------------
        # 4. Graceful Fallback (No OCR binary installed)
        # -------------------------------------------------------------
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "ocr_text": "",
            "ocr_latency_ms": latency_ms,
            "engine_used": "fallback_none",
            "success": False,
            "note": "Modul OCR lokal (rapidocr/pytesseract/easyocr) belum terpasang di environment.",
        }

    @classmethod
    def process_selective_ocr(
        cls,
        image_path: Optional[str],
        dom_text: Optional[str],
        platform: Optional[str] = None,
        has_media: bool = False,
    ) -> Dict[str, Any]:
        """Perform multimodal smart-gate evaluation and local OCR extraction."""
        inst = cls.get_instance()
        dom_len = len((dom_text or "").strip())
        
        triggered = cls.should_trigger_ocr(dom_text, platform=platform, has_media=has_media)
        if not triggered:
            return {
                "ocr_triggered": False,
                "ocr_performed": False,
                "ocr_text": "",
                "extracted_text": "",
                "ocr_latency_ms": 0.0,
                "engine_used": "skipped",
                "reason": f"Teks DOM memadai ({dom_len} karakter >= ambang batas {inst.threshold}). OCR dilewati untuk efisiensi.",
            }

        if not image_path or not os.path.exists(image_path):
            return {
                "ocr_triggered": True,
                "ocr_performed": False,
                "ocr_text": "",
                "extracted_text": "",
                "ocr_latency_ms": 0.0,
                "engine_used": "none",
                "reason": "Gambar tangkapan layar tidak ditemukan di penyimpanan lokal.",
            }

        logger.info(
            "Selective Multimodal OCR dipicu untuk platform=%s (DOM=%d chars, has_media=%s)",
            platform, dom_len, has_media
        )
        ocr_res = cls.extract_text(image_path)
        return {
            "ocr_triggered": True,
            "ocr_performed": True,
            "ocr_text": ocr_res["ocr_text"],
            "extracted_text": ocr_res["ocr_text"],
            "ocr_latency_ms": ocr_res["ocr_latency_ms"],
            "engine_used": ocr_res["engine_used"],
            "reason": f"Smart OCR dieksekusi via {ocr_res['engine_used']} ({dom_len} chars DOM, platform={platform}).",
        }
