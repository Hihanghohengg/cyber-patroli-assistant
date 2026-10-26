"""Tests for IndonesianTextProcessor."""

import unittest
from app.services.intelligence.text_processor import IndonesianTextProcessor


class TestIndonesianTextProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = IndonesianTextProcessor()

    def test_clean_text_removes_urls_and_mentions(self):
        raw = "Banjir parah di daerah Jakarta Timur https://t.co/xyz123 @detikcom tolong segera ditangani!!"
        cleaned = self.processor.clean_text(raw)
        self.assertNotIn("https", cleaned)
        self.assertNotIn("@detikcom", cleaned)
        self.assertIn("jakarta timur", cleaned.lower())

    def test_tokenize_removes_indonesian_stopwords(self):
        text = "Ini adalah sebuah informasi penting yang harus diketahui oleh kita semua."
        tokens = self.processor.tokenize(text)
        self.assertNotIn("adalah", tokens)
        self.assertNotIn("sebuah", tokens)
        self.assertNotIn("yang", tokens)
        self.assertIn("informasi", tokens)
        self.assertIn("penting", tokens)

    def test_keyword_extraction(self):
        text = """
        Kebakaran hutan dan lahan karhutla melanda kawasan Riau dan Kalimantan Barat.
        Asap tebal akibat kebakaran hutan dan lahan karhutla mengganggu jarak pandang warga.
        Karhutla terjadi karena musim kemarau panjang.
        """
        keywords = self.processor.extract_keywords(text, top_k=5)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(any("karhutla" in k or "kebakaran" in k for k in keywords))

    def test_to_canonical_slug(self):
        title = "Kebakaran Hutan Riau & Kabut Asap 2026!"
        slug = self.processor.to_canonical_slug(title)
        self.assertEqual(slug, "kebakaran-hutan-riau-kabut-asap-2026")
        self.assertNotIn("!", slug)
        self.assertNotIn("&", slug)

    def test_jaccard_similarity(self):
        text_a = "Banjir bandang melanda wilayah Demak dan Kudus Jawa Tengah"
        text_b = "Banjir bandang rendam ribuan rumah di Demak Jawa Tengah"
        text_c = "Resep membuat nasi goreng spesial enak dan gurih"

        sim_ab = self.processor.compute_jaccard_similarity(text_a, text_b)
        sim_ac = self.processor.compute_jaccard_similarity(text_a, text_c)

        self.assertGreater(sim_ab, 0.2)
        self.assertEqual(sim_ac, 0.0)


if __name__ == "__main__":
    unittest.main()
