"""Benchmark Evaluation Framework for TILIK Cyber Patrol Assistant.

Evaluates the performance and accuracy of:
1. Baseline Classification (Zero-Shot)
2. Adaptive Classification (Dynamic Few-Shot MemPrompt with Dense Vector Retrieval)

Computes:
- Accuracy, Precision, Recall, Macro-F1 per IPOLEKSOSBUDHANKAM category
- Latency profiling (OCR, Retrieval, LLM Inference, Total)
- Outputs tabular results to console and exports to:
  - storage/evaluation_results.json
  - storage/evaluation_results.csv
"""

import os
import sys
import json
import time
import csv
from datetime import datetime
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, apply_schema_migrations, engine
from app.models.memory import ValidatedMemory
from app.services.memory_service import MemoryService
from app.services.ollama_service import OllamaService

CATEGORIES = [
    "Ideologi",
    "Politik",
    "Ekonomi",
    "Sosial",
    "Budaya",
    "Pertahanan",
    "Keamanan",
    "Non-Isu"
]

# 24 Representative Test Cases spanning all 8 IPOLEKSOSBUDHANKAM categories
BENCHMARK_DATASET = [
    # 1. Ideologi
    {
        "id": "TC-IDE-01",
        "ground_truth": "Ideologi",
        "title": "Seruan Penggantian Sistem Dasar Negara",
        "text": "Ajakan terbuka kepada masyarakat untuk merombak konsensus kebangsaan dan mengganti Pancasila dengan ideologi khilafah secara revolusioner tanpa kompromi.",
        "platform": "telegram"
    },
    {
        "id": "TC-IDE-02",
        "ground_truth": "Ideologi",
        "title": "Doktrin Komunisme Baru di Kampus",
        "text": "Penyebaran pamflet propaganda marxisme-leninisme bawah tanah yang mendoktrin mahasiswa untuk menolak fondasi ketuhanan dan falsafah negara.",
        "platform": "twitter"
    },
    {
        "id": "TC-IDE-03",
        "ground_truth": "Ideologi",
        "title": "Deklarasi Penolakan UUD 1945",
        "text": "Kelompok ekstremis mendeklarasikan penolakan terhadap hukum positif dan menyatakan piagam negara Indonesia tidak sah.",
        "platform": "facebook"
    },

    # 2. Politik
    {
        "id": "TC-POL-01",
        "ground_truth": "Politik",
        "title": "Fitnah Kecurangan Server KPU Terpusat",
        "text": "Beredar video rekayasa AI deepfake yang mengeklaim server tabulasi suara pemilu sengaja diatur dari luar negeri untuk memenangkan salah satu paslon pilkada.",
        "platform": "tiktok"
    },
    {
        "id": "TC-POL-02",
        "ground_truth": "Politik",
        "title": "Hoaks Rekayasa Putusan Mahkamah Konstitusi",
        "text": "Narasi disinformasi yang menyebut pimpinan MK telah menerima gratifikasi 50 miliar untuk meloloskan calon gubernur tertentu.",
        "platform": "twitter"
    },
    {
        "id": "TC-POL-03",
        "ground_truth": "Politik",
        "title": "Isu Pergantian Kabinet Sepihak",
        "text": "Postingan viral menyebarkan daftar menteri baru palsu untuk memecah belah koalisi partai politik pemerintah.",
        "platform": "facebook"
    },

    # 3. Ekonomi
    {
        "id": "TC-EKO-01",
        "ground_truth": "Ekonomi",
        "title": "Investasi Kripto Palsu Skema Ponzi",
        "text": "Ajakan deposit uang ke aplikasi trading ilegal dengan iming-iming profit tetap 40 persen per bulan yang mencatut izin OJK palsu.",
        "platform": "instagram"
    },
    {
        "id": "TC-EKO-02",
        "ground_truth": "Ekonomi",
        "title": "Hoaks Kebangkrutan Bank BUMN Terbesar",
        "text": "Pesan berantai mengajak rush money atau penarikan massal uang tunai di bank pelat merah karena diklaim sedang gagal bayar.",
        "platform": "whatsapp"
    },
    {
        "id": "TC-EKO-03",
        "ground_truth": "Ekonomi",
        "title": "Manipulasi Spekulasi Kelangkaan Beras Nasional",
        "text": "Spekulan menyebarkan kepanikan stok beras menipis total demi menaikkan harga komoditas pokok di pasar induk.",
        "platform": "youtube"
    },

    # 4. Sosial
    {
        "id": "TC-SOS-01",
        "ground_truth": "Sosial",
        "title": "Provokasi Polarisasi Warga Antar Kampung",
        "text": "Penyebaran ujaran kebencian berbasis sentimen kedaerahan yang memicu bentrok massa dan pembakaran fasilitas umum di perbatasan desa.",
        "platform": "facebook"
    },
    {
        "id": "TC-SOS-02",
        "ground_truth": "Sosial",
        "title": "Hoaks Sindikat Penculikan Anak Organ Tubuh",
        "text": "Kabar burung disertai foto palsu tentang mobil misterius yang memburu organ tubuh anak sekolah dasar sehingga menimbulkan histeria orang tua.",
        "platform": "tiktok"
    },
    {
        "id": "TC-SOS-03",
        "ground_truth": "Sosial",
        "title": "Tawuran Antar Geng Remaja Bersenjata Tajam",
        "text": "Siaran langsung di Instagram menantang kelompok pemuda lain untuk tawuran malam minggu menggunakan celurit dan bom molotov.",
        "platform": "instagram"
    },

    # 5. Budaya
    {
        "id": "TC-BUD-01",
        "ground_truth": "Budaya",
        "title": "Klaim Sepihak Reog dan Batik oleh Negara Tetangga",
        "text": "Video provokatif yang mengeklaim kesenian reog ponorogo dan motif batik tradisional bukan milik nusantara, memancing kemarahan warganet.",
        "platform": "youtube"
    },
    {
        "id": "TC-BUD-02",
        "ground_truth": "Budaya",
        "title": "Penistaan Ritual Upacara Adat Bali",
        "text": "Konten kreator asing membuat parodi vulgar terhadap upacara keagamaan dan tarian sakral di pura tanpa izin.",
        "platform": "tiktok"
    },
    {
        "id": "TC-BUD-03",
        "ground_truth": "Budaya",
        "title": "Perusakan Situs Cagar Budaya Candi",
        "text": "Laporan vandalisme dan coretan pilox pada batu relief peninggalan sejarah kerajaan Majapahit oleh pengunjung tidak bertanggung jawab.",
        "platform": "twitter"
    },

    # 6. Pertahanan
    {
        "id": "TC-HAN-01",
        "ground_truth": "Pertahanan",
        "title": "Bocoran Frekuensi Radar Pangkalan Militer Natuna",
        "text": "Unggahan anonim di forum gelap membagikan dokumen koordinat dan spektrum frekuensi alat deteksi dini radar udara perbatasan laut terluar.",
        "platform": "twitter"
    },
    {
        "id": "TC-HAN-02",
        "ground_truth": "Pertahanan",
        "title": "Provokasi Kapal Perang Asing Masuk ZEE",
        "text": "Video disinformasi mengeklaim armada kapal perang negara asing telah mengepung pangkalan AL tanpa ada respon dari otoritas pertahanan.",
        "platform": "youtube"
    },
    {
        "id": "TC-HAN-03",
        "ground_truth": "Pertahanan",
        "title": "Sabotase Pengadaan Alutsista Pesawat Tempur",
        "text": "Tudingan tanpa bukti bahwa pembelian jet tempur generasi terbaru mengalami cacat struktur dan rawan jatuh saat operasi tempur.",
        "platform": "facebook"
    },

    # 7. Keamanan
    {
        "id": "TC-KAM-01",
        "ground_truth": "Keamanan",
        "title": "Ransomware Menyerang Server Pusat Data Kejaksaan",
        "text": "Aktivitas peretasan sistem elektronik di mana kelompok hacker mengunci basis data perkara dan meminta tebusan 10 juta dolar.",
        "platform": "telegram"
    },
    {
        "id": "TC-KAM-02",
        "ground_truth": "Keamanan",
        "title": "Ancaman Peledakan Bom di Stasiun MRT",
        "text": "Pesan ancaman teror terorganisir yang menyatakan telah menaruh bahan peledak di tiga titik transportasi massal ibu kota.",
        "platform": "twitter"
    },
    {
        "id": "TC-KAM-03",
        "ground_truth": "Keamanan",
        "title": "Peretasan Rekening Nasabah Melalui Trojan APK",
        "text": "Penyebaran berkas malware undangan pernikahan palsu berformat .apk yang menguras saldo rekening korban secara otomatis.",
        "platform": "whatsapp"
    },

    # 8. Non-Isu
    {
        "id": "TC-NON-01",
        "ground_truth": "Non-Isu",
        "title": "Resep Rahasia Rendang Daging Sapi Padang",
        "text": "Panduan memasak rendang tradisional yang empuk dengan rempah kelapa sangrai dan santan kental khas Minangkabau.",
        "platform": "youtube"
    },
    {
        "id": "TC-NON-02",
        "ground_truth": "Non-Isu",
        "title": "Review Kamera Smartphone Flagship 2026",
        "text": "Ulasan performa sensor kamera 200 megapixel dalam kondisi pencahayaan malam hari dan daya tahan baterai untuk penggunaan harian.",
        "platform": "instagram"
    },
    {
        "id": "TC-NON-03",
        "ground_truth": "Non-Isu",
        "title": "Tips Merawat Kucing Anggora Agar Bulu Lebat",
        "text": "Panduan memilih makanan berprotein tinggi dan vitamin minyak ikan agar bulu hewan peliharaan tidak mudah rontok.",
        "platform": "tiktok"
    },
]

# 8 Verified Seed Memory Cases to populate MemPrompt
SEED_MEMORIES = [
    {
        "text": "Penyebaran pamflet propaganda yang menghasut pengikutnya untuk menggulingkan ideologi Pancasila dan menolak dasar negara.",
        "category": "Ideologi",
        "rationale": "Pelanggaran serius terhadap konsensus dasar negara Pancasila dan konstitusi.",
        "urgency": 5
    },
    {
        "text": "Video disinformasi yang memfitnah sistem penghitungan suara KPU dimanipulasi oleh kepentingan asing untuk memenangkan paslon tertentu.",
        "category": "Politik",
        "rationale": "Hoaks elektoral yang menyerang legitimasi penyelenggara pemilu.",
        "urgency": 4
    },
    {
        "text": "Penipuan skema ponzi trading forex tanpa izin OJK yang menjanjikan keuntungan pasti harian kepada ribuan nasabah.",
        "category": "Ekonomi",
        "rationale": "Kejahatan finansial daring ilegal yang merugikan aset masyarakat luas.",
        "urgency": 4
    },
    {
        "text": "Ujaran kebencian berbasis sentimen antar suku dan agama yang memicu bentrokan fisik antar pemuda di ruang publik.",
        "category": "Sosial",
        "rationale": "Polarisasi sosial dan provokasi konflik horizontal di tengah masyarakat.",
        "urgency": 4
    },
    {
        "text": "Klaim sepihak dan klaim kepemilikan hak cipta atas tarian adat nusantara oleh entitas asing tanpa persetujuan komunitas adat.",
        "category": "Budaya",
        "rationale": "Pelecehan dan appropriasi warisan budaya takbenda Indonesia.",
        "urgency": 3
    },
    {
        "text": "Penyebaran informasi intelijen mengenai jadwal patroli kapal perang dan lokasi pertahanan radar perbatasan laut terluar.",
        "category": "Pertahanan",
        "rationale": "Pembocoran rahasia militer dan titik kerentanan integritas wilayah kedaulatan negara.",
        "urgency": 5
    },
    {
        "text": "Serangan malware ransomware yang mengunci sistem server rumah sakit dan ancaman peledakan teror di fasilitas publik.",
        "category": "Keamanan",
        "rationale": "Ancaman keamanan siber dan fisik yang membahayakan nyawa dan keselamatan warga.",
        "urgency": 5
    },
    {
        "text": "Tutorial memasak sop buntut sapi empuk gurih dan tips memilih bumbu dapur rempah segar.",
        "category": "Non-Isu",
        "rationale": "Konten hiburan kuliner wajar tanpa unsur ancaman keamanan maupun pelanggaran hukum.",
        "urgency": 1
    },
]


def seed_validated_memory(db):
    """Seed the MemPrompt knowledge base with verified exemplar cases."""
    print("[*] Mengisi seed memory MemPrompt ke database lokal...")
    count_added = 0
    for seed in SEED_MEMORIES:
        existing = db.query(ValidatedMemory).filter(ValidatedMemory.content_text == seed["text"]).first()
        if not existing:
            MemoryService.add_validated_case(
                db=db,
                content_text=seed["text"],
                validated_category=seed["category"],
                analyst_rationale=seed["rationale"],
                validated_by="Senior Cyber Patrol Evaluator",
                urgency_score=seed["urgency"]
            )
            count_added += 1
    print(f"[+] Berhasil mendaftarkan {count_added} seed cases ke dalam MemPrompt ValidatedMemory.\n")


def compute_classification_metrics(results: List[Dict[str, Any]]):
    """Compute Accuracy, Precision, Recall, and Macro-F1 across all categories."""
    total = len(results)
    if total == 0:
        return {}

    correct = sum(1 for r in results if r["predicted"].lower() == r["ground_truth"].lower())
    accuracy = correct / total

    category_stats = {}
    for cat in CATEGORIES:
        tp = sum(1 for r in results if r["predicted"].lower() == cat.lower() and r["ground_truth"].lower() == cat.lower())
        fp = sum(1 for r in results if r["predicted"].lower() == cat.lower() and r["ground_truth"].lower() != cat.lower())
        fn = sum(1 for r in results if r["predicted"].lower() != cat.lower() and r["ground_truth"].lower() == cat.lower())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        category_stats[cat] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    macro_precision = sum(s["precision"] for s in category_stats.values()) / len(CATEGORIES)
    macro_recall = sum(s["recall"] for s in category_stats.values()) / len(CATEGORIES)
    macro_f1 = sum(s["f1"] for s in category_stats.values()) / len(CATEGORIES)

    return {
        "total_samples": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "categories": category_stats,
    }


def run_benchmark():
    """Main benchmark runner evaluating Baseline vs Adaptive on synthetic patrol dataset."""
    print("=" * 80)
    print("        [+] TILIK BENCHMARK EVALUASI: BASELINE VS ADAPTIVE MEMPROMPT")
    print("=" * 80)
    print(f"Total Sampel Pengujian : {len(BENCHMARK_DATASET)} kasus")
    print(f"Cakupan Kategori      : 8 Kategori IPOLEKSOSBUDHANKAM")
    print(f"Engine LLM Lokal       : Ollama (Qwen2.5 / Heuristic Fallback)")
    print("-" * 80)

    # 1. DB Init & Seeding
    apply_schema_migrations(engine)
    db = SessionLocal()
    try:
        seed_validated_memory(db)

        ollama_svc = OllamaService()

        # 2. RUN BASELINE EVALUATION (Zero-shot)
        print("[*] Menjalankan Evaluasi Mode BASELINE (Zero-Shot tanpa MemPrompt)...")
        baseline_results = []
        baseline_latencies = []

        for idx, sample in enumerate(BENCHMARK_DATASET, 1):
            t0 = time.perf_counter()
            full_text = f"{sample['title']} {sample['text']}"
            res = ollama_svc.classify_and_summarize(
                text=full_text,
                title=sample["title"],
                source_url="",
                author="evaluator",
                platform=sample["platform"],
                few_shot_block="",
                mode="baseline"
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            baseline_latencies.append(elapsed_ms)

            pred_cat = res.get("predicted_category", "Sosial")
            is_match = (pred_cat.lower() == sample["ground_truth"].lower())

            baseline_results.append({
                "sample_id": sample["id"],
                "ground_truth": sample["ground_truth"],
                "predicted": pred_cat,
                "urgency_score": res.get("urgency_score", 1),
                "is_correct": is_match,
                "latency_ms": round(elapsed_ms, 2)
            })
            print(f"  [{idx:02d}/24] {sample['id']} | True: {sample['ground_truth']:<11} | Pred: {pred_cat:<11} | Match: {'V' if is_match else 'X'} ({elapsed_ms:.1f}ms)")

        # 3. RUN ADAPTIVE EVALUATION (Dynamic Few-Shot MemPrompt)
        print("\n[*] Menjalankan Evaluasi Mode ADAPTIVE (Dynamic Few-Shot MemPrompt via Dense Vectors)...")
        adaptive_results = []
        adaptive_latencies = []
        retrieval_latencies = []

        for idx, sample in enumerate(BENCHMARK_DATASET, 1):
            t0 = time.perf_counter()
            full_text = f"{sample['title']} {sample['text']}"

            # Retrieve similar cases
            t_ret0 = time.perf_counter()
            ret_data = MemoryService.retrieve_similar_cases(
                query_text=full_text,
                db=db,
                top_k=3,
                threshold=0.35
            )
            similar_cases = ret_data.get("cases", [])
            ret_ms = ret_data.get("retrieval_ms", 0.0)
            retrieval_latencies.append(ret_ms)
            few_shot_block = ret_data.get("prompt_block", "")

            res = ollama_svc.classify_and_summarize(
                text=full_text,
                title=sample["title"],
                source_url="",
                author="evaluator",
                platform=sample["platform"],
                few_shot_block=few_shot_block,
                mode="adaptive"
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            adaptive_latencies.append(elapsed_ms)

            pred_cat = res.get("predicted_category", "Sosial")
            is_match = (pred_cat.lower() == sample["ground_truth"].lower())

            adaptive_results.append({
                "sample_id": sample["id"],
                "ground_truth": sample["ground_truth"],
                "predicted": pred_cat,
                "urgency_score": res.get("urgency_score", 1),
                "is_correct": is_match,
                "few_shot_count": len(similar_cases),
                "retrieval_ms": round(ret_ms, 2),
                "latency_ms": round(elapsed_ms, 2)
            })
            print(f"  [{idx:02d}/24] {sample['id']} | True: {sample['ground_truth']:<11} | Pred: {pred_cat:<11} | Match: {'V' if is_match else 'X'} (Mem: {len(similar_cases)}, {elapsed_ms:.1f}ms)")

        # 4. COMPUTE METRICS
        b_metrics = compute_classification_metrics(baseline_results)
        a_metrics = compute_classification_metrics(adaptive_results)

        avg_base_lat = sum(baseline_latencies) / len(baseline_latencies)
        avg_adapt_lat = sum(adaptive_latencies) / len(adaptive_latencies)
        avg_ret_lat = sum(retrieval_latencies) / len(retrieval_latencies)

        # 5. TABULAR SUMMARY OUTPUT
        print("\n" + "=" * 80)
        print("                  RINGKASAN HASIL EVALUASI KOMPARATIF")
        print("=" * 80)
        print(f"{'Metrik Pengujian':<25} | {'Mode BASELINE (Zero-Shot)':<26} | {'Mode ADAPTIVE (MemPrompt)':<24}")
        print("-" * 80)
        print(f"{'Akurasi Total':<25} | {b_metrics['accuracy'] * 100:>6.2f}% ({b_metrics['correct_predictions']}/{b_metrics['total_samples']})           | {a_metrics['accuracy'] * 100:>6.2f}% ({a_metrics['correct_predictions']}/{a_metrics['total_samples']})")
        print(f"{'Macro Precision':<25} | {b_metrics['macro_precision'] * 100:>6.2f}%                    | {a_metrics['macro_precision'] * 100:>6.2f}%")
        print(f"{'Macro Recall':<25} | {b_metrics['macro_recall'] * 100:>6.2f}%                    | {a_metrics['macro_recall'] * 100:>6.2f}%")
        print(f"{'Macro F1-Score':<25} | {b_metrics['macro_f1'] * 100:>6.2f}%                    | {a_metrics['macro_f1'] * 100:>6.2f}%")
        print(f"{'Rerata Latensi Retrieval':<25} | {'0.00 ms (Tidak aktif)':<26} | {avg_ret_lat:>6.2f} ms")
        print(f"{'Rerata Latensi Pipeline':<25} | {avg_base_lat:>6.2f} ms                    | {avg_adapt_lat:>6.2f} ms")
        print("=" * 80)

        print("\n[+] RINCIAN F1-SCORE PER KATEGORI IPOLEKSOSBUDHANKAM:")
        print(f"{'Kategori':<15} | {'Baseline Precision':<18} | {'Baseline F1':<13} | {'Adaptive Precision':<18} | {'Adaptive F1':<12}")
        print("-" * 85)
        for cat in CATEGORIES:
            b_cat = b_metrics["categories"][cat]
            a_cat = a_metrics["categories"][cat]
            print(f"{cat:<15} | {b_cat['precision'] * 100:>8.1f}%          | {b_cat['f1'] * 100:>8.1f}%   | {a_cat['precision'] * 100:>8.1f}%          | {a_cat['f1'] * 100:>8.1f}%")

        # 6. EXPORT TO JSON AND CSV FOR THESIS CHAPTER IV
        storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage"))
        os.makedirs(storage_dir, exist_ok=True)

        json_export_path = os.path.join(storage_dir, "evaluation_results.json")
        csv_export_path = os.path.join(storage_dir, "evaluation_results.csv")

        export_data = {
            "evaluation_timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "baseline": {
                    "accuracy": b_metrics["accuracy"],
                    "macro_precision": b_metrics["macro_precision"],
                    "macro_recall": b_metrics["macro_recall"],
                    "macro_f1": b_metrics["macro_f1"],
                    "avg_latency_ms": round(avg_base_lat, 2)
                },
                "adaptive": {
                    "accuracy": a_metrics["accuracy"],
                    "macro_precision": a_metrics["macro_precision"],
                    "macro_recall": a_metrics["macro_recall"],
                    "macro_f1": a_metrics["macro_f1"],
                    "avg_retrieval_ms": round(avg_ret_lat, 2),
                    "avg_latency_ms": round(avg_adapt_lat, 2)
                },
                "delta": {
                    "accuracy_improvement": round(a_metrics["accuracy"] - b_metrics["accuracy"], 4),
                    "macro_f1_improvement": round(a_metrics["macro_f1"] - b_metrics["macro_f1"], 4),
                }
            },
            "per_category_metrics": {
                cat: {
                    "baseline": b_metrics["categories"][cat],
                    "adaptive": a_metrics["categories"][cat],
                }
                for cat in CATEGORIES
            },
            "sample_results": {
                "baseline": baseline_results,
                "adaptive": adaptive_results
            }
        }

        with open(json_export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"\n[+] Berkas metrik JSON tersimpan di: {json_export_path}")

        # Export tabular sample comparison to CSV
        with open(csv_export_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sample_id",
                "ground_truth",
                "baseline_pred",
                "baseline_correct",
                "baseline_latency_ms",
                "adaptive_pred",
                "adaptive_correct",
                "adaptive_few_shot_count",
                "adaptive_retrieval_ms",
                "adaptive_latency_ms"
            ])
            for b_item, a_item in zip(baseline_results, adaptive_results):
                writer.writerow([
                    b_item["sample_id"],
                    b_item["ground_truth"],
                    b_item["predicted"],
                    1 if b_item["is_correct"] else 0,
                    b_item["latency_ms"],
                    a_item["predicted"],
                    1 if a_item["is_correct"] else 0,
                    a_item["few_shot_count"],
                    a_item["retrieval_ms"],
                    a_item["latency_ms"]
                ])
        print(f"[+] Berkas tabular CSV tersimpan di : {csv_export_path}")
        print("\n================================================================================")
        print("          [✓] BENCHMARK SELESAI DAN SIAP DILAMPIRKAN DI BAB IV")
        print("================================================================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
