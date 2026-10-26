"""Tests for 5W+1H schema and extraction."""

import unittest
from app.schemas.intelligence import Analysis5W1H
from app.services.intelligence.analysis_5w1h import Analysis5W1HService


class Test5W1H(unittest.TestCase):
    def test_schema_validation(self):
        data = {
            "what": "Terjadi aksi unjuk rasa di depan gedung DPR",
            "who": "Massa mahasiswa",
            "when_info": "Siang hari ini",
            "where_info": "Gedung DPR Jakarta",
            "why": "Menuntut peninjauan kembali RUU",
            "how": "Membawa spanduk dan berorasi damai",
            "summary": "Mahasiswa menggelar aksi damai di depan DPR.",
            "main_topic": "Aksi Demo DPR",
            "sub_topics": ["mahasiswa", "ruu"],
            "keywords": ["demo", "dpr", "mahasiswa"],
            "hashtags": ["#DemoDPR"],
            "named_entities": ["DPR"],
            "sentiment": "NETRAL",
            "category": "Politik",
            "relevance_score": 0.8,
            "urgency_score": 0.6,
            "confidence_score": 0.9,
            "misinfo_indicators": [],
            "information_basis": "EKSPLISIT",
        }
        model = Analysis5W1H(**data)
        self.assertEqual(model.sentiment, "NETRAL")
        self.assertEqual(model.category, "Politik")
        self.assertEqual(model.what, "Terjadi aksi unjuk rasa di depan gedung DPR")

    def test_heuristic_fallback_extraction(self):
        service = Analysis5W1HService()
        result = service._heuristic_fallback(
            text="Bencana banjir bandang merendam ratusan rumah warga di wilayah Garut Jawa Barat akibat hujan deras.",
            author="infogarut",
            platform="tiktok",
        )
        self.assertEqual(result.category, "Bencana Alam")
        self.assertIsNotNone(result.what)
        self.assertTrue("Banjir" in result.main_topic or "Garut" in result.main_topic or len(result.keywords) > 0)
        self.assertEqual(result.information_basis, "CAMPURAN")


if __name__ == "__main__":
    unittest.main()
