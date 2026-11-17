"""Live test script for Ollama inference with English input."""
import os
import sys
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ollama_service import OllamaService
from app.config import settings

def test_live_ollama():
    print("=" * 80)
    print(f"[*] MENJALANKAN UJI LIVE INFERENSI OLLAMA: {settings.OLLAMA_MODEL}")
    print(f"[*] Base URL: {settings.OLLAMA_BASE_URL} | Timeout: {settings.OLLAMA_TIMEOUT}s")
    print("=" * 80)

    svc = OllamaService()
    
    english_sample = (
        "Breaking News: Hackers have claimed responsibility for leaking sensitive database records "
        "containing identity documents and credentials from national infrastructure servers. "
        "Cybersecurity authorities are urging all critical agencies to patch vulnerabilities immediately."
    )

    print("\n[>] Mengirim narasi berbahasa Inggris ke Ollama...")
    res = svc.classify_and_summarize(
        text=english_sample,
        title="Major Cybersecurity Data Leak Detected",
        source_url="https://x.com/cybersecurity_watch/status/987654321",
        author="cybersecurity_watch",
        platform="X",
        mode="baseline"
    )

    print("\n[+] HASIL RESPONS OLLAMA:")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print(f"[*] Engine used       : {res.get('engine_used')}")
    print(f"[*] Predicted Category: {res.get('predicted_category')}")
    print(f"[*] Urgency Score     : {res.get('urgency_score')}/5")
    print(f"[*] Original Language : {res.get('original_language')}")
    print(f"[*] Indonesian Content: {res.get('indonesian_content')}")
    print(f"[*] LLM Latency       : {res.get('llm_latency_ms')} ms")
    print("=" * 80)

if __name__ == "__main__":
    test_live_ollama()
