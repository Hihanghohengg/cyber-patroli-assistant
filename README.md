# 🛡️ TILIK — Sistem Pemantauan & Analisis Konten Siber

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Extension](https://img.shields.io/badge/Browser_Extension-Manifest_V3-4285F4?style=flat&logo=googlechrome&logoColor=white)](extension/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM_qwen2.5:7b-black?style=flat&logo=ollama&logoColor=white)](https://ollama.com/)
[![SQLite WAL](https://img.shields.io/badge/Database-SQLite_WAL_Mode-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/wal.html)
[![Cryptography](https://img.shields.io/badge/Integrity-NIST_FIPS_198--1_HMAC--SHA256-10b981?style=flat)]()
[![Status](https://img.shields.io/badge/Status-Field_Validated_Ready-10b981?style=flat)]()

> **TILIK** adalah platform operasional pemantauan ruang siber terpadu untuk pengumpulan barang bukti digital, analisis intelijen isu strategis (**IPOLEKSOSBUDHANKAM**), penegakan rantai bukti (*Chain of Custody*) berstandar kriptografi **NIST FIPS 198-1 HMAC-SHA256**, serta klasifikasi adaptif bebas *retraining* (**MemPrompt Few-Shot Learning**).

---

## 🏛️ Batasan Arsitektur Utama (*Core Architectural Constraints*)

1. **100% On-Premise / Local-First:** Seluruh pemrosesan (ekstraksi konten, OCR, embedding vektor, inferensi LLM, dan basis data) berjalan sepenuhnya di infrastruktur lokal/intranet tertutup tanpa mengirim satu bita pun data ke API cloud eksternal demi kerahasiaan data operasional dinas intelijen siber.
2. **Multi-User LAN Ready:** Arsitektur mendukung penggunaan bersamaan oleh beberapa operator patroli melalui jaringan area lokal (LAN) dengan identitas operator (`operator_id`), antrean pemrosesan asinkron dengan penjagaan semafor memori/GPU, serta konkurensi basis data mode SQLite Write-Ahead Logging (WAL) ber-timeout 60 detik.
3. **Deterministik & Ringan (Anti Over-Engineering):** Tidak menggunakan *framework* agen otonom pihak ketiga yang berat dan tidak melakukan *fine-tuning/retraining* bobot LLM. Orkestrasi dilakukan dengan kode deterministik yang ringan, stabil, mudah diaudit, dan siap disidangkan.
4. **Single-Post Capture:** Akuisisi dipicu secara sadar oleh operator (*one click per post*) melalui Browser Extension Manifest V3, bukan *automated bulk scraping/crawling*.

---

## 📑 Daftar Isi

- [Arsitektur Sistem Terintegrasi](#-arsitektur-sistem-terintegrasi)
- [Pilar Fitur Utama Terimplementasi](#-pilar-fitur-utama-terimplementasi)
- [Skema Basis Data & Konkurensi WAL](#-skema-basis-data--konkurensi-wal)
- [Panduan Pemasangan Ekstensi Browser](#-panduan-pemasangan-ekstensi-browser)
- [Panduan Cepat Menjalankan Sistem](#-panduan-cepat-menjalankan-sistem)
- [Verifikasi Kriptografi & Simulasi Tamper](#-verifikasi-kriptografi--simulasi-tamper)
- [Tolok Ukur Evaluasi & Benchmark](#-tolok-ukur-evaluasi--benchmark)
- [Struktur Direktori Proyek](#-struktur-direktori-proyek)

---

## 🏗️ Arsitektur Sistem Terintegrasi

```
[ KLIEN PERAMBAN OPERATOR LAN ]
  └── Browser Extension (Chrome/Edge MV3)
      ├── Prioritas 0: User Highlight-to-Capture (window.getSelection() >= 10 chars)
      ├── Layer 1   : OpenGraph & JSON-LD (Portal Berita Nasional & YouTube)
      └── Layer 2   : Viewport Semantic <article> Isolation (X/Twitter, Instagram, FB, Threads, TikTok)
                      │
                      ▼ (HTTP POST /api/v1/assistant/intake + Base64 Screenshot + Timestamp UTC)
          [ BACKEND FASTAPI LOKAL (Port 8000) ]
                      │
        ┌─────────────┴────────────────────────────────────────────────┐
        ▼                                                              ▼
  [ 1. ENGINE KRIPTOGRAFI ]                                      [ 2. SELECTIVE OCR ENGINE ]
  - Kanonisasi JSON Ambiguity-Free                               - Cek Panjang Teks DOM:
    {captured_at_utc, dom_text, ocr_text,                          - Jika DOM >= 30 chars -> Skip OCR (Hemat GPU/RAM)
     operator_id, screenshot_sha256, source_url}                  - Jika DOM < 30 chars  -> Picu Local OCR (Tesseract/EasyOCR)
  - Tag HMAC-SHA256 (NIST FIPS 198-1)
  - Constant-time verification (hmac.compare_digest)
        │                                                              │
        └─────────────────────────────┬────────────────────────────────┘
                                      ▼
                        [ 3. MEMPROMPT CASE MEMORY ]
                        - Ekstraksi Vektor Dense 384-Dimensi L2-Normalized
                        - Dynamic Few-Shot In-Context Retrieval (Top-3 Kasus Tervalidasi Analis)
                        - Semantic Twin Deduplication (Threshold Cosine 0.85 dalam Hari Kalender Sama)
                                      │
                                      ▼
                      [ 4. LOCAL AI ENGINE (OLLAMA) ]
                      - Model Default: Qwen 2.5 7B / Llama 3.1 8B (http://127.0.0.1:11434)
                      - GPU Semaphore Guard (asyncio.Semaphore(1))
                      - Ekstraksi Terstruktur JSON Baku:
                        * summary_5w1h: {who, what, when, where, why, how}
                        * predicted_category: 8 Kategori IPOLEKSOSBUDHANKAM
                        * urgency_score: 1 s.d. 5
                        * ai_reasoning: Penjelasan naratif teks
                      - Failopen Heuristik Deterministik jika Ollama offline
                                      │
                                      ▼
                   [ 5. BASIS DATA & AUTONOMOUS TRENDING ]
                   - SQLite 3 dalam Mode WAL (PRAGMA journal_mode=WAL) + Timeout 60s
                   - Tabel Utama: contents, evidences, reports, validated_memory, audit_logs
                   - Autonomous Background Trending: Sinkronisasi otomatis tiap 5 menit
                                      │
                                      ▼
                  [ 6. WEB DASHBOARD COCKPIT & EKSPOR ]
                  - React 18 + Vite + Tailwind CSS (Cyber-Dark & Light Mode)
                  - High-Contrast Institutional Sidebar & Tactile Theme Toggle
                  - Kurasi Analis Human-in-the-Loop (HITL)
                  - Ekspor Rekapitulasi Harian: Markdown (.md) & PDF Resmi 2-Pass (ReportLab)
```

---

## ⚡ Pilar Fitur Utama Terimplementasi

### 1. Cryptographic Integrity Engine (NIST FIPS 198-1)
* **Kanonisasi Bebas Ambigu:** Seluruh berkas bukti digital diserialisasi deterministik menggunakan JSON kanonik alfabetis (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`) yang mengikat secara erat: `screenshot_sha256`, `source_url`, `dom_text`, `ocr_text`, `captured_at_utc`, dan `operator_id`.
* **Penyegelan HMAC-SHA256:** Dihasilkan menggunakan kunci rahasia simetris `SECRET_HMAC_KEY` dari lingkungan server tertutup, mencegah pemalsuan bukti di sisi klien.
* **Verifikasi *Constant-Time*:** Menggunakan `hmac.compare_digest` untuk mengeliminasi kerentanan *timing attacks*.
* **Simulasi Tamper Aman (*Dry-Run*):** Pengujian manipulasi 1-bit pada citra (`IMAGE_BIT_FLIP`), perubahan karakter teks (`TEXT_MUTATION`), dan pemalsuan metadata (`METADATA_SPOOF`) dapat disimulasikan tanpa merusak integritas rekaman asli di disk/database.

### 2. Universal 3-Layer Browser Extension (MV3)
* **Prioritas 0 (Highlight-to-Capture):** Jika operator memblok teks penting di layar sebelum klik tangkap, teks tersebut langsung dijadikan narasi primer (`user_highlight`).
* **Layer 1 (OpenGraph & JSON-LD):** Mengekstrak metadata terstruktur artikel dari portal berita nasional (Kompas, Detik, Tempo) dan YouTube.
* **Layer 2 (Viewport Semantic `<article>` & Anti-Noise Filtering):**
  * Untuk media sosial (X/Twitter, Instagram, Facebook, Threads, TikTok), sistem mengunci elemen `<article>` atau `[role="article"]` di titik tengah pandangan peramban (*viewport*).
  * **Ekstraksi Presisi H1 & Pemisahan Komentar:** Pada Instagram, mengekstrak tag `<h1>` yang berisi narasi asli pembuat postingan, memisahkan komentar netizen ke array terisolasi, dan membuang sampah teks antarmuka (*"Lihat terjemahan"*, banner likes, repetisi handle).
  * **Rekaman Layar Bersih (*Clean Screenshot*):** Badge dan modal triase otomatis disembunyikan menggunakan kelas CSS `.cp-capturing` (`display:none !important`) dengan jeda 120ms saat penangkapan layar, menjamin barang bukti murni tanpa elemen UI ekstensi.
* **Dynamic LAN Routing:** Operator dapat mengatur alamat IP server dinas LAN (`http://192.168.x.x:8000`) dan ID operator langsung dari antarmuka *popup* ekstensi dengan indikator koneksi instan (*health check ping*).

### 3. Local AI Engine, Sintesis Analitis, & MemPrompt Adaptive Learning
* **Inferensi 100% On-Premise via Ollama:** Menjalankan model `qwen2.5:7b` lokal dengan *prompt template* terstruktur ketat untuk ekstraksi 5W+1H dan 8 kategori IPOLEKSOSBUDHANKAM (*Ideologi, Politik, Ekonomi, Sosial, Budaya, Pertahanan, Keamanan, Non-Isu*).
* **Sintesis Analitis Human-Grade (Anti Copy-Paste):** Ringkasan disusun dalam bentuk analisis narasi aktif berbasis aktor dan peristiwa (contoh: *"Konten membahas Mantan Kapolri Jenderal Listyo Sigit Prabowo terkait dugaan makar dan ilegal akses"*), menolak pemotongan mentah (*raw copy-paste slicing*) dan artefak titik berulang (`....`).
* **Severity-Weighted Urgency Scoring (Skala 1–5):**
  * Skor 5 / Bahaya Tinggi (`PERINGATAN`): Isu makar, separatisme, teror bom.
  * Skor 4 / Kriminal Khusus (`PERINGATAN`): Tersangka tindak pidana, ilegal akses, korupsi.
  * Skor 3 / Perhatian Khusus (`WASPADA`): Isu politik kekuasaan, pengunduran diri pejabat negara, judi online.
  * Skor 1–2 / Edukatif (`AMAN`): Konten wajar, rekrutmen komunitas, informasi akademik.
* **Pre-Flight Socket Health Check (0.02s Fail-Fast):** Pemeriksaan konektivitas jaringan tertutup (<0.05s) mencegah *hang* 60 detik akibat timeout gateway cloud eksternal.
* **GPU Semaphore Concurrency:** Penggunaan `asyncio.Semaphore(1)` / `threading.Semaphore(1)` memastikan permintaan bersamaan dari banyak operator LAN diantrekan secara berurutan sehingga memori GPU/VRAM tidak mengalami *Out-Of-Memory* (OOM).
* **Selective Local OCR:** OCR hanya dipicu jika panjang teks DOM `< 30` karakter (misal: infografis / tangkapan gambar Instagram). Konten berita teks panjang dilewati seketika untuk menghemat komputasi lokal.
* **MemPrompt Case Memory:** Menggunakan proyeksi vektor dense 384-dimensi L2-normalized. Saat ada kasus baru, sistem menarik top-3 preseden tervalidasi analis manusia terdahulu (*cosine similarity*) dan menyuntikkannya ke *prompt* LLM (*dynamic few-shot*), meningkatkan akurasi klasifikasi tanpa *fine-tuning*.
* **Deduplikasi Semantik Harian:** Otomatis mendeteksi postingan kembar yang dilaporkan oleh beberapa personel patroli pada hari yang sama menggunakan ambang batas kemiripan kosinus $\ge 0.85$.

### 4. Forensic Web Cockpit & Laporan Harian Otomatis
* **Antarmuka Taktis Berstandar Forensik:** Konsol web berbasis React + Tailwind CSS dengan transisi tema *Cyber-Dark* / *Light* yang mulus, *tactile theme toggle*, dan navigasi bilah samping (*sidebar*) berkontras tinggi.
* **Otomasi Radar Tren Isu:** Penghitungan skor tren topik berjalan otomatis di latar belakang (*autonomous background worker*) tiap 5 menit dan saat server menyala tanpa tombol manual.
* **Ekspor Rekapitulasi Harian:**
  * **Format Markdown (`.md`):** Format ringkas terstruktur untuk catatan operasional cepat.
  * **Format PDF Resmi Dua-Pass (`.pdf`):** Menghasilkan berkas dossier resmi berpenomoran urut menggunakan ReportLab, tabel kronologi 5W+1H, badge kategori IPOLEKSOSBUDHANKAM, tautan aktif, gambar tangkapan layar, stempel forensik, dan segel verifikasi HMAC-SHA256.

---

## 🗄️ Skema Basis Data & Konkurensi WAL

Sistem menggunakan SQLite 3 dengan mode **Write-Ahead Logging (WAL)**:
* `PRAGMA journal_mode=WAL;`
* `PRAGMA busy_timeout=60000;` (Mencegah error *database locked* saat banyak operator menyimpan bukti bersamaan)
* `PRAGMA synchronous=NORMAL;`

### Tabel Fisik Relasional Utama:
1. **`contents`**: Metadata konten patroli (`url`, `dom_text`, `ocr_text`, `canonical_hash`, `hmac_tag`, `operator_id`, `verification_status`).
2. **`evidences`**: Bukti citra digital (`file_hash_sha256`, path penyimpanan lokal, pHash citra).
3. **`reports`**: Siklus hidup tiket patroli (`ticket_number`, status analisis, 5W+1H, kategori IPOLEKSOSBUDHANKAM, skor urgensi 1–5).
4. **`validated_memory`**: Memori pembelajaran adaptif MemPrompt (`content_text`, `embedding_vector` 384-d, `validated_category`, `analyst_rationale`, `validated_by`, `urgency_score`).
5. **`topics` & `topic_snapshots`**: Radar topik tren dinamis dan riwayat perhitungan skor lonjakan isu.
6. **`audit_logs`**: Catatan rantai audit forensik tindakan sistem dan keputusan operator.

---

## 🧩 Panduan Pemasangan Ekstensi Browser

Ekstensi terletak pada direktori `extension/` dan memenuhi standar Google Chrome Manifest V3:

1. Buka peramban kerja (Google Chrome, Microsoft Edge, atau Brave).
2. Akses halaman manajemen ekstensi:
   * Chrome: `chrome://extensions/`
   * Edge: `edge://extensions/`
3. Aktifkan **Developer mode** (Mode pengembang) di sudut kanan atas.
4. Klik tombol **Load unpacked** (Muat yang belum dibongkar).
5. Pilih folder:
   ```
   d:\Obed\mini project\cyber-patrol-assistant\extension
   ```
6. Klik ikon ekstensi **TILIK** pada bilah peramban:
   * Masukkan **ID Operator** (contoh: `op_d23_01`).
   * Masukkan **Alamat Server** (default lokal: `http://127.0.0.1:8000` atau IP server LAN).
   * Status koneksi akan otomatis berubah menjadi hijau (**Terhubung**).
7. Buka tautan media sosial / portal berita, lalu klik **⚡ Triase Konten (Universal 3-Layer)**. Bukti akan langsung disegel secara kriptografis dan masuk ke dasbor.

---

## 🚀 Panduan Cepat Menjalankan Sistem

### 1. Prasyarat Lingkungan
* Python 3.11+
* Node.js 18+ & npm
* Ollama (opsional untuk inferensi AI lokal; sistem menyediakan *deterministic heuristic fallback* jika Ollama offline).

### 2. Konfigurasi Lingkungan (`.env`)
Salin berkas konfigurasi template:
```bash
cp .env.example .env
```
Pastikan kunci kriptografi terisi (contoh):
```ini
SECRET_HMAC_KEY="kunci-rahasia-hmac-sha256-tilik-fips198-rplk-2026"
OLLAMA_BASE_URL="http://127.0.0.1:11434"
OLLAMA_MODEL="qwen2.5:7b"
DATABASE_URL="sqlite:///./storage/patrol.db"
```

### 3. Menjalankan Model AI Lokal (Ollama)
Jika menggunakan inferensi LLM lokal:
```bash
ollama serve
ollama pull qwen2.5:7b
```

### 4. Menjalankan Seluruh Sistem (Single Command)
Cukup jalankan satu skrip eksekusi tunggal dari terminal *root* proyek:
```powershell
.\run.bat
```
Atau menggunakan PowerShell:
```powershell
.\run.ps1
```
Skrip ini secara otomatis:
1. Memverifikasi dan mengaktifkan Python Virtual Environment (`venv`).
2. Menjalankan backend FastAPI pada `http://127.0.0.1:8000`.
3. Menyajikan web dashboard statis yang telah dikompilasi pada `http://127.0.0.1:8000/dashboard/`.
4. Membuka peramban secara otomatis dan berhenti bersih (*clean shutdown*) jika ditekan `Ctrl+C`.

---

## 🔐 Verifikasi Kriptografi & Simulasi Tamper

TILIK menyediakan endpoint pengujian forensik mandiri untuk membuktikan keabsahan rantai bukti dan mendeteksi manipulasi data:

### Verifikasi Keabsahan Tiket:
```http
GET /api/v1/integrity/verify/{ticket_number}
```
*Respons:*
```json
{
  "status": "success",
  "ticket_number": "PS-20261113-0001",
  "verification_status": "VERIFIED",
  "computed_hmac": "f2a87ed9602f931173e90d23c639acdc...",
  "stored_hmac": "f2a87ed9602f931173e90d23c639acdc...",
  "match": true,
  "verification_time_ms": 0.024
}
```

### Pengujian Manipulasi Aman (*Dry-Run Tamper Test*):
```http
POST /api/v1/integrity/tamper-test
Content-Type: application/json

{
  "ticket_or_id": "PS-20261113-0001",
  "tamper_mode": "IMAGE_BIT_FLIP",
  "dry_run": true
}
```
*Respons:*
```json
{
  "status": "success",
  "tamper_simulation": "IMAGE_BIT_FLIP",
  "tampered_verification_status": "TAMPERED",
  "detected": true,
  "tamper_details": "Simulasi 1-bit flip citra mengubah hash SHA-256. HMAC tidak lagi cocok.",
  "latency_ms": 0.028
}
```

---

## 📊 Tolok Ukur Evaluasi & Benchmark

Sistem dilengkapi skrip evaluasi kuantitatif mandiri untuk menguji performa klasifikasi AI pada 24 kasus nyata 8 bidang IPOLEKSOSBUDHANKAM (Ollama `qwen2.5:3b` & `bge-m3`):
```bash
python scripts/evaluate_tilik.py
```

### Profil Performa Sistem Aktual:
| Parameter / Metrik Pengujian | Nilai Performa Aktual | Keterangan Operasional |
|---|:---:|---|
| **Akurasi Klasifikasi** | **95.83%** (23/24 kasus) | 23 dari 24 kasus uji teridentifikasi tepat sesuai *ground-truth* |
| **Macro Precision** | **96.88%** | Rata-rata presisi prediksi antarseluruh 8 bidang isu |
| **Macro Recall** | **95.83%** | Rata-rata sensitivitas penangkapan isu antarseluruh 8 bidang |
| **Macro F1-Score** | **95.71%** | Keseimbangan harmonik presisi dan recall |
| **Rerata Latensi Retrieval (BGE-M3)** | **2,505.12 ms** | Pencarian preseden semantik vektor *dense* 384-dimensi L2 |
| **Rerata Latensi Pipeline (CPU 8-Thread)** | **158.84 s** | Inferensi lokal penuh tanpa ketergantungan koneksi internet eksternal |
| **F1-Score Bidang Ideologi** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Politik** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Ekonomi** | **85.7%** | Sangat Kuat (Precision: 75.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Sosial** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Budaya** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Pertahanan** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |
| **F1-Score Bidang Keamanan** | **80.0%** | Kuat (Precision: 100.0%, Recall: 66.7%, 2/3 kasus) |
| **F1-Score Bidang Non-Isu** | **100.0%** | Sempurna (Precision: 100.0%, Recall: 100.0%, 3/3 kasus) |

*Berkas hasil pengujian tersimpan otomatis dalam:*
* `storage/evaluation_results.json` (Detail metrik dan profil per kasus).
* `storage/evaluation_results.csv` (Tabel terstruktur untuk lampiran Bab IV Tugas Akhir).

---

## 📁 Struktur Direktori Proyek

```
cyber-patrol-assistant/
├── .env.example                     # Template konfigurasi environment lokal
├── run.bat                          # Launcher instan Windows (Batch)
├── run.ps1                          # Launcher instan Windows (PowerShell)
├── run.py                           # Runner terpadu FastAPI + Web Dashboard
├── requirements.txt                 # Dependensi Python
├── SYSTEM_PRD_AND_ARCHITECTURE.md   # Dokumen spesifikasi kebutuhan produk & arsitektur resmi
├── README.md                        # Dokumentasi sistem & panduan operasional
├── extension/                       # Universal 3-Layer Browser Extension (Manifest V3)
│   ├── manifest.json                # Konfigurasi MV3 resmi
│   ├── popup.html / popup.js        # Antarmuka popup akuisisi bukti & router LAN dinamis
│   ├── content.js / content.css     # Skrip injeksi Universal 3-Layer (Highlight, News, Social)
│   └── background.js                # Service worker peramban
├── dashboard/                       # Frontend Web Cockpit (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── pages/                   # Overview, ContentDetail, ContentExplorer, Analytics, Curation
│   │   ├── components/layout/       # Sidebar (High-Contrast), Navbar, DashboardLayout
│   │   ├── components/common/       # ThemeToggle, Badge, Charts, KPICard
│   │   └── api/client.ts            # API Client Axios (Intake, Integrity, Report Export)
│   └── dist/                        # Bundle produksi siap saji
├── app/
│   ├── main.py                      # Server FastAPI, CORS, Lifespan, & Auto-Trending Worker
│   ├── config.py                    # Konfigurasi Pydantic BaseSettings
│   ├── database.py                  # Engine SQLite WAL Mode + Migrasi Otomatis Skema
│   ├── models/                      # ORM SQLAlchemy (report, evidence, memory, audit)
│   │   └── memory.py                # Tabel validated_memory untuk preseden analis
│   ├── services/                    # Domain Layanan Bisnis & Kriptografi
│   │   ├── crypto_service.py        # NIST FIPS 198-1 HMAC-SHA256 & Constant-Time Engine
│   │   ├── ollama_service.py        # Local Ollama Inference & Structured Output 5W+1H
│   │   ├── memory_service.py        # MemPrompt Few-Shot & Semantic Twin Deduplication
│   │   ├── ocr_service.py           # Selective Local OCR Engine (< 30 chars threshold)
│   │   └── pdf_report_service.py    # ReportLab Two-Pass Numbered PDF Dossier Generator
│   └── api/
│       ├── v1/                      # REST API Endpoints:
│       │   ├── assistant.py         # POST /api/v1/assistant/intake & /classify
│       │   ├── integrity.py         # GET /verify/{id} & POST /tamper-test
│       │   └── report_export.py     # GET /api/v1/reports/daily-export (.md / .pdf)
│       └── dashboard/               # Endpoint dashboard analitik, radar tren, & kurasi HITL
├── scripts/
│   ├── evaluate_tilik.py            # Tolok ukur evaluasi kuantitatif komparatif (24 kasus)
│   └── ingest_real_patrol_data.py   # Skrip seeding data patroli nyata
├── tests/
│   └── test_tilik_full_pipeline.py  # Test suite otomatis seluruh pipeline TILIK (5 skenario)
└── storage/
    ├── evidences/                   # Penyimpanan citra tangkapan layar lokal
    ├── reports/                     # Arsip berkas laporan dinas PDF & Markdown
    └── patrol.db                    # Basis data SQLite lokal (dengan berkas -wal & -shm)
```

---

## 🧪 Pengujian Otomatis Seluruh Pipeline

Jalankan seluruh pengujian integrasi otomatis dari terminal:
```bash
python tests/test_tilik_full_pipeline.py
```
*Hasil:*
```text
================================================================================
      [+] TEST AUTOMATISASI AKHIR PIPELINE PENUH TILIK (FASE 1 - 4)
================================================================================

[TEST 1] Menguji Cryptographic Seal & Constant-Time Verification...
  [✓] Seal generated: f2a87ed9... | Verification: VERIFIED in 0.02ms
  [✓] Tamper 1-bit flip simulation properly detected as: TAMPERED in 0.027ms

[TEST 2] Menguji Selective OCR Engine...
  [✓] Long DOM text correctly bypassed OCR
  [✓] Short DOM text without image handled gracefully without crash

[TEST 3] Menguji MemPrompt Case Memory & Dense Vector Retrieval...
  [✓] Gated memory entry created (Category: Keamanan)
  [✓] Dense vector retrieval found 3 similar cases in 3.4ms

[TEST 4] Menguji Ollama Local Intelligence & Heuristic Failopen...
  [✓] Inference classified as: Sosial (Urgency: 3/5) | 5W1H What: Kerusuhan SARA

[TEST 5] Menguji Semantic Deduplication Engine...
  [✓] Semantic duplicate check completed successfully: is_dup=False

================================================================================
          [✓] SELURUH PIPELINE TILIK (FASE 1 - 4) TERVERIFIKASI 100% SUKSES
================================================================================
```

---
**TILIK — Sistem Pemantauan & Analisis Konten Siber**  
*Platform Pemantauan Siber Lokal & Berintegritas Kriptografis*
