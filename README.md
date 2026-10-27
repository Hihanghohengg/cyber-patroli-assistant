# 🛡️ Asisten Patroli Siber & Social Intelligence v3.1
### *(Field-Aligned Final: Browser Extension MV3, Multimodal RAG & Web Dashboard Analitik)*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Extension](https://img.shields.io/badge/Browser_Extension-Manifest_V3-4285F4?style=flat&logo=googlechrome&logoColor=white)](extension/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-Multimodal_+_Embeddings-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![Forensics](https://img.shields.io/badge/Forensic_Chain-SHA--256_+_Hash--Chain-10b981?style=flat)](PRD%20v3.1%20-%20Asisten%20Patroli%20Siber%20%28Field-Aligned%20Final%29.md)
[![Status](https://img.shields.io/badge/Status-Field--Aligned_Production_Ready-10b981?style=flat)]()

> **Sistem Cerdas Operasional Piket Patroli Siber & Dasbor Analitik Social Intelligence (v3.1 Field-Aligned Final)**  
> **Lokus Penugasan:** Badan Siber dan Sandi Negara (BSSN) — Tim Pengendalian Operasi Informasi (Dalinfo), Sub Tim Analisis Intelijen Siber.  
> 
> Platform terpadu analisis konten digital bermasalah, akuisisi bukti web berstandar forensik digital, pemantauan isu viral strategis (8 Bidang IPOLEKSOSBUDHANKAM), triase cerdas berbasis AI Multimodal 5W+1H, dan memori institusional (*Multimodal RAG*) dengan evaluasi buta (*blind evaluation*).
> 
> Dirancang berdasarkan kondisi operasional riil di ruangan penugasan Dalinfo D22, arahan pembimbing lapangan (Bang Zazal), serta review dosen pembimbing:
> - **Pintu Masuk Utama**: Ekstensi Peramban (*Browser Extension* Chrome/Edge/Firefox MV3) dengan *Client-First Capture* (Screenshot Full HD + Rendered DOM + SHA-256 di browser klien via WebCrypto API).
> - **Pusat Validasi**: Antrean Validasi di Web Dashboard Console (*Human-in-the-Loop* atomik dengan kode alasan wajib).
> - **Tata Kelola Akun**: 3 Peran Resmi (`OPERATOR`, `ANALYST`, `ADMIN` dengan 2FA TOTP).
> - **Kriptografi Forensik**: Hashing SHA-256 seketika di titik capture, re-verifikasi di worker, dan rantai audit *hash-chain* (`prev_hash` & `row_hash`) ber-jangkar eksternal di luar sistem.

---

## 📑 Daftar Isi

- [Dokumen Spesifikasi Produk (PRD v3.1)](#-dokumen-spesifikasi-produk-prd-v31)
- [Arsitektur Sistem (v3.1 Field-Aligned)](#-arsitektur-sistem-v31-field-aligned)
- [Matriks Penyelarasan Kebutuhan Lapangan (Notulensi D22)](#-matriks-penyelarasan-kebutuhan-lapangan-notulensi-d22)
- [Skema Basis Data 11 Tabel Relasional Resmi](#-skema-basis-data-11-tabel-relasional-resmi)
- [Panduan Pemasangan Ekstensi Browser (Chrome / Edge / Firefox)](#-panduan-pemasangan-ekstensi-browser-chrome--edge--firefox)
- [Panduan Cepat Menjalankan Sistem](#-panduan-cepat-menjalankan-sistem)
- [Fitur Utama Web Dashboard Analitik](#-fitur-utama-web-dashboard-analitik)
- [Struktur Direktori Proyek](#-struktur-direktori-proyek)
- [Pengujian Otomatis & Kesiapan Tugas Akhir](#-pengujian-otomatis--kesiapan-tugas-akhir)

---

## 📄 Dokumen Spesifikasi Produk (PRD v3.1)

Spesifikasi lengkap, model ancaman (T1–T8), DFD Level 0–2, arsitektur, dan 32 kriteria penerimaan (AC-01 s.d. AC-32) terdokumentasi secara rinci pada:
- **[PRD v3.1 — DRAF FINAL (Field-Aligned Final)](PRD%20v3.1%20-%20Asisten%20Patroli%20Siber%20%28Field-Aligned%20Final%29.md)**
- **[PRD v3 — Arsip Spesifikasi Lengkap](PRD%20v3%20-%20Asisten%20Patroli%20Siber%20%28RAG%20Terukur%20+%20Dashboard%20Analitik%29.md)**

---

## 🏗️ Arsitektur Sistem (v3.1 Field-Aligned)

```
[ KONSOL WORKSTATION OPERASIONAL ]
  ├── 1. Browser Extension (Chrome/Edge/Firefox MV3) ──► 1-Click Visible Tab Capture + DOM + SHA-256
  └── 2. Web Dashboard Console (React 18 + Vite)     ──► Antrean Validasi HITL & 9 Grafik Analitik
                      │
                      ▼
          [ FastAPI Central Service ]
    - /api/v1/auth/* (Otentikasi Argon2id + 2FA TOTP)
    - /api/v1/intake/extension (Client-First Intake)
    - /api/v1/dashboard/queue & /decide (Validasi Atomik)
    - /api/v1/dashboard/analytics (9 Visualisasi IPOLEKSOSBUDHANKAM)
    - /api/v1/admin/* (Revisi Keputusan, Kurasi Entitas, Audit Verifier)
                      │
                      ▼
                [ Redis Broker ]
                      │
                      ▼
              [ Celery Worker ]
                      │
      ┌───────────────┴────────────────┐
      ▼                                ▼
[ Pipeline Bukti Digital & OCR ]   [ Pipeline AI & RAG ]
- Re-verifikasi Hash SHA-256       - Gemini text-embedding-001 (768d L2)
- Tesseract OCR (Deterministik)    - Cosine Similarity >= 0.75 (top_k=5)
- Deteksi Duplikasi pHash (<= 6)   - RAG Fail-Open Murni (Tanpa Vektor Palsu)
- Storage Read-Only Forensik       - Gemini Vision Multimodal 5W+1H
      │                                │
      └───────────────┬────────────────┘
                      ▼
        [ Basis Data Dual-Engine ]
        - Mode Produksi : PostgreSQL 16 + pgvector (Exact Scan Cosine)
        - Mode Mandiri  : SQLite Lokal (storage/patrol.db)
        - 11 Tabel Fisik Resmi + Audit Hash-Chain Terenkripsi
                      │
                      ▼
   [ Konsol Web Dashboard & Laporan Dinas ]
   - Antrean Validasi Analis (Bukti Full HD + 5W+1H + Preseden RAG)
   - Tombol Keputusan Atomik + Kode Alasan Wajib
   - 9 Grafik Agregat Sosial Intelijen IPOLEKSOSBUDHANKAM
   - Generator Dokumen Dinas Microsoft Word (.docx) ber-Chain Head Audit
```

---

## 📋 Matriks Penyelarasan Kebutuhan Lapangan (Notulensi D22)

| Masalah Riil di Ruangan Dalinfo | Solusi Terimplementasi PRD v3.1 | Status |
|---|---|:---:|
| **Screenshot manual tidak memenuhi standar forensik** | Ekstensi otomatis mengambil tangkapan layar Full HD + rendered DOM + metadata + kalkulasi hash SHA-256 seketika di peramban klien via WebCrypto API. | ✅ Selesai |
| **Data patroli tersebar di lembar Excel lokal** | Repositori terpusat PostgreSQL 16 + form metadata baku otomatis dari ekstensi. | ✅ Selesai |
| **Serah-terima patroli ke analis lambat** | Satu alur kerja langsung: Ekstensi → Antrean Validasi Web Dashboard → Putusan Analis, tanpa file Excel perantara. | ✅ Selesai |
| **Ketergantungan layanan pihak ketiga manual** | AI Gateway mandiri format standar OpenAI, mempermudah transisi ke model lokal *on-premise*. | ✅ Selesai |
| **Visualisasi analitik terbatas** | Web Dashboard menyajikan 9 grafik agregat: tren waktu, platform, kategori, risiko, topik IPOLEKSOSBUDHANKAM, aktor publik, dan media asal. | ✅ Selesai |
| **Personel baru butuh waktu adaptasi lama** | RAG sebagai memori institusional: preseden kasus lama yang relevan otomatis disajikan di antrean validasi. | ✅ Selesai |
| **Bukti rentan disangkal keabsahannya** | Audit log ber-hash-chain (`prev_hash` & `row_hash`) dengan jangkar eksternal harian pada dokumen dinas DOCX. | ✅ Selesai |
| **Konten sama dilaporkan berulang kali** | Deteksi duplikat otomatis berbasis URL kanonikal, hash SHA-256, dan perceptual hash (pHash $\le 6$). | ✅ Selesai |
| **Tidak semua personel memakai Telegram di PC** | Ekstensi peramban (Chrome/Edge/Firefox MV3) sebagai pintu masuk utama yang universal di PC dinas. | ✅ Selesai |
| **Kliping screenshot manual melelahkan** | Satu klik tombol ekstensi (*1-Click Capture*) langsung mengekstrak dan mengarsipkan seluruh bukti. | ✅ Selesai |

---

## 🗄️ Skema Basis Data 11 Tabel Relasional Resmi

Sistem mengimplementasikan tepat **11 tabel relasional fisik resmi** yang bebas dependensi akun Telegram:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      users      │       │    contents     │       │    evidences    │
│(Argon2id + TOTP)│       │ (canonical_url) │       │ (SHA-256 64hex) │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │ (reporter/analyst)      │ (1:N)                   │ (1:N)
         ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                               reports                               │
│      (7 Status Resmi, 5W+1H, Kategori, Risiko, Topik, Cluster ID)   │
└────────┬─────────────────────────┬─────────────────────────┬────────┘
         │ (1:N)                   │ (1:N)                   │ (1:N)
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│report_revisions │       │knowledge_entries│       │  report_actors  │
│ (Revisi ADMIN)  │       │(RAG Preseden KB)│       │ (Aktor Target)  │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
┌─────────────────┐       ┌─────────────────┐                ▼
│     topics      │       │   audit_logs    │       ┌─────────────────┐
│(IPOLEKSOSBUDHANKAM)     │  (Hash-Chain)   │       │    entities     │
└─────────────────┘       └─────────────────┘       │(Aktor/Topik/Sbr)│
                                                    └────────┬────────┘
                                                             │ (1:N)
                                                             ▼
                                                    ┌─────────────────┐
                                                    │ entity_aliases  │
                                                    └─────────────────┘
```

1. **`users`**: Kredensial pengguna sistem (Argon2id, role `OPERATOR`, `ANALYST`, atau `ADMIN` dengan 2FA TOTP).
2. **`accounts`**: Profil akun media sosial sumber konten (username, platform, metadata profil).
3. **`contents`**: Metadata konten patroli (`canonical_url`, teks caption, snapshot rendered DOM).
4. **`evidences`**: Bukti tangkapan layar digital (validasi `file_hash_sha256` tepat 64 hex, pHash 16-char, storage path).
5. **`reports`**: Siklus hidup tiket patroli (7 status, raw AI fields, final label & risk, cluster ID).
6. **`report_revisions`**: Rekam jejak revisi putusan analis oleh ADMIN beserta kode alasan wajib.
7. **`report_actors`**: Relasi *many-to-many* laporan dengan aktor sasaran (`role = 'TARGET'`).
8. **`topics`**: Katalog topik terkontrol berbasis 8 bidang strategis nasional IPOLEKSOSBUDHANKAM.
9. **`entities`**: Katalog entitas kanonikal (`TOPIC`, `ACTOR`, `SOURCE` dengan status review).
10. **`entity_aliases`**: Kamus varian penulisan, singkatan, dan alias entitas.
11. **`knowledge_entries`**: Basis pengetahuan preseden RAG berjejak (`is_active`, `deactivated_at`, Vector 768-D).
12. **`audit_logs`**: Rantai audit forensik kekal (`prev_hash` & `row_hash = SHA-256(prev_hash || data)`).

---

## 🧩 Panduan Pemasangan Ekstensi Browser (Chrome / Edge / Firefox)

Ekstensi peramban terletak pada direktori `extension/` dan memenuhi standar resmi Manifest V3:

1. **Buka menu ekstensi di peramban dinas**:
   - Google Chrome: Buka `chrome://extensions/`
   - Microsoft Edge: Buka `edge://extensions/`
   - Mozilla Firefox: Buka `about:debugging#/runtime/this-firefox`
2. **Aktifkan *Developer Mode* (Mode Pengembang)** pada sudut kanan atas.
3. **Klik tombol *Load unpacked* (Muat yang belum dibongkar)**.
4. **Pilih folder**: `d:\Obed\mini project\cyber-patrol-assistant\extension`
5. **Konfigurasi Ekstensi**:
   - Klik ikon ekstensi pada toolbar browser.
   - Buka menu *Settings* (Pengaturan).
   - Masukkan alamat backend: `http://localhost:8000` (atau IP server dinas).
   - Masukkan kredensial login akun personel (Role `OPERATOR` atau `ANALYST`).
6. **Uji Coba Capture**:
   - Buka halaman media sosial (YouTube, TikTok, Instagram, X/Threads).
   - Klik ikon ekstensi dan tekan tombol **Capture Bukti Halaman Ini**.
   - Ekstensi seketika mengambil tangkapan layar Full HD, mengekstrak DOM, menghitung SHA-256, dan menampilkan nomor tiket resmi `PS-YYYYMMDD-XXXX`.

---

## 🚀 Panduan Cepat Menjalankan Sistem

### Opsi A: Mode Mandiri / Pengujian Cepat (Auto-Fallback SQLite)

Sistem dirancang cerdas untuk berjalan secara mandiri di lingkungan workstation Windows/macOS/Linux tanpa dependensi eksternal:

1. **Install dependensi Python & Headless Browser**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **Inisialisasi Database & Seeding Data Uji**:
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```
   *(Secara otomatis membuat basis data lokal `storage/patrol.db` dan menginisialisasi 11 tabel resmi).*
3. **Jalankan Backend Service**:
   ```bash
   python -m app.main
   ```
   *(Backend FastAPI aktif di `http://127.0.0.1:8000`).*
4. **Jalankan Frontend Web Dashboard (Dev Mode)**:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```
   *(Web Dashboard aktif di `http://localhost:5173`).*

#### Kredensial Default Sistem:
- **Administrator** (`Role ADMIN`): Username `admin` | Password `patroladmin2026`
- **Analis Intelijen** (`Role ANALYST`): Username `analyst` | Password `patrolanalyst2026`
- **Petugas Piket** (`Role OPERATOR`): Username `operator` | Password `patroloperator2026`

---

### Opsi B: Menggunakan Docker Compose (Mode Produksi Lengkap)

1. **Salin konfigurasi environment**:
   ```bash
   cp .env.example .env
   ```
2. **Lengkapi kredensial pada `.env`**:
   - `GEMINI_API_KEY`: API Key dari [Google AI Studio](https://aistudio.google.com/)
3. **Jalankan seluruh layanan**:
   ```bash
   docker-compose up -d --build
   ```
4. **Akses antarmuka terpadu**:
   - Web Dashboard: [http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)
   - Dokumentasi Swagger API: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Status Kesehatan Sistem: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🌐 Fitur Utama Web Dashboard Analitik

Web Dashboard dirancang dengan estetika **Cyber-Dark Console** (Glassmorphism, Dark Slate `#0b0f19`, aksen neon semantik HSL, dan tipografi modern):

1. **Antrean Validasi Terpusat (HITL Queue)**:
   - Menampilkan kartu tiket temuan baru beresolusi Full HD.
   - Ringkasan intelijen AI dimensi 5W+1H (*Who, What, Where, When, Why, How*).
   - Rekomendasi kategori, tingkat risiko, dan topik IPOLEKSOSBUDHANKAM.
   - Panel preseden RAG: Menampilkan hingga 5 kasus lama yang relevan sebagai bahan pertimbangan analis.
   - Tombol keputusan atomik: `[Setuju]`, `[Ubah Kategori/Risiko]`, dan `[Bukan Pelanggaran]` beserta kewajiban memilih kode alasan resmi.
2. **9 Grafik Visual Analitik Agregat**:
   - **Visual 1 (Tren Waktu)**: Dual-Line Chart membandingkan laporan masuk vs temuan terkonfirmasi per hari.
   - **Visual 2 (Per Platform)**: Bar Chart sebaran YouTube, TikTok, Instagram, X/Threads.
   - **Visual 3 (Per Kategori)**: Horizontal Bar volume HOAKS, SARA, Ujaran Kebencian, Penipuan Finansial, dll.
   - **Visual 4 (Distribusi Risiko)**: Donut Chart proporsi risiko SEDANG, TINGGI, dan RENDAH.
   - **Visual 5 (Topik IPOLEKSOSBUDHANKAM)**: Peringkat sebaran isu berdasarkan 8 bidang strategis nasional.
   - **Visual 6 (Aktor Target Publik)**: Peringkat entitas lembaga/tokoh publik sasaran narasi.
   - **Visual 7 (Media Asal Teratas)**: Peringkat media daring/kanal yang paling sering dicatut sebagai sumber.
   - **Visual 8 (Ketidaksepakatan Analis vs AI)**: Perbandingan jumlah putusan disetujui vs diubah oleh analis.
   - **Visual 9 (Progres Evaluasi Buta RAG)**: Monitoring metrik akurasi evaluasi buta (FR-13).
3. **Fitur Drill-Down Interaktif**:
   - Mengklik elemen grafik manapun langsung menyaring daftar tiket pada tabel secara *real-time*.
4. **Unduh Rekapitulasi Harian Dinas (.docx)**:
   - Menghasilkan dokumen resmi Microsoft Word (.docx) berstempel waktu dinas, tabel rekapitulasi 6-kolom, tangkapan layar ber-SHA-256, dan nilai *chain head* hash audit log hari bersangkutan.
5. **Ekspor CSV Aman (Anti-CSV Injection)**:
   - Mengekspor data tabular dengan *escaping* otomatis pada karakter formula (`=`, `+`, `-`, `@`).
6. **Banner Disclaimer Netralitas Permanen**:
   - Tersemat secara permanen: *"Label: frekuensi kemunculan topik, aktor, dan sumber tidak menunjukkan penetapan bersalah. Keputusan analis bukan penetapan hukum otomatis."*
7. **Panel Administrasi & Keamanan (Role ADMIN)**:
   - Kurasi entitas dan topik baru `LAINNYA`.
   - Tata kelola KB (penonaktifan logis `is_active = False`).
   - Verifikasi integritas rantai audit *hash-chain* terhadap nilai jangkar supervisor.
   - Halaman pemantauan kesehatan teknis sistem (10 indikator alarm dini).

---

## 📁 Struktur Direktori Proyek

```
cyber-patrol-assistant/
├── .env.example              # Template konfigurasi environment
├── Dockerfile                # Docker image (Python 3.11 + Playwright Chromium)
├── docker-compose.yml        # Orkestrasi 10 service modular terisolasi
├── requirements.txt          # Dependensi Python backend
├── PRD v3.1 - Asisten Patroli Siber (Field-Aligned Final).md # Spesifikasi Kebutuhan Final Lapangan D22
├── PRD v3 - Asisten Patroli Siber (RAG Terukur + Dashboard Analitik).md # Spesifikasi Lengkap Dosen & DFD
├── README.md                 # Dokumentasi panduan operasional sistem
├── tests/                    # Test suite otomatis (18 unit tests terverifikasi)
├── extension/                # Browser Extension (Chrome/Edge/Firefox Manifest V3)
│   ├── manifest.json         # Konfigurasi MV3 resmi
│   ├── popup.html            # Antarmuka popup 1-Click Capture
│   ├── popup.js              # Ekstraksi tab, rendered DOM, dan WebCrypto SHA-256
│   └── background.js         # Service worker & penanganan token terenkripsi
├── dashboard/                # Frontend Web Dashboard (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── pages/            # Halaman Overview, Queue Validasi, Kurasi, Admin Health
│   │   ├── components/       # DualLineChart, BarChart, KPICard, Table, FilterBar
│   │   ├── api/client.ts     # Client Axios + Secure Blob Exporter via Bearer Header
│   │   └── types/            # Definisi tipe TypeScript
│   └── dist/                 # Production build bundle
├── app/
│   ├── main.py               # Entry point FastAPI & database init
│   ├── config.py             # Pydantic BaseSettings konfigurasi aplikasi
│   ├── database.py           # Engine basis data adaptif (PostgreSQL 16 / Auto-Fallback SQLite)
│   ├── models/               # Model ORM SQLAlchemy 11 Tabel Relasional Fisik
│   │   ├── report.py         # Account, Content, Report (7 status, raw AI fields)
│   │   ├── evidence.py       # Evidence (SHA-256 64-hex, storage_path, pHash)
│   │   ├── knowledge.py      # KnowledgeEntry (Versioning berjejak is_active & deactivated_at)
│   │   ├── entities.py       # Entity, EntityAlias, dan ReportActor
│   │   ├── user.py           # User (Argon2id + 2FA TOTP: OPERATOR, ANALYST, ADMIN)
│   │   └── audit.py          # AuditLog (Rantai audit hash-chain prev_hash & row_hash)
│   ├── services/             # Domain Layanan Bisnis, Forensik & AI
│   │   ├── rag_service.py    # RAG Engine Fail-Open murni (tanpa vektor palsu, threshold 0.75)
│   │   ├── ai_service.py     # Gemini Vision Multimodal & ekstraksi intelijen 5W+1H
│   │   ├── entity_service.py # Resolusi alias, exact matching, & merger entitas
│   │   ├── crypto_service.py # Verifikasi SHA-256 & audit hash-chain
│   │   ├── report_service.py # Generator rekapitulasi dinas DOCX berstempel dinas & chain head
│   │   └── seeder.py         # Inisialisasi data simulasi operasional standar
│   ├── api/
│   │   ├── v1/               # Endpoint REST API v1 (Intake, Dashboard, Admin, Kurasi)
│   │   └── dashboard/        # Endpoint Autentikasi JWT & Radar Trending
│   └── workers/
│       └── tasks.py          # Celery background workers (Scraping, RAG Ingestion, Verification)
└── storage/
    ├── evidences/            # Direktori penyimpanan bukti berstatus read-only (0444)
    └── reports/              # Direktori arsip dokumen laporan dinas DOCX
```

---

## 🧪 Pengujian Otomatis & Kesiapan Tugas Akhir

### 1. Test Suite Otomatis Backend (18 Pengujian Lulus)
```bash
python -m unittest discover -s tests
```
*Hasil Verifikasi:*
```text
Ran 18 tests in 0.859s
OK
```
*Cakupan Pengujian:*
- Integritas skema basis data dan relasi 11 tabel relasional resmi.
- Verifikasi sidik jari kriptografi SHA-256 dan perlindungan *Chain of Custody*.
- Perilaku *Fail-Open* modul RAG saat model embedding offline (bebas vektor palsu).
- Normalisasi entitas, resolusi alias eksak, dan penggabungan entitas (*Merge*).
- Validasi kewajiban kode alasan pada status `MODIFIED` dan `REJECTED`.
- Netralisasi `final_risk` menjadi `NULL` pada status `REJECTED`.
- Endpoint REST API autentikasi, antrean dashboard, analitik, dan kurasi admin.

### 2. Frontend Production Build
```bash
cd dashboard && npm run build
```
*Hasil Verifikasi:*
```text
✓ 1571 modules transformed.
dist/index.html                   1.18 kB │ gzip:  0.72 kB
dist/assets/index-CWGyHX2_.css   31.46 kB │ gzip:  6.44 kB
dist/assets/index-Cqlw0vKn.js   351.36 kB │ gzip: 99.43 kB
✓ built in 4.93s
```

### 3. Kesiapan Menuju Tugas Akhir (TA)
Arsitektur PRD v3.1 sengaja dirancang agar pekerjaan selama masa magang dapat langsung dilanjutkan menjadi Tugas Akhir tanpa perombakan:
- **Pilar RPL / Forensik Digital**: Akuisisi bukti web ber-SHA-256 seketika di peramban klien, verifikasi worker, dan rantai audit *hash-chain* dengan jangkar eksternal.
- **Pilar Kecerdasan Buatan (AI/RAG)**: Evaluasi buta multimodal RAG untuk triase konten dinamis dengan pengujian hipotesis pra-registrasi teruji (FR-13).
- **Pilar Data / Intelijen Sosial**: Pemantauan isu strategis 8 Bidang IPOLEKSOSBUDHANKAM, resolusi entitas kanonikal, dan *content clustering*.

---

**Asisten Patroli Siber v3.1 (Field-Aligned Final)** | *Badan Siber dan Sandi Negara (BSSN) — Tim Dalinfo, Sub Tim Analisis Intelijen Siber.*
