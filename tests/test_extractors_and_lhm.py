import sys
import os

# Add root of cyber-patrol-assistant to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.extractors.registry import ExtractorRegistry
from app.services.ollama_service import OllamaService

def test_extractors():
    cases = [
        ("https://www.threads.net/@suarapembaruan/post/DG24_68SZqE", "threads"),
        ("https://www.threads.com/@someone/post/12345", "threads"),
        ("https://www.instagram.com/p/Df1lENWhdQq/liked_by", "instagram"),
        ("https://x.com/Kemkominfo/status/1888000000000000000", "x"),
        ("https://twitter.com/jokowi/status/12345", "x"),
        ("https://www.facebook.com/kompascom/posts/10161400000000000", "facebook"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://news.detik.com/berita/d-12345/judul-berita", "web"),
    ]

    for url, expected_plat in cases:
        extractor = ExtractorRegistry.get_extractor(url)
        assert extractor.platform_name == expected_plat, f"Expected {expected_plat} for {url}, got {extractor.platform_name}"
        post = extractor.extract(url)
        assert post.platform == expected_plat
        print(f"PASS: Extractor {url} -> {post.platform} (canonical: {post.canonical_url})")

def test_lhm_heuristic_fallback():
    ollama = OllamaService()
    
    # 1. Judi Online
    res_judi = ollama.classify_and_summarize("Daftar sekarang di link slot gacor deposit pulsa tanpa potongan maxwin hari ini!")
    assert res_judi["predicted_category"] == "Judi Online", f"Got {res_judi['predicted_category']}"
    assert res_judi["urgency_score"] >= 3
    print(f"PASS: Judi Online -> {res_judi['predicted_category']}, urgency: {res_judi['urgency_score']}")

    # 2. Narkotika
    res_narkoba = ollama.classify_and_summarize("Polisi menangkap kurir sabu dan pengedar narkoba membawa 5 kg paket sabu")
    assert res_narkoba["predicted_category"] == "Narkotika", f"Got {res_narkoba['predicted_category']}"
    assert res_narkoba["urgency_score"] >= 3
    print(f"PASS: Narkotika -> {res_narkoba['predicted_category']}, urgency: {res_narkoba['urgency_score']}")

    # 3. Violent Extremism
    res_teror = ollama.classify_and_summarize("Ancaman teror bom bunuh diri jaringan radikal isis di fasilitas publik")
    assert res_teror["predicted_category"] == "Violent Extremism", f"Got {res_teror['predicted_category']}"
    assert res_teror["urgency_score"] >= 4
    print(f"PASS: Violent Extremism -> {res_teror['predicted_category']}, urgency: {res_teror['urgency_score']}")

    # 4. Umum / Di Luar Topik
    res_umum = ollama.classify_and_summarize("Mahasiswa berprestasi kampus memenangkan lomba inovasi teknologi dan beasiswa")
    assert res_umum["predicted_category"] == "Umum / Di Luar Topik", f"Got {res_umum['predicted_category']}"
    assert res_umum["urgency_score"] <= 2
    print(f"PASS: Umum / Di Luar Topik -> {res_umum['predicted_category']}, urgency: {res_umum['urgency_score']}")

if __name__ == "__main__":
    test_extractors()
    test_lhm_heuristic_fallback()
    print("ALL TESTS PASSED SUCCESSFULLY!")
