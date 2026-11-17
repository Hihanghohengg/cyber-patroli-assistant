# GEMINI.md — Context & Architecture Guide

## Project Overview
**TILIK** adalah platform operasional pemantauan ruang siber terpadu untuk pengumpulan barang bukti digital, analisis intelijen isu strategis (**IPOLEKSOSBUDHANKAM**), penegakan rantai bukti (*Chain of Custody*) berstandar kriptografi **NIST FIPS 198-1 HMAC-SHA256**, serta klasifikasi adaptif bebas *retraining* (**MemPrompt Few-Shot Learning & BGE-M3 Cross-Lingual**).

Sistem menganut prinsip **100% On-Premise / Local-First**, **Forensic Integrity**, **Multi-User LAN Concurrency**, dan **Human-in-the-Loop Supremacy**.

---

## Tech Stack

| Layer | Teknologi Utama |
|---|---|
| **Backend API** | Python 3.11, FastAPI 0.110+, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Local AI & ML** | Ollama (`qwen2.5:7b` / `llama3.1:8b`), GPU Semaphore Guard (`asyncio.Semaphore(1)`), MemPrompt Few-Shot In-Context Learning, scikit-learn (Dense 384-dim L2-normalized vectors), Sastrawi (Indonesian NLP), Selective OCR (Tesseract / EasyOCR fallback) |
| **Database** | SQLite 3 (PRAGMA `journal_mode=WAL`, `busy_timeout=60000` untuk konkurensi LAN), support PostgreSQL 16 + pgvector |
| **Kriptografi & Forensik** | NIST FIPS 198-1 HMAC-SHA256, Kanonisasi JSON deterministik (`sort_keys=True`, `separators=(',', ':')`), Verifikasi *constant-time* (`hmac.compare_digest`), Safe dry-run tamper simulation |
| **Web Dashboard** | React 18, TypeScript 5, Vite 5, Tailwind CSS 3, Lucide React, Axios, React Router DOM 6 |
| **Browser Extension** | Chrome/Edge Manifest V3 (Universal 3-Layer: Prioritas 0 User Highlight, Layer 1 OpenGraph & JSON-LD, Layer 2 Viewport Semantic `<article>` Isolation) |
| **Pelaporan** | ReportLab (Two-Pass Numbered Official PDF Dossier) & Markdown generator |

---

## Folder Structure

```text
cyber-patrol-assistant/
├── app/                                # Backend service (FastAPI)
│   ├── api/                            # REST API router
│   │   ├── dashboard/                  # Endpoint internal dashboard analitik
│   │   └── v1/                         # Endpoint v1 (assistant, integrity, report_export, admin)
│   ├── auth/                           # Otentikasi JWT & role-based access control (RBAC)
│   ├── models/                         # Model tabel SQLAlchemy (evidence, memory, report, audit)
│   ├── schemas/                        # Pydantic schemas (validasi payload & respon)
│   ├── services/                       # Business logic (crypto, ollama, memory, ocr, report)
│   ├── database.py                     # Inisialisasi engine SQLite WAL & session maker
│   ├── config.py                       # Konfigurasi Pydantic Settings (.env loader)
│   └── main.py                         # FastAPI application entry point & background workers
│
├── dashboard/                          # Frontend cockpit (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── api/                        # HTTP client (Axios)
│   │   ├── components/                 # UI components (Layout, ThemeToggle, Charts, Badges)
│   │   └── pages/                      # View pages (Overview, ContentExplorer, Detail, Curation)
│   ├── dist/                           # Bundle produksi frontend siap saji
│   ├── package.json                    # Konfigurasi dependensi frontend
│   └── vite.config.ts                  # Konfigurasi bundler Vite
│
├── extension/                          # Browser Extension (Manifest V3)
│   ├── manifest.json                   # Konfigurasi Chrome MV3 extension
│   ├── popup.html / popup.js           # UI popup akuisisi bukti & dynamic LAN host router
│   ├── content.js / content.css        # Universal 3-Layer Injected Script
│   └── background.js                   # Service Worker MV3 (screen capture & fetch relay)
│
├── scripts/                            # Skrip otomatisasi & evaluasi
│   ├── evaluate_tilik.py               # Benchmark komparatif 24 kasus evaluasi
│   └── ingest_real_patrol_data.py      # Seeder data awal patroli
│
├── tests/                              # Automated test suites
│   ├── test_tilik_full_pipeline.py     # End-to-end full pipeline verification
│   ├── test_api_dashboard.py           # Endpoint & routing verification
│   └── test_rag_entities.py            # Retrieval & entity tests
│
├── storage/                            # Penyimpanan data lokal
│   ├── patrol.db                       # Database SQLite utama (beserta .db-wal & .db-shm)
│   ├── evidences/                      # Berkas gambar screenshot barang bukti
│   └── reports/                        # Berkas arsip laporan intelijen (.pdf & .md)
│
├── venv/                               # Virtual Environment Python
├── .env / .env.example                 # Variabel konfigurasi lingkungan
├── requirements.txt                    # Dependensi Python
└── run.py                              # Unified single-command launcher
```

---

## Key Commands

### 1. Menjalankan Sistem Penuh (Backend + Dashboard)
Jalankan salah satu perintah dari root folder atau direktori ini:
```powershell
# Dari direktori root / direktori ini:
.\run.bat

# Menggunakan PowerShell:
.\run.ps1

# Menggunakan Python launcher:
python run.py
```
- **Web Dashboard**: `http://127.0.0.1:8000/dashboard/`
- **Interactive API Docs (Swagger UI)**: `http://127.0.0.1:8000/docs`

### 2. Menjalankan Verifikasi Test Pipeline
```powershell
.\venv\Scripts\python.exe tests\test_tilik_full_pipeline.py
```

### 3. Kompilasi / Build Frontend Dashboard
```powershell
cd dashboard
npm run build
```

### 4. Menjalankan Frontend Standalone Dev Server
```powershell
cd dashboard
npm run dev
```

### 5. Menjalankan Benchmark Evaluasi Kuantitatif
```powershell
.\venv\Scripts\python.exe scripts\evaluate_tilik.py
```

---

## Project Conventions

1. **100% Local-First / Zero External Cloud:**
   - Dilarang menambahkan dependensi yang mengirimkan data patroli ke API cloud pihak ketiga.
   - Seluruh inferensi AI wajib dialirkan melalui Ollama lokal (`qwen2.5:7b`) atau deterministic heuristic fallback bila Ollama tidak aktif.

2. **Kriptografi & Integritas Bukti (NIST FIPS 198-1):**
   - Kanonisasi JSON bukti wajib deterministik alfabetis: `json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.
   - Verifikasi segel HMAC-SHA256 wajib menggunakan *constant-time comparison* (`hmac.compare_digest`).

3. **Selective Local OCR:**
   - Cek panjang teks DOM terlebih dahulu: jika `len(dom_text) >= 30` karakter, lewati (bypass) OCR untuk menghemat memori/GPU.
   - Panggil OCR (Tesseract / EasyOCR) hanya jika `len(dom_text) < 30`.

4. **Konkurensi Basis Data Multi-User LAN:**
   - Mode SQLite wajib Write-Ahead Logging (`PRAGMA journal_mode=WAL`) dengan `busy_timeout=60000` (60 detik) untuk mencegah `database is locked` saat diakses bersamaan oleh operator LAN.

5. **Human-in-the-Loop (HITL) Supremacy:**
   - Klasifikasi AI bersifat asistif. Promosi entri ke basis memori dinamis (`ValidatedMemory`) hanya dilakukan setelah divalidasi oleh analis manusia.

6. **Gaya Penulisan Kode:**
   - **Backend (Python):** PEP 8, tipe data anotasi eksplisit (*type hints*), `snake_case` untuk fungsi/variabel/modul, `PascalCase` untuk kelas.
   - **Frontend (React/TypeScript):** `PascalCase` untuk nama komponen & file JSX/TSX (`ContentDetail.tsx`), `camelCase` untuk fungsi/hooks/properti.
   - **API Routes:** Mengikuti konvensi RESTful kebab-case dengan prefiks `/api/v1/...`.
