# 🛡️ Asisten Patroli Siber & Social Intelligence v3.0
### *(Enterprise Omnichannel Edition: Telegram, Browser Extension & WhatsApp)*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Extension](https://img.shields.io/badge/Chrome_&_Edge-Manifest_V3-4285F4?style=flat&logo=googlechrome&logoColor=white)](extension/)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Gateway_Ready-25D366?style=flat&logo=whatsapp&logoColor=white)](app/api/v1/assistant.py)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-Multimodal_+_Embeddings-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-Headless_Full_HD-2EAD33?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Status](https://img.shields.io/badge/Status-Production_Ready-10b981?style=flat)]()

> **Sistem Cerdas Operasional Piket Patroli Siber & Dasbor Analitik Social Intelligence** — Platform terpadu analisis ancaman konten digital, penegakan integritas bukti forensik digital, pemantauan isu viral, dan triase cerdas berbasis AI Multimodal dengan arsitektur modular **Omnichannel Assistant**.
> 
> Didukung oleh **Omnichannel Client Gateway** (Bot Telegram, Ekstensi Peramban Chrome/Edge Manifest V3, WhatsApp Business Gateway, serta Web Command Console), **Dual-Engine Database** (PostgreSQL 16 + pgvector dan Auto-Fallback SQLite), **RAG Preseden Fail-Open Murni**, Analisis **5W+1H Multimodal Gemini**, serta Validasi **Human-in-the-Loop** berjejak.

---

## 📑 Daftar Isi

- [Arsitektur Sistem Omnichannel (v3.0)](#-arsitektur-sistem-omnichannel-v30)
- [Kanal Antarmuka Asisten (Omnichannel Gateway)](#-kanal-antarmuka-asisten-omnichannel-gateway)
- [Matriks Penyelarasan Kebutuhan Proposal](#-matriks-penyelarasan-kebutuhan-proposal)
- [Skema Basis Data 11 Tabel Fisik Resmi](#-skema-basis-data-11-tabel-fisik-resmi)
- [Panduan Pemasangan Ekstensi Browser Chrome/Edge](#-panduan-pemasangan-ekstensi-browser-chromeedge)
- [Panduan Cepat Menjalankan Sistem](#-panduan-cepat-menjalankan-sistem)
- [Panduan Operasional Telegram Bot & WhatsApp](#-panduan-operasional-telegram-bot--whatsapp)
- [Fitur Utama Web Dashboard Analitik](#-fitur-utama-web-dashboard-analitik)
- [Struktur Direktori Proyek](#-struktur-direktori-proyek)

---

## 🏗️ Arsitektur Sistem Omnichannel (v3.0)

Sistem dirancang dengan arsitektur **Decoupled API-First**, di mana antarmuka pengguna tidak terkunci pada satu aplikasi saja, melainkan modular ke berbagai kanal:

```
[ KANAL ASISTEN & CLIENT GATEWAY ]
  ├── 1. Telegram Bot (Operasional Lapangan & Approval Inline)
  ├── 2. Chrome & Edge Browser Extension (1-Click Capture saat Patroli Web)
  ├── 3. WhatsApp Business Gateway (Inbound Webhook & Mobile Chat)
  └── 4. Web Command Console (Intake Langsung & Verifikasi Data)
                      │
                      ▼
         [ FastAPI Central Service ]
   - /api/v1/assistant/intake (Unified Intake)
   - /api/v1/assistant/channels (Monitoring Kanal)
   - /api/v1/assistant/whatsapp/webhook (WA Bridge)
   - /api/v1/dashboard & /admin (Analitik & Kurasi)
                      │
                      ▼
               [ Redis Queue ]
                      │
                      ▼
              [ Celery Worker ]
                      │
     ┌────────────────┴────────────────┐
     ▼                                 ▼
[ Playwright Full HD Scraper ]   [ RAG Preseden & Vector Search ]
- Resolusi 1920x1080 Headless    - Gemini text-embedding-004 (768d)
- Validasi Anti-Blank (>20 KB)   - Cosine Similarity >= 0.75 (top_k=5)
- Auto-Retry 1x jika gagal       - Filter: is_active == True
- Fallback ke MANUAL_FALLBACK    - Fail-Open: Konteks Kosong + AuditLog
- Hash SHA-256 Bukti Visual      - Bebas Vektor Palsu/Pseudo-Random
     │                                 │
     └────────────────┬────────────────┘
                      ▼
          [ Multimodal Gemini AI ]
          - Multi-Model Failover (Flash Latest -> 3.5 -> 2.5)
          - Ekstraksi Intelijen 5W+1H (Who, What, Where, When, Why, How)
          - Rekomendasi: Kategori, Risiko, Topik, Aktor, Sumber
                      │
                      ▼
        [ Basis Data Dual-Engine ]
        - Mode Prod : PostgreSQL 16 + pgvector (HNSW Index)
        - Mode Lokal: SQLite Mandiri (storage/patrol.db)
        - 11 Tabel Fisik Resmi (Termasuk report_actors)
                      │
                      ▼
   [ Notifikasi & Rekapitulasi Multikanal ]
   - Sinkronisasi instan ke Web Dashboard
   - Kartu Analis Telegram (Tombol Validasi HITL)
   - Respon Otomatis WhatsApp Terformat
   - Generator Rekapitulasi Dinas Harian DOCX
```
       - 7 Status Tiket: PENDING_ANALYSIS s.d. VALIDATED/MODIFIED/REJECTED
                      │
                      ▼
       [ Feedback Loop & Versioning Berjejak ]
       - Deaktivasi Entri KB Lama (is_active=False, deactivated_at=NOW())
       - Buat Entri KB Baru (is_active=True, No Hard-Delete)
       - Normalisasi Entitas, Resolusi Alias & Fuzzy Match (>=0.85)
```

---

## 📋 Matriks Penyelarasan Kebutuhan Sistem

Sistem telah diuji dan memenuhi seluruh butir spesifikasi standar operasional patroli siber:

### Kebutuhan Fungsional (FR-01 s.d. FR-12)
| ID | Nama Fitur | Spesifikasi Terimplementasi | Status |
|:---|:---|:---|:---:|
| **FR-01** | Intake Tautan & Media | Mendukung intake via Telegram untuk URL (YouTube, TikTok, Instagram) dan unggahan foto/screenshot manual. | ✅ 100% |
| **FR-02** | Scraper Headless & Fallback | Playwright Full HD (1920x1080) dengan validasi ukuran berkas **> 20 KB** dan 1x retry. Jika gagal/login-wall, status beralih ke `MANUAL_FALLBACK` dan bot meminta foto manual. | ✅ 100% |
| **FR-03** | Rantai Bukti Forensik | Kalkulasi nilai hash kriptografi SHA-256 tepat 64 karakter heksadesimal seketika pada biner gambar di tabel `evidences`. | ✅ 100% |
| **FR-04** | RAG Preseden Fail-Open | Pencarian semantik Gemini `text-embedding-004` (768 dimensi) dengan threshold $\ge 0.75$ dan $k=5$ pada entri `is_active=True`. RAG Fail-Open murni (tanpa vektor palsu) mencatat `RAG_FALLBACK_EMPTY` jika offline. | ✅ 100% |
| **FR-05** | Triase Multimodal 5W+1H | AI Gemini mengekstrak Who, What, Where, When, Why, How, rekomendasi kategori, tingkat risiko, confidence score, raw entities, dan sitasi preseden. | ✅ 100% |
| **FR-06** | HITL & Siklus Hidup Tiket | 7 Status siklus tiket: `PENDING_ANALYSIS`, `WAITING_VALIDATION`, `MANUAL_FALLBACK`, `FAILED`, `VALIDATED`, `MODIFIED`, `REJECTED`. Catatan analis wajib pada `MODIFIED` & `REJECTED`; risiko dinetralkan pada `REJECTED`. | ✅ 100% |
| **FR-07** | Generator Rekapitulasi DOCX | Pembuatan berkas dinas Microsoft Word (.docx) berstempel disclaimer simulasi prototipe yang hanya menyaring tiket final `VALIDATED` dan `MODIFIED`. | ✅ 100% |
| **FR-08** | RBAC Bot Telegram | Whitelist 3 peran pada tabel `patrol_users`: `OPERATOR` (intake & `/status`), `ANALYST` (validasi kartu & `/rekap_harian`), dan `ADMIN` (kelola `/whitelist`). | ✅ 100% |
| **FR-09** | Tata Kelola Entitas Kanonikal | Ekstraksi Topik, Aktor Target, dan Sumber. Resolusi alias eksak dan fuzzy Levenshtein ($\ge 0.85$), relasi aktor via `report_actors`, serta fitur Admin *Entity Merging*. | ✅ 100% |
| **FR-10** | Versioning Berjejak KB | Pembaruan keputusan menerapkan soft-deactivation (`is_active=False`, `deactivated_at=NOW()`) tanpa hard-delete, menjamin maksimal 1 entri aktif per `report_id`. | ✅ 100% |
| **FR-11** | Web Dashboard Cyber-Dark | Bar Filter Utama, 4 Kartu KPI Ringkasan, 8 Grafik Visual Wajib dengan fitur drill-down interaktif, Banner Disclaimer Netralitas permanen, dan Tab 5W+1H/Trending. | ✅ 100% |
| **FR-12** | Otorisasi RBAC & Ekspor Aman | Pemisahan hak akses Dashboard (`USER` read-only vs `ADMIN` full control) dan ekspor CSV aman via Bearer header Blob request yang tercatat di `audit_logs`. | ✅ 100% |

### Kebutuhan Non-Fungsional (NFR-01 s.d. NFR-07)
- **NFR-01 (Performa)**: Waktu respons pemrosesan intake hingga rekomendasi awal AI tersedia $< 30$ detik.
- **NFR-02 (Ketersediaan & Dual-Engine)**: Mendukung PostgreSQL 16 pgvector (Docker/Prod) dan Auto-Fallback SQLite lokal; pipeline kebal crash jika RAG offline.
- **NFR-03 (Integritas Bukti)**: Hash SHA-256 64-karakter tersimpan permanen dan seluruh mutasi tercatat di tabel `audit_logs`.
- **NFR-04 (Validitas Forensik Semantik)**: Bebas representasi vektor palsu; kegagalan embedding wajib menghasilkan konteks kosong ter-audit.
- **NFR-05 (Keamanan Akses)**: Hash sandi Bcrypt, JWT Bearer Token (tanpa JWT pada query string), dan Whitelist Telegram ID.
- **NFR-06 (Netralitas Hukum)**: Banner disclaimer netralitas permanen pada antarmuka visual grafik dan dokumen ekspor.
- **NFR-07 (Immutable History KB)**: Versioning berjejak tanpa operasi `DELETE` fisik dengan partial unique index di PostgreSQL dan layer validasi di SQLite.

---

## 🗄️ Skema Basis Data 11 Tabel Fisik Resmi

Sistem mengimplementasikan tepat **11 tabel fisik** berelasi sesuai ERD Proposal:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ dashboard_users │       │  patrol_users   │       │   audit_logs    │
└─────────────────┘       └────────┬────────┘       └─────────────────┘
                                   │ (reporter/validator)
┌─────────────────┐       ┌────────▼────────┐       ┌─────────────────┐
│    accounts     │◄──────┤     reports     ├──────►│    evidences    │
└────────┬────────┘       └─┬─────────────┬─┘       │ (SHA-256 64hex) │
         │ (1:N)            │             │         └─────────────────┘
┌────────▼────────┐         │ (1:N)       │ (1:N)
│    contents     │◄────────┘             ▼
└─────────────────┘              ┌──────────────────┐
                                 │knowledge_entries │ (NFR-07 Versioning)
┌─────────────────┐              └──────────────────┘
│ trending_topics │
└─────────────────┘
                                 ┌──────────────────┐
                                 │     entities     │ (TOPIC, ACTOR, SOURCE)
                                 └──┬────────────┬──┘
                                    │ (1:N)      │ (N:M via report_actors)
                         ┌──────────▼─────┐    ┌─▼──────────────┐
                         │ entity_aliases │    │ report_actors  │ (Tabel Ke-11)
                         └────────────────┘    └────────────────┘
```

1. **`dashboard_users`**: Kredensial akun Web Dashboard (Bcrypt hash, role `USER` atau `ADMIN`).
2. **`patrol_users`**: Whitelist Telegram bot (role `OPERATOR`, `ANALYST`, atau `ADMIN`).
3. **`accounts`**: Profil akun media sosial sumber konten (termasuk kolom `account_created_at`).
4. **`contents`**: Metadata konten patroli (`canonical_url` nullable, metadata atribut JSONB).
5. **`evidences`**: Bukti tangkapan layar digital (validasi `file_hash_sha256` tepat 64 hex, `storage_path`, `source_type`).
6. **`reports`**: Siklus hidup tiket patroli (7 status, raw AI fields `ai_output` JSONB, final label & risk, `analyst_notes`).
7. **`entities`**: Katalog entitas kanonikal (`TOPIC`, `ACTOR`, `SOURCE` dengan status `PENDING_REVIEW`, `APPROVED`, `MERGED`).
8. **`entity_aliases`**: Kamus varian penulisan, singkatan, dan alias entitas.
9. **`report_actors`** *(Tabel Ke-11)*: Relasi many-to-many laporan dengan aktor target (`role = 'TARGET'`).
10. **`knowledge_entries`**: Basis pengetahuan preseden RAG berjejak (`is_active`, `deactivated_at`, Vector 768-D, partial unique index).
11. **`audit_logs`**: Rekam jejak forensik immutable mencatat seluruh aktivitas sistem dan fallback.

---

## 🚀 Panduan Cepat Menjalankan Sistem

### Opsi A: Menggunakan Docker Compose (Mode Produksi Lengkap)

1. **Salin konfigurasi environment**:
   ```bash
   cp .env.example .env
   ```
2. **Lengkapi kredensial pada `.env`**:
   - `TELEGRAM_BOT_TOKEN`: Token bot dari [@BotFather](https://t.me/BotFather)
   - `GEMINI_API_KEY`: API Key dari [Google AI Studio](https://aistudio.google.com/)
3. **Jalankan seluruh layanan**:
   ```bash
   docker-compose up -d --build
   ```
4. **Akses antarmuka**:
   - Web Dashboard : [http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)
   - Dokumentasi Swagger API : [http://localhost:8000/docs](http://localhost:8000/docs)
   - Endpoint Health Check : [http://localhost:8000/health](http://localhost:8000/health)

---

### Opsi B: Pengujian Lokal Mandiri (Auto-Fallback SQLite)

Sistem dirancang cerdas untuk berjalan secara mandiri di lingkungan Windows/macOS/Linux tanpa memerlukan PostgreSQL maupun Redis eksternal:

1. **Install dependensi Python & Browser Playwright**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **Inisialisasi Database & Seeding 10 Data Uji Proposal**:
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```
   *(Secara otomatis membuat basis data lokal `storage/patrol.db` dan mengisi 10 data simulasi standar Proposal).*
3. **Jalankan Backend Server & Bot Telegram**:
   ```bash
   python -m app.main
   ```
   *(Backend FastAPI dan Bot berjalan di `http://127.0.0.1:8000`).*
4. **Jalankan Frontend Web Dashboard (Dev Mode)**:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```
   *(Akses dashboard di `http://localhost:5173`).*

#### Kredensial Default Web Dashboard:
- **Administrator** (`Role ADMIN`): Username `admin` | Password `patroladmin2026`
- **Analis / Pengguna** (`Role USER`): Username `analyst` | Password `patrolanalyst2026`

---

## 🤖 Panduan Operasional Telegram Bot

Akses bot dilindungi Whitelist tabel `patrol_users` dengan 3 tingkatan peran:

| Peran | Hak Akses & Kemampuan |
|:---|:---|
| **`OPERATOR`** | Mengirimkan tautan URL sosmed atau foto langsung, memicu triase AI, mengecek `/status`. |
| **`ANALYST`** | Seluruh hak Operator + Menekan tombol validasi `[SETUJU]`, `[UBAH]`, `[BUKAN PELANGGARAN]` + Mengunduh `/rekap_harian`. |
| **`ADMIN`** | Seluruh hak Analyst + Mengelola whitelist pengguna bot secara interaktif via `/whitelist`. |

### Daftar Perintah & Interaksi

| Perintah / Interaksi | Contoh Aksi | Keterangan Operasional |
|---|---|---|
| `/start` | `/start` | Menampilkan pesan sambutan, status whitelist, peran Anda, dan petunjuk operasional. |
| **Kirim Tautan URL** | `https://instagram.com/p/...` | Scraper Playwright mengambil Full HD screenshot (>20 KB), hash SHA-256, retrieval RAG, triase 5W+1H, dan menerbitkan Kartu Analis. |
| **Kirim Foto Langsung** | *(Unggah screenshot ponsel)* | Solusi langsung jika target terhalang login-wall/firewall kantor. Dapat disertai caption teks analisis awal. |
| **Fallback Otomatis** | *(Otomatis oleh sistem)* | Jika scraper gagal/screenshot $\le 20\text{ KB}$ setelah 1x retry, status menjadi `MANUAL_FALLBACK` dan bot meminta unggah foto manual. |
| **Validasi `[SETUJU]`** | Klik tombol hijau | Menyetujui rekomendasi AI (status `VALIDATED`), memperbarui preseden aktif pada Knowledge Base. |
| **Validasi `[UBAH]`** | Klik tombol kuning | Analis **wajib menginput catatan koreksi** (status `MODIFIED`). Catatan disimpan sebagai nalar preseden RAG. |
| **Validasi `[BUKAN PELANGGARAN]`** | Klik tombol merah | Analis **wajib menginput justifikasi** (status `REJECTED`). Tingkat risiko dinetralkan menjadi NULL/None. |
| `/status` | `/status` | Menampilkan rekapitulasi status tiket aktif berdasarkan 7 siklus status proposal. |
| `/rekap_harian` | `/rekap_harian` | Mengunduh dokumen `.docx` resmi 6-kolom ber-KOP dinas dan stempel disclaimer simulasi (hanya tiket `VALIDATED` & `MODIFIED`). |
| `/whitelist` | `/whitelist add 123456 OPERATOR` | *(Khusus Admin)* Mengelola daftar ID pengguna Telegram yang berwenang mengakses bot. |

---

## 🌐 Fitur Utama Web Dashboard Analitik

Web Dashboard dirancang dengan estetika **Cyber-Dark Console** (Glassmorphism, Dark Slate `#0b0f19`, dan aksen neon semantik HSL):

1. **Bar Filter Utama (Sticky Header)**:
   - Filter Rentang Tanggal (7 Hari, 14 Hari, 30 Hari, 90 Hari, Semua).
   - Filter Platform (`Instagram`, `YouTube`, `TikTok`).
   - Filter Kategori (`HOAKS`, `DI_LUAR_KONTEKS`, `UJARAN_KEBENCIAN`, `PROVOKASI_SARA`).
   - Filter Risiko (`TINGGI`, `SEDANG`, `RENDAH`).
   - Tombol **Ekspor CSV Aman** (Menggunakan request `fetch` dengan Authorization Bearer header, diunduh sebagai Blob, dan dicatat di `audit_logs`).
2. **4 Kartu KPI Ringkasan (Sesuai Gambar L3.18 Proposal)**:
   - **Total Laporan**: Seluruh temuan yang masuk ke sistem.
   - **Temuan Tervalidasi**: Jumlah temuan berstatus `VALIDATED` + `MODIFIED`.
   - **Koreksi Analis**: Jumlah temuan berstatus `MODIFIED`.
   - **Bukan Pelanggaran**: Jumlah temuan berstatus `REJECTED` (False Positive).
   - *Interaktivitas*: Mengklik kartu KPI langsung memfilter tabel tiket di bawahnya.
3. **8 Grafik Visual Wajib (Berdasarkan Putusan Final Analis)**:
   - **Visual 1 (Tren Waktu)**: Dual-Line Chart membandingkan garis `Laporan Masuk` vs `Temuan Tervalidasi` per hari.
   - **Visual 2 (Per Platform)**: Vertical Bar Chart perbandingan jumlah temuan pada Instagram, YouTube, dan TikTok.
   - **Visual 3 (Per Kategori)**: Horizontal Bar Chart perbandingan volume `HOAKS`, `DI_LUAR_KONTEKS`, `UJARAN_KEBENCIAN`, `PROVOKASI_SARA`.
   - **Visual 4 (Distribusi Risiko)**: Donut Chart persentase tingkat risiko `SEDANG`, `TINGGI`, dan `RENDAH`.
   - **Visual 5 (Topik Teratas)**: Horizontal Bar List peringkat entitas kanonikal bertipe `TOPIC`.
   - **Visual 6 (Aktor Target Teratas)**: Horizontal Bar List peringkat entitas kanonikal bertipe `ACTOR` (dari relasi `report_actors`).
   - **Visual 7 (Sumber Konten Teratas)**: Horizontal Bar List peringkat entitas kanonikal bertipe `SOURCE`.
   - **Visual 8 (Kesepakatan AI vs Analis)**: Vertical Bar Chart perbandingan jumlah putusan `VALIDATED`, `MODIFIED`, dan `REJECTED`.
4. **Fitur Drill-Down Interaktif**:
   - Mengklik elemen batang grafik, irisan donut, atau baris entitas pada visual manapun langsung menyaring daftar tiket pada tabel di bawahnya secara *real-time*.
5. **Banner Disclaimer Netralitas Permanen (NFR-06)**:
   - Tersemat secara permanen di bawah area visualisasi:
     > *"Label: frekuensi kemunculan topik, aktor, dan sumber tidak menunjukkan kesalahan pihak mana pun. Status tiket dan keputusan analis bukan penetapan hukum otomatis."*
6. **Panel Kurasi & Administrasi Eksklusif (`Role ADMIN`)**:
   - Kurasi entitas `PENDING_REVIEW`, pendaftaran alias baru, dan penggabungan entitas duplikat (*Entity Merging*).
   - Penonaktifan entri Knowledge Base RAG (`is_active = False`) secara non-destruktif.
   - Manajemen pengguna Web Dashboard dan Whitelist Telegram.
   - Peninjauan jejak audit forensik kronologis (`audit_logs`).

---

## 📁 Struktur Direktori Proyek

```
cyber-patrol-assistant/
├── .env.example              # Template konfigurasi environment lengkap
├── Dockerfile                # Docker image (Python 3.11 + Playwright Chromium)
├── docker-compose.yml        # Orkestrasi multi-container (PostgreSQL pgvector, Redis, App, Worker)
├── requirements.txt          # Dependensi Python backend
├── PRD v3 - Asisten Patroli Siber (RAG Terukur + Dashboard Analitik).md # Spesifikasi Kebutuhan Produk & DFD Level 0-2 (v3.0)
├── README.md                 # Dokumentasi resmi panduan sistem (File ini)
├── tests/                    # Test suite otomatis (18 unit tests terverifikasi)
├── dashboard/                # Frontend Web Dashboard (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── pages/            # Halaman Overview (L3.18), Trending/5W+1H, Curation, Dossier
│   │   ├── components/       # DualLineChart, VerticalBarChart, KPICard, Table, FilterBar
│   │   ├── api/client.ts     # Client Axios + Secure Blob Exporter via Bearer Header
│   │   └── types/            # Definisi tipe TypeScript
│   ├── dist/                 # Production build bundle
│   └── vite.config.ts        # Konfigurasi Vite dev server & proxy
├── app/
│   ├── main.py               # Entry point FastAPI, bot background runner, & database init
│   ├── config.py             # Pydantic BaseSettings konfigurasi aplikasi
│   ├── database.py           # Engine basis data adaptif (PostgreSQL 16 / Auto-Fallback SQLite)
│   ├── models/               # Model ORM SQLAlchemy 11 Tabel Fisik Resmi
│   │   ├── report.py         # Account, Content, Report (7 status, raw AI fields)
│   │   ├── evidence.py       # Evidence (SHA-256 64-hex, storage_path, source_type)
│   │   ├── knowledge.py      # KnowledgeEntry (Versioning berjejak is_active & deactivated_at)
│   │   ├── entities.py       # Entity, EntityAlias, dan ReportActor (Tabel Ke-11)
│   │   ├── user.py           # DashboardUser (Bcrypt) dan PatrolUser (Telegram Whitelist)
│   │   └── audit.py          # AuditLog (Rekam jejak forensik immutable)
│   ├── services/             # Domain Layanan Bisnis & AI
│   │   ├── rag_service.py    # RAG Engine Fail-Open murni (tanpa vektor palsu, threshold 0.75)
│   │   ├── ai_service.py     # Gemini Vision Multimodal & ekstraksi intelijen 5W+1H
│   │   ├── entity_service.py # Resolusi alias, fuzzy match Levenshtein, & merger entitas
│   │   ├── crypto_service.py # Penghitungan sidik jari kriptografi SHA-256
│   │   ├── report_service.py # Generator rekapitulasi harian DOCX berstempel dinas
│   │   ├── seeder.py         # Inisialisasi 10 data simulasi operasional standar
│   │   └── scraper/          # Scraper Playwright Full HD (>20 KB check & 1x retry)
│   ├── api/
│   │   ├── v1/               # Endpoint REST API v1 (Dashboard Summary, Admin, Kurasi)
│   │   └── dashboard/        # Endpoint Autentikasi JWT & Radar Trending
│   ├── bot/
│   │   └── handlers.py       # Logika Telegram Bot (3 Role Whitelist, Kartu Analis, /whitelist)
│   └── workers/
│       └── tasks.py          # Celery background workers (Scraping, RAG Ingestion)
└── storage/
    ├── evidences/            # Direktori penyimpanan tangkapan layar berstempel SHA-256
    └── reports/              # Direktori arsip dokumen laporan dinas DOCX
```

---

## 🧪 Pengujian Otomatis & Validasi Artefak

Seluruh fitur telah diverifikasi secara ketat melalui test suite otomatis:

### 1. Backend Unit Test Suite (18 Pengujian)
```bash
python -m unittest discover -s tests
```
*Output:*
```text
Ran 18 tests in 0.692s
OK
```
*Cakupan:*
- Inisialisasi basis data dan relasi 11 tabel fisik.
- Pengujian Chain of Custody hash SHA-256.
- RAG Fail-Open behavior saat model embedding offline (bebas vektor palsu).
- Normalisasi entitas, resolusi alias eksak, dan penggabungan entitas (*Merge*).
- Validasi kewajiban `analyst_notes` pada status `MODIFIED` dan `REJECTED`.
- Netralisasi `final_risk` menjadi NULL pada status `REJECTED`.
- Endpoint REST API autentikasi, ringkasan analitik, dan kurasi admin.

### 2. Frontend Production Build
```bash
cd dashboard && npm run build
```
*Output:*
```text
✓ 1571 modules transformed.
dist/index.html                   1.18 kB │ gzip:  0.72 kB
dist/assets/index-CWGyHX2_.css   31.46 kB │ gzip:  6.44 kB
dist/assets/index-Cqlw0vKn.js   351.36 kB │ gzip: 99.43 kB
✓ built in 4.93s
```

---

## ⚖️ Keamanan & Integritas Forensik

- **Jejak Bukti Digital (Chain of Custody)**: Setiap tangkapan layar diverifikasi seketika dengan algoritma SHA-256 tepat 64 karakter heksadesimal, dicatat ke basis data, dan dicantumkan pada berkas rekapitulasi dinas resmi.
- **Fail-Open Resilience**: Kegagalan subsistem eksternal (kuota API embedding Gemini habis atau kendala jaringan) tidak menghentikan intake patroli siber. Sistem mencatat insiden ke `audit_logs` dan tetap melanjutkan proses triase.
- **Prinsip Netralitas Hukum**: Sistem memposisikan AI sebagai asisten rekomendasi (*Human-in-the-Loop*). Seluruh keputusan penetapan kategori dan risiko merupakan wewenang mutlak analis manusia, didukung oleh banner disclaimer netralitas permanen.
- **Perlindungan Data & Token**: Pertukaran berkas ekspor dan manipulasi basis data dilakukan melalui header `Authorization: Bearer <token>` tanpa mengekspos token pada URL query string.

---

**Asisten Patroli Siber v3.0** | *Subdirektorat Operasi Siber / Tim Tanggap Insiden Keamanan Siber (CSIRT / SOC).*
