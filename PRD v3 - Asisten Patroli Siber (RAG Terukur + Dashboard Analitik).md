# PRD v3.1 — DRAF FINAL
## Asisten Patroli Siber
### Browser Extension + Multimodal RAG + Dashboard Analitik, dengan Akuisisi Bukti Web Ber-SHA-256

---

**Status Dokumen:** DRAF FINAL untuk submission ke pembimbing lapangan (Bang Zazal), dosen pembimbing, dan Pak Giri.  
**Versi:** 3.1 (Field-Aligned Final)  
**Tanggal:** 27 Oktober 2026  
**Lokus Penugasan:** Badan Siber dan Sandi Negara (BSSN) — Tim Pengendalian Operasi Informasi (Dalinfo), Sub Tim Analisis Intelijen Siber  
**Basis Dokumen:** PRD v3 (review dosen pembimbing) + Notulensi Rapat D22 Dalinfo + Arahan Teknis Bang Zazal + PRD v2 (usulan awal kelompok)  
**Prinsip Desain:** *Keep it simple*, terukur secara matematis, *fail-open* bertingkat, dapat dimatikan via saklar fitur (*feature flags*), tidak menghentikan triase operasional, dan siap untuk operasional jangka panjang dan pengembangan berkelanjutan.

---

## Riwayat Revisi

| Versi | Tanggal | Perubahan Utama |
|---|---|---|
| **v1.0** | Okt 2026 | Fondasi awal: Dual Intake, scraper Playwright headless, verifikasi SHA-256, HITL Telegram Bot, dan ekspor DOCX. |
| **v2.0** | Okt 2026 | Penambahan memori preseden RAG, web dashboard analitik, ekstraksi topik/aktor/sumber, serta form catatan analis. |
| **v3.0** | Okt 2026 | Penguatan sistemik menyeluruh: evaluasi buta RAG (FR-13), model ancaman keamanan (T1–T8), audit hash-chain, privasi *fail-closed*, fase rilis bertahap, dan 32 kriteria penerimaan (AC-01 s.d. AC-32). |
| **v3.1** | **27 Okt 2026** | **Field-Aligned Final (Kondisi Lapangan Riil D22 Dalinfo):**<br>• Pintu masuk utama beralih penuh dari Bot Telegram ke **Browser Extension** (Chrome/Edge/Firefox MV3).<br>• Antrean validasi dipusatkan di **Web Dashboard Console**.<br>• Hierarki peran disederhanakan menjadi **3 Role** (`OPERATOR`, `ANALYST`, `ADMIN`); role `VIEWER` ditunda pasca-MVP.<br>• Taksonomi topik diselaraskan dengan **8 Bidang IPOLEKSOSBUDHANKAM**.<br>• Strategi akuisisi bukti beralih ke **Client-First Capture** (tangkapan layar tab aktif Full HD + DOM render + hash SHA-256 dihitung di browser klien via WebCrypto).<br>• Penerapan **Adapter Pattern** untuk platform media sosial (YouTube, TikTok, Instagram) serta dukungan X/Threads berbasis DOM aktif.<br>• Pemisahan tegas batasan scope implementasi operasional versus rencana pengembangan lanjutan. |

---

## 0. Ringkasan Perubahan dari v3 ke v3.1

| Area | v3 (Dosen Pembimbing) | v3.1 (Final, Field-Aligned) | Rasional & Dasar Keputusan |
|---|---|---|---|
| **Pintu Masuk Utama** | Bot Telegram | **Browser Extension** (Chrome/Edge/Firefox MV3) | Arahan Bang Zazal: 100% personel patroli di ruangan bekerja di browser workstation; tidak semua memakai Telegram di PC dinas. |
| **Tempat Validasi HITL** | Kartu inline Telegram | **Antrean Validasi di Web Dashboard** | Satu pusat kendali terpadu; memudahkan komparasi bukti visual Full HD dan teks di layar monitor dinas. |
| **Perintah Status & Rekap** | `/status`, `/rekap_harian` via Telegram | **Menu Terpadu di Web Dashboard** | Konsisten dengan alur kerja berbasis web workstation dinas. |
| **Identitas Akun** | `patrol_users` + `telegram_id` nullable | **`users`** tanpa dependensi `telegram_id` | Seluruh otentikasi menggunakan kredensial web/ekstensi terpusat (Argon2id + 2FA TOTP). |
| **Outbox Notifikasi** | Outbox Telegram API | **Dihapus**; notifikasi internal via dashboard | Mengeliminasi dependensi jaringan luar Telegram Bot API dan mengurangi *point of failure*. |
| **Hierarki Peran (Role)** | 4 Role (OPERATOR, ANALYST, ADMIN, VIEWER) | **3 Role** (OPERATOR, ANALYST, ADMIN) | Realistis diselesaikan oleh tim magang 3 orang; peran VIEWER ditunda ke rilis pasca-MVP. |
| **Akuisisi Bukti Visual** | Scraper Playwright server-side | **Client-First Capture** + Playwright fallback | Anti login-wall & IP-block media sosial; menangkap persis apa yang dirender di layar mata personel. |
| **Cakupan Platform** | 3 platform (YouTube, TikTok, IG) | **3 platform utama + Adapter Pattern** untuk X/Threads via active-tab capture | Menjawab kebutuhan operasional “semua platform” tanpa melanggar batasan stabilitas server. |
| **Taksonomi Topik** | Kategori pelanggaran saja | **Kategori pelanggaran + Topik Terkontrol IPOLEKSOSBUDHANKAM** | Menjawab langsung notulensi rapat D22 Tim Dalinfo BSSN. |
| **Evaluasi RAG (FR-13)** | Lengkap dengan evaluasi buta | **Dipertahankan penuh 100%** | Menjadi landasan pembuktian empiris keandalan AI sebelum diaktifkan penuh. |
| **Audit Hash-Chain** | Hash-chain + jangkar DOCX harian | **Dipertahankan penuh 100%** | Menjamin keabsahan rantai bukti digital (Chain of Custody) yang berkekuatan hukum. |
| **Fase Rilis** | 3 fase implementasi | **3 fase dengan scope terfokus** | Sangat terukur, bertahap, dan realistis diselesaikan dalam periode magang. |

> **Komponen yang Tidak Berubah dari v3:**  
> Kalkulasi SHA-256 seketika di titik capture, re-verifikasi hash di worker, OCR deterministik Tesseract, modul RAG terukur dengan evaluasi buta (FR-13), kode alasan terstruktur, deteksi duplikat (URL kanonikal, SHA-256, dan pHash), audit log ber-hash-chain dengan jangkar eksternal, perlindungan privasi *fail-closed*, target tingkat layanan (SLO), prosedur pencadangan dan uji pemulihan, model ancaman keamanan (T1–T8), 32 kriteria penerimaan (AC-01 s.d. AC-32), dan fase rilis bergerbang.

---

## 1. Product Requirement Document (PRD)

### 1.1 Ringkasan Eksekutif

Asisten Patroli Siber adalah sistem terintegrasi yang membantu personel piket patroli siber menangkap konten media sosial yang diduga bermasalah, mengamankan buktinya secara forensik digital, menganalisisnya dengan kecerdasan buatan multimodal sebagai **saran indikatif 5W+1H**, dan menyerahkan keputusan vonis kepada analis manusia (*Human-in-the-Loop*). 

Keputusan final analis disimpan sebagai **memori institusional** (*Retrieval-Augmented Generation* / RAG) untuk memperkaya konteks triase pada kasus-kasus berikutnya, dan seluruh hasil analisis disajikan secara agregat pada **Web Dashboard Analitik**.

Versi 3.1 menyelaraskan seluruh rancangan sistem dengan kondisi kerja riil di Sub Tim Analisis Intelijen Siber, Tim Dalinfo BSSN:
1. **Pintu Masuk Dialihkan ke Browser Extension**: Personel patroli bekerja aktif di peramban web workstation dinas; 1-klik ekstensi menangkap layar aktif, struktur DOM, metadata, dan nilai hash SHA-256 di sisi klien.
2. **Validasi Dipusatkan di Web Dashboard**: Analis memvalidasi temuan pada antrean tiket terpusat di konsol web workstation.
3. **Penyederhanaan Ruang Lingkup**: Memangkas kompleksitas non-esensial agar realistis diselesaikan oleh 3 mahasiswa magang dalam periode waktu yang tersedia, dengan arsitektur bersih yang siap diintegrasikan secara operasional berkelanjutan.

---

### 1.2 Masalah yang Diselesaikan (Pemetaan Notulensi D22 Dalinfo)

| No | Masalah Riil di Ruangan Dalinfo D22 | Solusi Teknis PRD v3.1 |
|---|---|---|
| 1 | **Tangkapan layar manual (PrintScreen/Snipping Tool) tidak memenuhi standar forensik.** | Ekstensi otomatis mengambil tangkapan layar Full HD + snapshot rendered DOM + metadata + kalkulasi nilai *hash* SHA-256 seketika di titik capture. |
| 2 | **Pencatatan temuan patroli tersebar di lembar kerja Excel lokal yang tidak seragam.** | Repositori basis data terpusat PostgreSQL 16 + formulir metadata baku otomatis via ekstensi peramban. |
| 3 | **Serah-terima temuan patroli ke analis lambat dan berbelit-belit.** | Alur terintegrasi satu pipa: Ekstensi → Antrean Validasi Web Dashboard → Keputusan Analis, tanpa perantara file Excel. |
| 4 | **Ketergantungan pada layanan pihak ketiga berbayar (Claude/ChatGPT manual).** | *AI Gateway* mandiri yang kompatibel dengan format standar OpenAI, mempermudah transisi ke model lokal di kemudian hari. |
| 5 | **Visualisasi data analitik terbatas dan sulit ditarik kesimpulan trennya.** | Web Dashboard menyajikan 9 grafik agregat: tren waktu, platform, kategori, risiko, topik IPOLEKSOSBUDHANKAM, aktor publik, dan media asal. |
| 6 | **Personel baru membutuhkan waktu adaptasi lama memahami konteks kasus.** | RAG sebagai memori institusional: preseden kasus lama yang relevan otomatis disajikan di antrean validasi sebagai bahan pertimbangan. |
| 7 | **Keabsahan bukti digital rentan disangkal dalam pembuktian hukum.** | Integritas bukti dijamin oleh rantai audit *hash-chain* (`prev_hash` & `row_hash`) serta jangkar eksternal di luar sistem. |
| 8 | **Konten yang sama sering dilaporkan berulang kali oleh personel berbeda.** | Deteksi duplikasi otomatis berbasis URL kanonikal, hash SHA-256, dan kemiripan perceptual hash (pHash). |
| 9 | **Tidak semua personel piket memiliki/menggunakan akun Telegram di PC dinas.** | Ekstensi peramban (Chrome/Edge/Firefox MV3) sebagai pintu masuk utama yang universal di seluruh PC workstation dinas. |
| 10 | **Proses kliping screenshot manual melelahkan saat volume konten tinggi.** | Satu kali klik pada ekstensi peramban (*1-Click Capture*) langsung mengekstrak dan mengarsipkan seluruh bukti secara deterministik. |

---

### 1.3 Tujuan dan Non-Goals

**Tujuan Pengembangan v3.1:**
1. Mengotomatisasi akuisisi bukti konten patroli siber dengan standar integritas forensik digital.
2. Menyediakan triase AI indikatif dengan memori institusional (RAG) yang **diuji secara buta (*blind evaluation*)** sebelum diaktifkan permanen.
3. Menyatukan seluruh alur kerja: patroli (ekstensi) → analisis/validasi (dashboard) → laporan dinas (DOCX) dalam satu ekosistem terpadu.
4. Menyediakan konsol dashboard analitik agregat yang aman, terisolasi, dan netral bagi analis dan pimpinan.
5. Menghasilkan rantai bukti digital (*Chain of Custody*) dan jejak audit yang akuntabel dan tidak dapat disangkal.
6. Membangun fondasi arsitektur modular yang stabil dan siap diekspansi tanpa perombakan struktur inti.

**Non-Goals (Eksplisit Dilarang / Tidak Dikerjakan pada v3.1):**
1. Vonis hukum atau tindakan *takedown* otomatis tanpa persetujuan analis manusia (*Human-in-the-Loop* mutlak).
2. Klaim sepihak "AI makin pintar" sebelum evaluasi buta (FR-13) membuktikan peningkatan akurasi secara statistik.
3. Melakukan *fine-tuning* model fondasi AI (LLM).
4. Notifikasi *real-time* lonjakan isu otomatis (menghindari alarm palsu pada volume data awal).
5. Scraping *server-side* untuk platform login-wall ketat seperti X (Twitter) atau Threads (cukup ditangani via *active-tab capture* ekstensi).
6. Menambah kategori pelanggaran baru di luar taksonomi yang telah dibekukan tanpa persetujuan tertulis pemangku kepentingan.
7. Analisis sentimen dan emosi otomatis tingkat lanjut (ditunda ke fase pengembangan lanjutan).
8. Proyeksi/risiko eskalasi konflik sosial berbasis machine learning (ditunda ke fase pengembangan lanjutan).
9. *Profiling* individu privat atau pemeringkatan aktor berdasarkan "asumsi kesalahan".
10. Integrasi SSO instansi, aplikasi mobile native, atau implementasi role VIEWER di tahap MVP.
11. Menggunakan nilai `skor_keyakinan` AI sebagai ambang batas pengambilan keputusan.
12. Integrasi API langsung ke sistem eksternal kementerian/lembaga lain (cukup via ekspor CSV dan berkas DOCX dinas).

---

### 1.4 Profil Pengguna dan Role

Sistem menggunakan satu tabel identitas tunggal (`users`) untuk otentikasi ekstensi dan dashboard. Sistem membatasi hak akses ke dalam **3 peran resmi**:

| Role | Hak Akses Ekstensi Peramban | Hak Akses Web Dashboard | Subjek Personel |
|---|---|---|---|
| **OPERATOR** | Mengirimkan laporan konten (URL + active-tab capture), melihat status tiket buatannya sendiri. | Tidak memiliki hak akses ke Web Dashboard. | Personel piket patroli siber lapangan. |
| **ANALYST** | Memiliki seluruh hak akses OPERATOR. | Mengakses antrean validasi tiket, dashboard analitik, filter drill-down, ekspor CSV, dan halaman Penilaian Kedua (*Second Review*). | Analis Intelijen Siber (Sub Tim Analisis Dalinfo). |
| **ADMIN** | Memiliki seluruh hak akses ANALYST. | Hak penuh: kelola akun pengguna, kurasi topik IPOLEKSOSBUDHANKAM, kurasi entitas, nonaktifkan KB, revisi keputusan, verifikasi audit hash-chain, dan pantau kesehatan sistem. | Pengelola teknis sistem (minimal 1 orang, wajib 2FA TOTP). |

> **Catatan Tata Kelola Akun:**
> - **Role VIEWER ditunda**: Pimpinan piket/supervisor menerima dokumen rekapitulasi harian DOCX dan ekspor CSV agregat. Penambahan role VIEWER dievaluasi setelah dashboard beroperasi stabil.
> - **ADMIN bukan atasan/penentu vonis**: ADMIN adalah pengelola teknis sistem. Setiap revisi keputusan analis oleh ADMIN wajib menyertakan kode alasan resmi dan tercatat di *audit log*.
> - **Pemisahan Akun**: Satu individu diperbolehkan memiliki lebih dari satu akun jika memiliki peran ganda, namun hak akses antar-peran tetap terpisah secara tegas.

---

### 1.5 Kebutuhan Fungsional (Functional Requirements)

#### FR-01 Dual Intake & Client-First Capture (Browser Extension)
- **FR-01.1 Pintu Masuk Utama**: Ekstensi peramban (Chrome, Edge, Firefox berstandar Manifest V3) menjadi antarmuka utama penangkapan konten saat personel melakukan patroli di media sosial.
- **FR-01.2 Client-First Capture**: Saat tombol ekstensi ditekan, ekstensi di browser klien secara instan mengeksekusi:
  1. Pengambilan tangkapan layar tab aktif (*visible tab screenshot*) beresolusi Full HD (1920x1080).
  2. Ekstraksi snapshot *rendered DOM* (struktur HTML halaman yang selesai di-render).
  3. Perekaman metadata halaman: URL aktif, judul halaman, dan stempel waktu klien.
  4. Perhitungan nilai hash SHA-256 (64 karakter heksadesimal) dari berkas gambar tangkapan layar di memori browser klien menggunakan WebCrypto API sebelum transmisi jaringan.
- **FR-01.3 Fallback Unggah Manual**: Jika ekstensi mengalami kendala pada workstation tertentu, antarmuka menyediakan modul unggah berkas gambar mandiri (maksimum 20 MB, verifikasi tipe MIME biner, serta proteksi batas piksel Pillow `MAX_IMAGE_PIXELS`).

#### FR-02 Platform Adapter & Scraper Fallback
- **FR-02.1 Adapter Pattern**: Sistem menggunakan pola desain *Adapter Pattern* untuk memproses struktur konten media sosial:
  - `YouTubeAdapter`: Ekstraksi ID video, channel uploader, judul, durasi, views, dan likes.
  - `TikTokAdapter`: Ekstraksi username, deskripsi audio, teks caption, dan likes.
  - `InstagramAdapter`: Ekstraksi shortcode reel/post, uploader, dan caption.
  - `GenericActiveTabAdapter`: Menangani konten web umum, X (Twitter), atau Threads berbasis DOM tab aktif yang ditangkap ekstensi tanpa bergantung pada scraping server-side.
- **FR-02.2 Scraper Fallback Server-Side**: Jika input hanya berupa string URL murni (tanpa payload tangkapan layar klien), worker server menjalankan engine Playwright headless terisolasi.
- **FR-02.3 Egress Allowlist & Batas Kepercayaan**: Scraper server hanya diizinkan menghubungi domain platform resmi. Seluruh koneksi ke alamat IP privat/intranet diblokir pada layer firewall (mitigasi SSRF T1). Seluruh hasil scraping server diperlakukan sebagai data tak tepercaya.

#### FR-03 Kriptografi Forensik & Chain of Custody
- **FR-03.1 Hash di Titik Capture**: Nilai hash SHA-256 dihitung seketika saat berkas bukti pertama kali tercipta di browser klien (atau saat pertama kali ditulis ke disk oleh worker).
- **FR-03.2 Verifikasi Worker**: Worker backend memverifikasi ulang biner gambar terhadap nilai hash yang dikirimkan oleh klien. Jika terjadi ketidakcocokan nilai hash, tiket langsung berstatus `FAILED` dan insiden dicatat sebagai `EVIDENCE_HASH_MISMATCH` di *audit log*.
- **FR-03.3 Manifest Bukti & Immutability**: Metadata bukti dicatat di tabel `evidences` dan berkas biner disimpan di direktori `storage/evidences/` dengan status *read-only* (dilarang ditimpa atau dimodifikasi).

#### FR-04 Triase AI Multimodal 5W+1H & AI Gateway
- **FR-04.1 Skema Output Terstruktur**: Model AI mengembalikan respons JSON valid berbasis skema Pydantic `AIPatrolAnalysis`:
  - `status_keamanan`: `AMAN` atau `POTENSI_BAHAYA`.
  - `kategori_utama`: `HOAKS`, `UJARAN_KEBENCIAN`, `PROVOKASI_SARA`, `PENIPUAN_FINANSIAL`, `DI_LUAR_KONTEKS`, atau `BUKAN_PELANGGARAN`.
  - `tingkat_risiko`: `RENDAH`, `SEDANG`, `TINGGI` (wajib bernilai `NULL` jika kategori adalah `BUKAN_PELANGGARAN`).
  - `topik_kode`: Kode topik terkontrol dari katalog taksonomi IPOLEKSOSBUDHANKAM yang aktif.
  - `topik_usulan`: String usulan nama topik baru (maksimal 80 karakter) jika analis/AI memilih kode `LAINNYA`.
  - `aktor_target`: Daftar entitas sasaran beserta klasifikasinya (`TOKOH_PUBLIK`, `INSTITUSI`, `KELOMPOK`, `INDIVIDU_PRIVAT`).
  - `media_asal`: Nama media/kanal penerbit yang teridentifikasi dari watermark, logo, atau teks konten.
  - `analisis_5w1h`: Ringkasan terstruktur dimensi *Who, What, Where, When, Why, How*.
- **FR-04.2 Isolasi Input Tak Tepercaya**: Teks caption, judul, dan teks OCR dibungkus dalam blok pembatas data eksplisit (*explicit data boundary*) agar tidak dieksekusi sebagai instruksi prompt (*prompt injection mitigation* T3).
- **FR-04.3 Jejak Model & Audit AI**: Setiap inferensi AI mencatat metadata teknis: `ai_model_id`, `prompt_version`, `token_count`, dan `execution_time_ms`.
- **FR-04.4 AI Gateway Terstandarisasi**: Menggunakan antarmuka API yang kompatibel dengan format standar OpenAI, sehingga arsitektur siap dialihkan ke model lokal (*on-premise*) tanpa mengubah kode aplikasi.

#### FR-05 Human-in-the-Loop (HITL) di Web Dashboard
- **FR-05.1 Antrean Validasi Terpusat**: Seluruh hasil triase AI masuk ke menu Antrean Validasi di Web Dashboard. Kartu antrean menampilkan gambar bukti Full HD, ringkasan analisis 5W+1H, rekomendasi kategori/risiko, dan rujukan preseden RAG.
- **FR-05.2 Tombol Keputusan & Kode Alasan Terstruktur**:
  - `[Setuju]`: Mengonfirmasi rekomendasi AI (transisi ke status `VALIDATED` atau `REJECTED`).
  - `[Ubah Kategori/Risiko]`: Memilih kategori atau risiko baru (transisi ke status `MODIFIED`) + **Wajib memilih Kode Alasan**.
  - `[Bukan Pelanggaran]`: Menggugurkan indikasi pelanggaran (transisi ke status `REJECTED`) + **Wajib memilih Kode Alasan**.
  - *Daftar Kode Alasan Baku*: `SATIRE_ATAU_HUMOR`, `FAKTA_TERVERIFIKASI`, `KONTEKS_TIDAK_TERBACA_AI`, `SALAH_KATEGORI`, `RISIKO_TERLALU_TINGGI`, `RISIKO_TERLALU_RENDAH`, `KONTEN_TIDAK_RELEVAN`, `LAINNYA` (catatan teks bebas hanya wajib diisi jika memilih `LAINNYA`).
- **FR-05.3 Validasi Atomik**: Transisi status dilakukan dengan *conditional update* di database (`WHERE status = 'WAITING_VALIDATION'`). Jika dua analis membuka kartu tiket yang sama, hanya transaksi pertama yang berhasil disimpan; analis kedua menerima notifikasi bahwa tiket telah diputuskan.
- **FR-05.4 Mode Keputusan**: Sistem mencatat mode keputusan: `NORMAL`, `BLIND` (evaluasi buta), `NO_AI` (analisis manual saat AI offline), dan `DUPLICATE` (konfirmasi duplikat).
- **FR-05.5 Revisi ADMIN & Penilaian Kedua**: ADMIN dapat merevisi putusan melalui dashboard dengan verifikasi TOTP (tercatat di tabel `report_revisions`). Analis dapat ditugaskan untuk melakukan penilaian kedua (*Second Review*) tanpa melihat putusan penilai pertama.

#### FR-06 Pelacakan Tiket, Duplikasi & Clustering
- **FR-06.1 Siklus Hidup Tiket**: Tiket melalui 7 status resmi: `PENDING_ANALYSIS`, `WAITING_VALIDATION`, `MANUAL_FALLBACK`, `FAILED`, `VALIDATED`, `MODIFIED`, `REJECTED`.
- **FR-06.2 Deteksi Duplikat Pasti**: Konten dengan URL kanonikal identik atau nilai hash SHA-256 identik otomatis dikaitkan ke laporan pertama (`duplicate_of`) dan berbagi `content_cluster_id` yang sama.
- **FR-06.3 Petunjuk Kemiripan pHash**: Jarak Hamming pHash $\le 6$ menghasilkan petunjuk kemiripan visual di antrean validasi dengan opsi cepat `[Sama dengan Induk]`.
- **FR-06.4 Content Clustering & Resolusi Konflik**: Jika tiket duplikat diputuskan berbeda dari laporan induk oleh analis, sistem menandainya sebagai `cluster_conflict` dan tidak menulis entri ganda ke Knowledge Base.
- **FR-06.5 Pelacakan Status di Dashboard**: Seluruh status pemrosesan tiket dapat dipantau langsung melalui menu dashboard tanpa perlu bot perpesanan.

#### FR-07 Generator Rekapitulasi Harian Dinas (.docx) & Ekspor
- **FR-07.1 Format Dokumen Dinas**: Sistem menyediakan generator dokumen dinas berformat Microsoft Word (.docx) berstempel waktu yang dapat diunduh langsung melalui menu Web Dashboard.
- **FR-07.2 Filter Laporan Final**: Dokumen rekapitulasi hanya memuat laporan yang telah berstatus akhir (`VALIDATED` dan `MODIFIED`).
- **FR-07.3 Integritas Dokumen & Chain Head**: Dokumen menyertakan tabel rekapitulasi kasus, tangkapan layar bukti ber-SHA-256, catatan analis, serta *chain head* hash audit log hari bersangkutan.
- **FR-07.4 Ekspor CSV Aman**: Ekspor data tabular otomatis melakukan *escaping* pada karakter formula (`=`, `+`, `-`, `@`) guna mencegah celah keamanan CSV Injection.

#### FR-08 Keamanan, Autentikasi & Audit Hash-Chain
- **FR-08.1 Otentikasi Terpusat**: Menggunakan kredensial username dan password terenkripsi Argon2id, manajemen sesi *server-side* di Redis, dan proteksi token CSRF pada seluruh permintaan mutasi data.
- **FR-08.2 2FA TOTP Wajib untuk ADMIN**: Akses peran ADMIN wajib memasukkan kode TOTP 6 digit berbasis RFC 6238.
- **FR-08.3 Bootstrap CLI ADMIN**: Pendaftaran akun ADMIN pertama kali wajib dilakukan melalui perintah aman antarmuka baris perintah (`manage create-admin`).
- **FR-08.4 Audit Hash-Chain**: Setiap baris pada tabel `audit_logs` menyimpan `prev_hash` dan `row_hash = SHA-256(prev_hash || data_baris)`.
- **FR-08.5 Pemisahan Hak Basis Data**: Layanan aplikasi terhubung menggunakan role database non-owner yang tidak memiliki izin perintah `ALTER TABLE`, `DROP TABLE`, atau manipulasi baris tabel `audit_logs`.
- **FR-08.6 Jangkar Eksternal Terjadwal**: Pukul 23.55 WIB setiap hari, sistem mengunci nilai hash entri audit terakhir hari itu dan menyematkannya ke dalam dokumen rekapitulasi yang disimpan di luar sistem oleh supervisor.
- **FR-08.7 Rate Limit & Audit Aksi**: Membatasi laju permintaan otentikasi dan mencatat seluruh aksi mutasi ke dalam audit log kekal.

#### FR-09 Knowledge Base RAG Terukur
- **FR-09.1 Konten Referensi Murni**: Entri Knowledge Base hanya memuat cuplikan teks konten asli + keputusan final analis + kode alasan + catatan analis. **Dilarang keras menyisipkan teks buatan AI** (`ai_reasoning` atau ringkasan AI) ke dalam KB untuk mencegah bias sirkular.
- **FR-09.2 Embedding Deterministik**: Teks korpus (judul + caption + teks OCR) diubah menjadi vektor 768 dimensi menggunakan model `gemini-embedding-001` dengan normalisasi L2.
- **FR-09.3 Exact Scan Retrieval**: Pencarian preseden menggunakan *Exact Scan Cosine Similarity* di PostgreSQL pgvector dengan filter ketat `is_active = True`, mengecualikan cluster konten yang sama, dengan ambang batas similarity terkalibrasi dan batas `top_k = 5`.
- **FR-09.4 Kontrol Kualitas & Cold Start**: Hanya satu entri aktif yang disimpan per cluster konten guna mencegah polusi data.
- **FR-09.5 Saklar Fitur (RAG Fail-Open)**: Parameter konfigurasi `RAG_ENABLED` dapat dimatikan kapan saja. Jika modul RAG offline atau kuota habis, sistem menerapkan *fail-open* (analisis AI berlanjut dengan konteks kosong).
- **FR-09.6 Kalibrasi Ambang Similarity & pHash**: Nilai ambang kemiripan vektor dan perceptual hash ditentukan melalui fase kalibrasi empiris sebelum diaktifkan permanen.

#### FR-10 Entitas & Topik Terkontrol IPOLEKSOSBUDHANKAM
- **FR-10.1 Taksonomi Terkontrol 8 Bidang**: Model AI memetakan isu konten ke dalam 8 bidang strategis nasional:
  1. `IPOL_IDEOLOGI`: Isu radikalisme, separatisme, ideologi anti-Pancasila.
  2. `IPOL_POLITIK`: Isu pemilu, kebijakan pemerintah, hoaks tokoh politik.
  3. `IEK_EKONOMI`: Isu inflasi, kelangkaan bahan pokok, penipuan finansial, perbankan.
  4. `ISOS_SOSIAL`: Isu kerusuhan warga, provokasi antarkelompok, keresahan publik.
  5. `IBUD_BUDAYA`: Isu penodaan agama, konflik adat, ujaran kebencian SARA.
  6. `IHANKAM_PERTAHANAN`: Isu kedaulatan perbatasan, militer, ancaman spionase.
  7. `IHANKAM_KEAMANAN`: Isu terorisme, sabotase siber, kamtibmas luas.
  8. `LAINNYA`: Topik baru yang belum terklasifikasi (wajib mengisi `topik_usulan`).
- **FR-10.2 Manajemen Aktor & Resolusi Alias**: Aktor dinormalisasi melalui *exact alias matching* dan diverifikasi oleh ADMIN (*Entity Resolution*).
- **FR-10.3 Fail-Closed Privasi (UU PDP)**: Aktor berkategori `INDIVIDU_PRIVAT` tidak pernah didaftarkan ke tabel entitas katalog publik. Nama aktor hanya ditampilkan pada dashboard jika telah disetujui ADMIN sebagai `TOKOH_PUBLIK`, `INSTITUSI`, atau `KELOMPOK`.
- **FR-10.4 Media Asal Terkontrol**: Mengidentifikasi media daring atau kanal sumber yang sering dijadikan rujukan konten.

#### FR-11 Web Dashboard Analitik Social Intelligence
- **FR-11.1 Konsol 9 Grafik Agregat**: Dashboard menyajikan metrik operasional agregat berbasis keputusan final analis:
  1. *Tren Waktu*: Perbandingan volume laporan masuk vs temuan terkonfirmasi per hari.
  2. *Distribusi Platform*: Komparasi YouTube, TikTok, Instagram, X/Threads.
  3. *Distribusi Kategori*: Sebaran kategori HOAKS, SARA, Ujaran Kebencian, dll.
  4. *Distribusi Risiko*: Proporsi tingkat risiko RENDAH, SEDANG, TINGGI.
  5. *Topik Teratas*: Peringkat sebaran isu berdasarkan bidang IPOLEKSOSBUDHANKAM.
  6. *Aktor Target Publik*: Peringkat aktor/lembaga yang paling sering menjadi sasaran narasi.
  7. *Media Asal Teratas*: Peringkat media daring yang paling sering dicatut/dijadikan sumber.
  8. *Tingkat Ketidaksepakatan*: Evaluasi persentase koreksi analis terhadap rekomendasi awal AI.
  9. *Progres Evaluasi Buta*: Monitoring sampel evaluasi buta RAG (FR-13).
- **FR-11.2 Filter & Drill-down Interaktif**: Kemampuan memfilter data berdasarkan rentang tanggal, platform, kategori, risiko, dan topik, serta navigasi langsung ke rincian tiket.
- **FR-11.3 Banner Penafian Netralitas Hukum Permanen**: Tersemat penafian etik resmi: *"Label frekuensi kemunculan topik, aktor, dan sumber tidak menunjukkan penetapan bersalah. Keputusan analis bukan penetapan hukum otomatis."*

#### FR-12 Browser Extension Operasional (MV3)
- **FR-12.1 Kompatibilitas Manifest V3**: Ekstensi berjalan di Google Chrome, Microsoft Edge, dan Mozilla Firefox menggunakan standar Manifest V3.
- **FR-12.2 Aksi Utama 1-Click Capture**: Satu klik pada popup ekstensi langsung mengambil tangkapan layar, struktur DOM, metadata, dan menghitung SHA-256.
- **FR-12.3 Keamanan Token Terenkripsi**: Token otentikasi disimpan di storage peramban terenkripsi (WebCrypto API) dan komunikasi wajib melalui enkripsi HTTPS.
- **FR-12.4 Notifikasi Nomor Tiket**: Setelah capture berhasil dikirim, ekstensi menampilkan nomor tiket resmi `PS-YYYYMMDD-XXXX` dan status pemrosesan.

#### FR-13 Evaluasi Buta RAG (Blind Evaluation)
- **FR-13.1 Sampling Buta Acak**: Tiket non-duplikat diundi secara acak sebesar 10% s.d. 20% (`EVAL_BLIND_RATE`) menjadi tiket evaluasi buta (`eval_blind = True`).
- **FR-13.2 Validasi Tanpa Bias**: Pada antrean validasi tiket buta, hasil rekomendasi AI disembunyikan total dari analis agar analis menilai murni berdasarkan fakta bukti visual (*unbiased ground truth*).
- **FR-13.3 Dual-Pipeline Execution (Fase 3)**: Di latar belakang, sistem mengeksekusi dua jalur AI secara paralel: Jalur A (dengan RAG) dan Jalur B (tanpa RAG).
- **FR-13.4 Ukuran Sampel & Keandalan Label**: Mengukur reliabilitas label antar-analis (*Cohen's Kappa*) sebelum hasil evaluasi buta dikunci.
- **FR-13.5 Aturan Keputusan Pra-Registrasi**:
  - Dihitung selisih performa: $\Delta = \text{Akurasi}(A) - \text{Akurasi}(B)$ terhadap label buta analis menggunakan uji skor Tango 90% dan uji McNemar.
  - Metrik keselamatan: Evaluasi ketat terhadap kesalahan fatal (*miss risiko tinggi*).
  - Status evaluasi: **LULUS** (RAG dipertahankan permanen), **GAGAL** (RAG dimatikan otomatis), atau **TIDAK MEYAKINKAN**.
- **FR-13.6 Pemantauan Berkelanjutan**: Evaluasi terus berjalan secara berkala untuk mendeteksi degradasi performa model (*data drift*).

#### FR-14 Administrasi Sistem (ADMIN Console)
- **FR-14.1 Manajemen Akun & Sesi**: ADMIN dapat membuat akun, menonaktifkan akun personel seketika ($\le 5$ detik), dan mengatur role pengguna.
- **FR-14.2 Kurasi Data & Resolusi Entitas**: ADMIN mengelola katalog topik IPOLEKSOSBUDHANKAM, menyetujui entitas publik baru, menggabungkan entitas duplikat (*Merge*), dan meninjau usulan topik `LAINNYA`.
- **FR-14.3 Tata Kelola KB**: Menolak operasi `UPDATE` dan `DELETE` fisik; penonaktifan entri KB dilakukan secara logis (`is_active = False`) dengan mencantumkan kode alasan.
- **FR-14.4 Revisi Keputusan Berjejak**: Mengubah keputusan tiket pasca-validasi dengan mencatat histori perubahan di tabel `report_revisions` dan *audit log*.
- **FR-14.5 Verifikasi Integritas Audit Hash-Chain**: Menu khusus untuk memverifikasi keutuhan rantai hash log audit terhadap nilai jangkar milik supervisor.
- **FR-14.6 Pemantauan Kesehatan Sistem & Kuota API**: Halaman pemantauan teknis yang menyajikan status koneksi database, antrean Redis, penggunaan kuota API Gemini, dan log kesalahan.

---

### 1.6 Persyaratan Non-Fungsional (Non-Functional Requirements)

| No | Parameter | Spesifikasi Standar Kualitas Teknis |
|---|---|---|
| **NFR-01** | **Isolasi Beban Komputasi** | Engine Playwright berjalan pada kontainer terpisah (`scraper`); pemrosesan AI, OCR Tesseract, dan kalkulasi embedding berjalan di kontainer `worker`. |
| **NFR-02** | **Persistensi Data** | Menggunakan PostgreSQL 16 dengan ekstensi `pgvector`, volume Docker persisten, dan fallback lokal mandiri SQLite (`storage/patrol.db`). |
| **NFR-03** | **Performa Retrieval** | Exact scan similarity ditargetkan selesai dalam waktu $< 500$ ms untuk volume basis pengetahuan hingga 100.000 entri. |
| **NFR-04** | **Fail-Open Bertingkat** | Gangguan pada layanan pihak ketiga (kuota Gemini habis atau jaringan putus) tidak boleh menggagalkan intake bukti. Sistem mencatat insiden dan melanjutkan triase manual. |
| **NFR-05** | **Keamanan Web Dashboard** | Enkripsi TLS, cookie sesi `HttpOnly` + `Secure` + `SameSite=Strict`, proteksi CSRF, Content Security Policy (CSP) ketat tanpa CDN luar, dan rate limit otentikasi. |
| **NFR-06** | **Kepatuhan Privasi (UU PDP)** | Nama individu privat tidak pernah dipublikasikan di dashboard; identitas hanya diagregasikan jika berstatus entitas publik yang disetujui. |
| **NFR-07** | **Integritas Knowledge Base** | Trigger basis data menolak operasi `UPDATE` terhadap isi entri KB yang telah tersimpan. Koreksi dilakukan dengan deaktivasi logis (`is_active = False`). |
| **NFR-08** | **Mekanisme Purge Terkendali** | Penghapusan data retensi dilakukan melalui prosedur fungsi database `purge_report()` yang menyisakan *tombstone* bukti ber-SHA-256 tanpa merusak rantai audit. |
| **NFR-09** | **Kedaulatan & Keamanan Data AI** | API Gemini berbayar/Vertex AI dikonfigurasi dengan region resmi dan jaminan kontraktual bahwa data masukan tidak digunakan untuk pelatihan model publik. |
| **NFR-10** | **Batas Anggaran Operasional** | Sistem memantau biaya token bulanan: ambang 80% menerbitkan peringatan ke admin; ambang 100% beralih otomatis ke tier model hemat biaya. |
| **NFR-11** | **Pencadangan & Uji Pemulihan** | Backup otomatis harian (`pg_dump` dan arsip bukti) terenkripsi kunci publik dengan retensi 30 hari, disertai prosedur uji pemulihan (*restore test*) bulanan. |
| **NFR-12** | **Observabilitas Sistem** | Log terstruktur format JSON, visualisasi metrik kesehatan sistem pada dashboard admin, dan monitoring antrean worker. |
| **NFR-13** | **Standar Ekstensi Peramban** | Memenuhi arsitektur Manifest V3 resmi, tanpa dependensi pustaka pihak ketiga yang tidak aman, dan bebas dari pelacakan latar belakang (*zero-telemetry*). |
| **NFR-14** | **Arsitektur Gateway Netral** | Menggunakan layer abstraksi AI yang siap dialihkan ke model sumber terbuka (*Open-Source LLM*) secara lokal di workstation dinas. |

---

### 1.7 Target Tingkat Layanan (SLO) dan Metrik Keberhasilan

| Indikator Kinerja Layanan | Target Objektif (SLO) | Cara Pengukuran |
|---|---|---|
| **Waktu Terbit Tiket Ekstensi (p95)** | $\le 10$ detik | Dihitung dari waktu klik ekstensi hingga nomor tiket terbit. |
| **Waktu Tiket ke Antrean Validasi (p95)** | $\le 3$ menit | Dihitung dari waktu submit hingga kartu muncul di antrean analis. |
| **Rasio Keberhasilan Capture Ekstensi** | $\ge 95\%$ (7 hari bergulir) | Persentase capture sukses tanpa kegagalan transmisi. |
| **Rasio Keberhasilan Scraper Fallback** | $\ge 85\%$ (Alarm jika $< 70\%$) | Pengujian otomatis berkala pada URL publik tanpa login-wall. |
| **Kegagalan Validasi Race Condition** | Tepat $0$ kasus | Verifikasi integritas transaksi database bersyarat. |
| **Waktu Respons Kueri Dashboard (p95)** | $\le 2$ detik | Kueri agregat data 12 bulan terakhir pada dashboard analitik. |
| **Presisi Petunjuk Kemiripan pHash** | $\ge 90\%$ | Persentase konfirmasi kecocokan visual oleh analis pada saran duplikat. |
| **Antrean Kurasi Entitas Tertunda** | $< 50$ item | Jumlah usulan entitas/topik baru yang menunggu review ADMIN. |
| **Biaya Pemrosesan per Tiket** | Terpantau & Terukur | Ditetapkan baseline biaya pada Fase 1 rilis bertahap. |
| **Peningkatan Kualitas AI** | Terbukti Matematis | Diukur secara eksklusif lewat metodologi evaluasi buta (FR-13). |

---

### 1.8 Model Ancaman Sistem (Threat Model)

| ID | Vektor Ancaman | Dampak Risiko | Mitigasi Arsitektur Terpasang |
|---|---|---|---|
| **T1** | **SSRF via Scraper Fallback** | Penyerang mengirimkan URL intranet dinas untuk memetakan jaringan internal. | *Egress allowlist* domain media sosial resmi, isolasi jaringan kontainer `scraper` tanpa akses DB/kredensial, dan re-create kontainer berkala. |
| **T2** | **Keracunan Basis Pengetahuan (KB Poisoning)** | Analis keliru memasukkan label salah yang mencemari rekomendasi kasus berikutnya. | Evaluasi buta berkelanjutan (FR-13), kode alasan wajib, satu entri aktif per cluster, dan prosedur penonaktifan entri KB berjejak audit. |
| **T3** | **Serangan Prompt Injection** | Konten media sosial menyisipkan teks manipulatif untuk mengecoh keputusan AI. | *Data boundary* eksplisit, KB hanya menyuntikkan teks konten asli + putusan analis (tanpa narasi AI), validasi skema output, dan HITL mutlak. |
| **T4** | **Pemalsuan Bukti Tangkapan Layar** | Bukti dimanipulasi sebelum diserahkan ke proses hukum. | Hashing SHA-256 seketika di peramban klien, verifikasi ulang di worker, pencatatan `ai_model_id`, dan rantai audit hash-chain. |
| **T5** | **Pembajakan Ekstensi / Sesi Browser** | Kredensial personel dicuri dari workstation dinas. | Token tersimpan di storage peramban terenkripsi (WebCrypto API), enkripsi HTTPS wajib, sesi server-side Redis, CSRF protection, dan rate limit. |
| **T6** | **Penyalahgunaan Wewenang ADMIN** | Administrator mengubah catatan vonis atau memanipulasi bukti secara sepihak. | Audit hash-chain terhubung ke jangkar supervisor di luar sistem, pemisahan hak akun DB non-owner, dan pencatatan revisi di laporan DOCX. |
| **T7** | **Berkas Biner Perusak (DoS / Zip Bomb)** | Pengguna mengunggah gambar jebakan berukuran piksel raksasa untuk mematikan worker. | Pengecekan tipe MIME biner asli, batas ukuran berkas 20 MB, dan pembatasan resolusi memori Pillow `MAX_IMAGE_PIXELS`. |
| **T8** | **Pengambilalihan Sesi Web Dashboard** | Sesi analis dibajak melalui serangan XSS atau pencurian cookie. | Manajemen sesi *server-side* di Redis, cookie `HttpOnly` + `Secure` + `SameSite=Strict`, CSP ketat, dan auto-logout idle 30 menit. |

---

### 1.9 Kriteria Penerimaan Sistem (Acceptance Criteria)

| ID | Kriteria Pengujian Penerimaan Teknis |
|---|---|
| **AC-01** | URL ke host internal (RFC1918, link-local, localhost) atau domain di luar allowlist ditolak seketika dan dicatat ke log audit. |
| **AC-02** | Dua analis mengeksekusi validasi pada tiket yang sama dalam selisih $< 1$ detik: tepat 1 transaksi berhasil disimpan, analis lain menerima notifikasi informatif. |
| **AC-03** | Pilihan Ubah atau Bukan Pelanggaran tanpa kode alasan ditolak oleh sistem; kode alasan `LAINNYA` wajib menyertakan catatan teks. |
| **AC-04** | Tautan yang sama dilaporkan dua kali: tiket kedua otomatis terhubung ke `duplicate_of` dan dihitung 1 konten unik pada dashboard analitik. |
| **AC-05** | Kueri retrieval RAG tidak pernah mengembalikan entri dari cluster konten yang sama atau entri yang berstatus `is_active = False`. |
| **AC-06** | Simulasi API embedding offline: tiket laporan tetap berhasil sampai ke antrean validasi dengan status penanda `rag_mode = FAILED`. |
| **AC-07** | Aktor berkategori `INDIVIDU_PRIVAT` atau entitas berstatus `PENDING_REVIEW` terbukti tidak tampil pada visualisasi grafik publik dashboard. |
| **AC-08** | Manipulasi langsung pada baris database `audit_logs` (mengubah data atau menyisipkan baris) terdeteksi secara otomatis saat verifikasi hash dijalankan. |
| **AC-09** | Tiket evaluasi buta (`eval_blind = True`): kartu antrean menyembunyikan seluruh hasil rekomendasi AI hingga keputusan analis disimpan. |
| **AC-10** | Akun personel yang dinonaktifkan oleh ADMIN menyebabkan sesi aktif di browser terputus seketika dalam waktu $\le 5$ detik; ADMIN tanpa TOTP ditolak login. |
| **AC-11** | Pengujian terhadap 20 kasus uji prompt injection membuktikan maksimal 1 dari 20 kasus yang berhasil memengaruhi output klasifikasi AI. |
| **AC-12** | Prosedur uji restore database dan folder bukti pada server bersih membuktikan seluruh nilai hash SHA-256 berkas cocok 100%. |
| **AC-13** | Perintah `UPDATE` terhadap isi kolom data tabel `knowledge_entries` ditolak secara langsung oleh trigger basis data. |
| **AC-14** | Sel berkas ekspor CSV yang diawali karakter formula (`=`, `+`, `-`, `@`) otomatis di-escape guna mencegah celah CSV Injection. |
| **AC-15** | Berkas *decompression bomb* dan file biner berformat palsu ditolak oleh sistem tanpa menyebabkan crash pada worker. |
| **AC-16** | Dua berkas gambar identik dengan tingkat kompresi berbeda berhasil menghasilkan petunjuk kemiripan visual pHash pada antrean validasi. |
| **AC-17** | Revisi keputusan oleh ADMIN di dashboard berhasil memperbarui status laporan, mencatat rekaman di `report_revisions`, dan menonaktifkan entri KB lama. |
| **AC-18** | Simulasi batas anggaran tercapai 100%: sistem otomatis menonaktifkan pembuatan embedding baru dan menjalankan triase dengan tier model hemat biaya. |
| **AC-19** | Uji unit kalkulasi metrik evaluasi buta (interval Tango score, uji McNemar, dan aturan kelulusan) terverifikasi akurat secara matematis. |
| **AC-20** | Akun pengguna database aplikasi terbukti gagal saat mencoba menjalankan perintah `ALTER TABLE`, `DROP TABLE`, atau manipulasi trigger. |
| **AC-21** | Pengujian jaringan membuktikan kontainer `scraper` gagal melakukan koneksi ke kontainer basis data maupun jaringan lokal internal. |
| **AC-22** | Berkas hasil scraping yang memiliki nonce salah, path di luar direktori scratch, symlink, atau non-JSON ditolak oleh worker collector. |
| **AC-23** | Dokumen rekapitulasi dinas harian berhasil mencantumkan nilai *chain head* hash audit log hari bersangkutan yang terverifikasi cocok dengan salinan supervisor. |
| **AC-24** | Akses ke endpoint intake internal tanpa API key yang sah ditolak dengan status HTTP 401 Unauthorized; pencabutan API key berlaku seketika. |
| **AC-25** | Tiket duplikat yang diputuskan berbeda dari laporan induk otomatis ditandai `cluster_conflict` dan tidak menulis entri ganda ke Knowledge Base. |
| **AC-26** | Lalu lintas keluar (*egress*) dari kontainer backend ke domain luar yang tidak terdaftar di allowlist proxy terbukti diblokir. |
| **AC-27** | Tiket yang sedang dalam proses penilaian kedua (*Second Review*) menyembunyikan identitas keputusan analis pertama dari penilai kedua. |
| **AC-28** | Ekstensi berhasil mengirim gambar + DOM + SHA-256; worker memverifikasi kecocokan hash; mismatch memicu status `FAILED` dan audit alert. |
| **AC-29** | Penanganan konten berhalangan login-wall (X/Threads) sukses diakuisisi secara visual melalui active-tab capture ekstensi peramban. |
| **AC-30** | Audit keamanan kode ekstensi membuktikan tidak ada penyimpanan kredensial password dalam storage peramban; komunikasi wajib HTTPS. |
| **AC-31** | Penambahan adapter media sosial baru dapat dilakukan secara modular tanpa mengubah inti alur pemrosesan worker. |
| **AC-32** | Topik baru berstatus `LAINNYA` muncul dalam daftar antrean usulan admin tanpa langsung mencemari katalog topik utama IPOLEKSOSBUDHANKAM. |

---

## 2. Data Flow Diagram (DFD)

### 2.1 DFD Level 0 (Context Diagram)

Sistem Asisten Patroli Siber berinteraksi dengan **5 Entitas Eksternal**:
1. **Petugas Piket Patroli**: Berselancar di workstation dinas menggunakan Ekstensi Peramban (MV3) untuk mengirimkan tautan, snapshot DOM, tangkapan layar, dan hash SHA-256 awal.
2. **Analis Intelijen Siber / Administrator**: Mengakses Web Dashboard untuk memvalidasi antrean tiket, menganalisis grafik agregat, merevisi keputusan, dan mengunduh berkas dinas.
3. **Platform Media Sosial (YouTube, TikTok, Instagram, X/Threads)**: Sumber konten publik daring yang diambil bukti visual dan metadatanya.
4. **Google Gemini AI Gateway**: Layanan model kecerdasan buatan untuk pembentukan embedding vektor 768-D dan analisis multimodal 5W+1H.
5. **Supervisor / Pimpinan Piket**: Menerima dokumen rekapitulasi harian dinas (.docx) dan menyimpan salinan sah nilai jangkar audit hash-chain di luar sistem.

```
                           ┌───────────────────────────────┐
                           │     Platform Media Sosial     │
                           │(YouTube, TikTok, IG, X/Threads)│
                           └───────────────┬───────────────┘
                                           │
                         Navigasi Halaman  │  Tangkapan Layar & DOM
                         & Konten Publik   │  (Client-First / Fallback)
                                           ▼
 ┌───────────────────────────┐      ┌──────────────────────────────┐      ┌───────────────────────────┐
 │   Petugas Piket Patroli   │      │                              │      │   Google Gemini AI Gateway│
 │  (Workstation + Ekstensi) ├─────►│                              ├─────►│  (Multimodal Vision + Emb)│
 │                           │Capture│                              │Prompt│                           │
 │                           │SHA-256│                              │5W+1H │                           │
 │                           │      │ SISTEM ASISTEN PATROLI SIBER │      │                           │
 │                           │◄─────┤      PRD v3.1 ENTERPRISE     │◄─────┤                           │
 │                           │Tiket │   (BROWSER EXTENSION + WEB)  │JSON &│                           │
 │                           │Status│                              │Vector│                           │
 └───────────────────────────┘      └──────────────┬───────────────┘      └───────────────────────────┘
                                                   │
                                     Autentikasi,  │  Data Agregat,
                                     Validasi HITL,│  Grafik Dashboard,
                                     Kode Alasan   │  & Berkas Laporan
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │  Analis & Supervisor Piket   │
                                    │(Web Dashboard & Arsip Rekap) │
                                    └──────────────────────────────┘
```

---

### 2.2 DFD Level 1 (Dekomposisi Proses & Data Store)

#### Daftar 12 Data Store Fisik:
- **D1: Pengguna Sistem** (`users`)
- **D2: Profil Akun Media Sosial** (`accounts`)
- **D3: Konten Media Sosial** (`contents`)
- **D4: Berkas Bukti Digital** (`evidences`)
- **D5: Laporan & Tiket Patroli** (`reports`, `report_revisions`)
- **D6: Entitas, Alias & Aktor Sasaran** (`entities`, `entity_aliases`, `report_actors`)
- **D7: Basis Pengetahuan Preseden RAG** (`knowledge_entries`)
- **D8: Katalog Topik Terkontrol** (`topics`)
- **D9: Log Audit Forensik Hash-Chain** (`audit_logs`)
- **D10: Taksonomi & Konfigurasi** (`config_taxonomy`)
- **D11: Sesi & Antrean Cepat Redis** (`redis` default)
- **D12: Antrean Tugas Scraper Fallback** (`redis-scrape`)

#### Diagram Aliran Proses Level 1:
```
[Petugas + Ekstensi] ──Capture+SHA256──► ( 1.0 Intake Ekstensi & Validasi )
                                                    │
                                                    ├──Tiket Baru──► D5 (reports)
                                                    │
                                                    ▼
                                         ( 2.0 Verifikasi Hash & Simpan ) ◄── D11 (Redis)
                                                    │
                                                    ├──Meta Akun/Konten──► D2 (accounts), D3 (contents)
                                                    ├──Bukti & SHA-256──► D4 (evidences), Storage Fisik
                                                    │
                                                    ▼
                                         ( 3.0 OCR & Retrieval Preseden ) ◄── D7 (knowledge_entries)
                                                    │
                                                    ├──Top-k Preseden
                                                    ▼
                                         ( 4.0 Triase Cerdas 5W+1H ) ◄── Gemini AI Gateway
                                                    │
                                                    ├──Rekomendasi JSON──► D5 (reports)
                                                    │
                                                    ▼
                                         ( 5.0 Antrean Validasi Dashboard ) ◄── [ Analis Intelijen ]
                                                    │
                                                    ├──Putusan + Kode Alasan──► D5 (reports), D9 (audit_logs)
                                                    │
                                                    ▼
                                         ( 6.0 Asimilasi KB & Entitas ) ──► D7 (knowledge_entries)
                                                    │                    ──► D6 (entities, report_actors)
                                                    │
                                                    ▼
[Dashboard / Supervisor] ◄──Visual & DOCX── ( 7.0 Agregasi Analitik & Rekap ) ◄── D5, D6, D8, D9
```

---

### 2.3 Rincian Dekomposisi Proses Kritis (DFD Level 2)

#### Proses 2.0 (Verifikasi Hash & Akuisisi Bukti)
1. Worker menerima payload biner berkas bukti dan nilai hash SHA-256 dari antrean Redis.
2. Worker menghitung ulang nilai hash biner gambar menggunakan modul `hashlib.sha256()`.
3. Jika nilai hash cocok: berkas dipindahkan ke `storage/evidences/{report_id}_{hash}.png` dengan izin berkas *read-only* (0444), kemudian nilai perceptual hash (pHash 64-bit) dihitung untuk deteksi kemiripan visual.
4. Jika nilai hash berbeda: status tiket diubah menjadi `FAILED`, transaksi dibatalkan, dan kejadian dicatat sebagai pelanggaran integritas data di `audit_logs`.

#### Proses 3.0 (Retrieval RAG Preseden & Ekstraksi OCR)
1. Tesseract OCR mengekstrak seluruh teks yang tampak pada tangkapan layar bukti visual.
2. Menggabungkan teks caption, judul, dan teks OCR menjadi teks representasi konten.
3. Menghasilkan vektor embedding 768 dimensi via `gemini-embedding-001` dengan normalisasi L2.
4. Melakukan *Exact Scan Cosine Similarity* terhadap tabel `knowledge_entries` dengan kriteria: `is_active = True`, `content_cluster_id != current_cluster_id`, nilai kemiripan $\ge 0.75$, dan batas maksimal 5 preseden teratas.

#### Proses 4.0 (Triase Cerdas 5W+1H & Evaluasi Buta Dual AI)
1. Sistem memeriksa flag `eval_blind`: jika tiket terpilih sebagai sampel buta (10%), eksekusi dilakukan paralel untuk Jalur A (dengan konteks RAG) dan Jalur B (tanpa konteks RAG).
2. Prompt multimodal dikirim ke Gemini Vision API dengan pembungkus *explicit data boundary* untuk mengisolasi konten tak tepercaya.
3. Respons divalidasi ketat terhadap skema Pydantic `AIPatrolAnalysis`.
4. Output disimpan ke database; untuk tiket buta, hasil rekomendasi AI disembunyikan dari tampilan antrean validasi analis.

#### Proses 5.0 (Validasi Human-in-the-Loop di Dashboard)
1. Analis membuka antrean tiket di konsol Web Dashboard.
2. Analis meninjau tangkapan layar Full HD, rincian 5W+1H, rekomendasi kategori/risiko, dan rujukan kasus serupa.
3. Analis memilih salah satu tindakan: `[Setuju]`, `[Ubah Kategori/Risiko]`, atau `[Bukan Pelanggaran]` beserta kode alasan wajib.
4. Database mengeksekusi *conditional update* secara atomik: `UPDATE reports SET status = :new_status WHERE id = :id AND status = 'WAITING_VALIDATION'`.

#### Proses 8.0 (Audit Hash-Chain & External Anchor)
1. Setiap transaksi mutasi menulis baris baru ke tabel `audit_logs`.
2. Nilai hash baris baru dihitung: `row_hash = SHA-256(prev_hash || id || action || details || created_at)`.
3. Pukul 23.55 WIB setiap malam, scheduler otomatis mengambil `row_hash` terakhir hari itu (*chain head*) dan menyematkannya ke ringkasan dokumen rekapitulasi dinas (.docx) yang diunduh dan diarsipkan secara fisik oleh supervisor piket.

---

## 3. Arsitektur Sistem

### 3.1 Komponen Terdistribusi Modular

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        KONSOL OPERASIONAL WORKSTATION                                  │
│                                                                                        │
│   [ Ekstensi Peramban (Chrome / Edge / Firefox MV3) ]        [ Web Dashboard Console ] │
│   - 1-Click Visible Tab Capture & DOM Snapshot               - Antrean Validasi Analis │
│   - SHA-256 Calculation di Titik Klien (WebCrypto)           - 9 Grafik Analitik       │
│   - Token Otentikasi Terenkripsi                             - Manajemen Topik/Entitas │
└────────────────────────────────────────┬───────────────────────────────┬───────────────┘
                                         │ HTTPS / Bearer Token          │
                                         ▼                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI CENTRAL SERVICE LAYER                                 │
│                                                                                        │
│   - /api/v1/auth/* (Otentikasi Argon2id + 2FA TOTP)                                   │
│   - /api/v1/intake/extension (Penerimaan Bukti Digital Klien)                          │
│   - /api/v1/dashboard/queue (Antrean Tiket Analis & Validasi Atomik)                   │
│   - /api/v1/dashboard/analytics (Kueri 9 Visualisasi Agregat IPOLEKSOSBUDHANKAM)       │
│   - /api/v1/admin/* (Revisi Keputusan, Kurasi Entitas, Audit Verifier)                 │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ Enqueue Asinkron
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     REDIS BROKER & DISTRIBUTED CELERY WORKERS                          │
│                                                                                        │
│     [ Redis Broker (Queue: default) ] ──► [ Celery Processing Workers ]                │
│                                                    │                                   │
│            ┌───────────────────────────────────────┴────────────────────────────┐      │
│            ▼                                                                    ▼      │
│   [ Pipeline Bukti & OCR ]                                           [ Pipeline AI ]   │
│   - Re-verifikasi Hash SHA-256                                       - Gemini Gateway  │
│   - OCR Tesseract (ind+eng)                                          - Retrieval RAG   │
│   - Deteksi Duplikasi pHash                                          - Evaluasi Buta   │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ Persistensi Data
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE & SECURITY LAYER                                   │
│                                                                                        │
│   [ PostgreSQL 16 + pgvector ]                      [ Storage Bukti Digital ]          │
│   - 11 Tabel Relasional Resmi                       - storage/evidences/ (PNG)         │
│   - Partial Unique Index KB per Cluster             - storage/reports/ (DOCX)          │
│   - Hash-Chain Log Audit Terenkripsi                - Read-Only Forensik Volume        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Alur Operasional End-to-End

1. **Patroli & Deteksi**: Personel berselancar di workstation dinas. Saat menemukan konten mencurigakan, personel mengklik ikon ekstensi peramban (*1-Click Triage*).
2. **Client-Side Capture**: Ekstensi mengambil tangkapan layar tab aktif, mengekstrak rendered DOM, menghitung hash SHA-256 berkas biner di memori browser klien, dan mengirimkannya ke API backend via HTTPS.
3. **Penerbitan Tiket**: Backend menerbitkan nomor tiket resmi `PS-YYYYMMDD-XXXX` berstatus `PENDING_ANALYSIS`.
4. **Verifikasi Forensik & OCR**: Worker memverifikasi kecocokan hash SHA-256, mengekstrak teks gambar menggunakan Tesseract OCR deterministik, dan mendeteksi potensi duplikasi (pHash).
5. **Retrieval RAG Preseden**: Worker membuat embedding semantik teks kueri dan melakukan *exact scan* ke Knowledge Base untuk mengambil 5 kasus serupa yang pernah diputuskan analis sebelumnya.
6. **Triase AI Multimodal**: AI menganalisis visual bukti dan teks konteks untuk menghasilkan ringkasan 5W+1H, rekomendasi kategori, tingkat risiko, dan topik IPOLEKSOSBUDHANKAM. Tiket berstatus `WAITING_VALIDATION`.
7. **Antrean Validasi Dashboard**: Analis membuka antrean validasi di dashboard monitor, meninjau bukti Full HD, dan memilih putusan: `[Setuju]`, `[Ubah]`, atau `[Bukan Pelanggaran]` beserta kode alasan wajib.
8. **Asimilasi Pengetahuan**: Putusan final analis secara otomatis dicatat ke Knowledge Base sebagai preseden baru dan entitas dinormalisasi ke katalog.
9. **Visualisasi Agregat**: Dashboard analitik seketika memperbarui 9 grafik analitik berdasarkan keputusan final analis.
10. **Pengunduhan Rekapitulasi Dinas**: Analis mengunduh berkas laporan dinas resmi (.docx) berstempel waktu dinas dan ber-jangkar audit hash-chain.

---

### 3.3 State Machine Siklus Hidup Tiket

```
[ PENDING_ANALYSIS ]
        │
        ├── Capture sukses (AI sukses) ─────────────────────────► [ WAITING_VALIDATION ]
        ├── Capture sukses (AI offline / limit) ────────────────► [ WAITING_VALIDATION ] (Flag: NO_AI)
        ├── Sampel evaluasi buta (Bukti tersimpan) ─────────────► [ WAITING_VALIDATION ] (Flag: BLIND)
        │                                                                │
        │   ┌────────────────────────────────────────────────────────────┘
        │   │
        │   ├── Analis klik [Setuju] (Rekomendasi Pelanggaran) ─► [ VALIDATED ]
        │   ├── Analis klik [Ubah Kategori/Risiko] (+Kode Alasan) ► [ MODIFIED ]
        │   ├── Analis klik [Bukan Pelanggaran] (+Kode Alasan) ──► [ REJECTED ]
        │   └── Konfirmasi Duplikat (Status ikut laporan induk) ─► [ VALIDATED / MODIFIED / REJECTED ]
        │
        ├── Capture gagal (Koneksi putus / server error) ───────► [ MANUAL_FALLBACK ]
        │         │
        │         └── Personel unggah file bukti manual ────────► [ PENDING_ANALYSIS ]
        │
        └── Hash mismatch / Bukti korup ────────────────────────► [ FAILED ]

* Revisi oleh ADMIN (Dashboard + TOTP) pada tiket berstatus akhir:
  [ VALIDATED / MODIFIED / REJECTED ] ──Revisi ADMIN──► Status Baru (+ Catatan report_revisions)
```

---

### 3.4 Skema Basis Data 11 Tabel Relasional Resmi

```
┌────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│         users          │       │        contents        │       │       evidences        │
├────────────────────────┤       ├────────────────────────┤       ├────────────────────────┤
│ id (PK, UUID)          │       │ id (PK, UUID)          │       │ id (PK, UUID)          │
│ username (Varchar, UQ) │       │ canonical_url (Text)   │       │ report_id (FK, UUID) ──┼──┐
│ hashed_password (Text) │       │ platform (Varchar)     │       │ file_path (Text)       │  │
│ full_name (Varchar)    │       │ text_caption (Text)    │       │ file_hash_sha256 (64)  │  │
│ role (OPERATOR/ANALYST)│       │ rendered_dom (Text)    │       │ phash (String 16)      │  │
│ totp_secret (Text, Null│       │ published_at (DateTime)│       │ created_at (DateTime)  │  │
└────────────────────────┘       └───────────┬────────────┘       └────────────────────────┘  │
                                             │ 1                                              │
                                             │                                                │
                                             │ N                                              │
                                 ┌───────────▼────────────┐                                   │
                                 │        reports         │◄──────────────────────────────────┘
                                 ├────────────────────────┤
                                 │ id (PK, UUID)          │
                                 │ ticket_number (UQ)     │
                                 │ content_id (FK, UUID)  │
                                 │ reporter_id (FK, UUID) │
                                 │ status (7 Status Enum) │
                                 │ ai_category (Varchar)  │
                                 │ ai_risk_level (Varchar)│
                                 │ topic_code (Varchar)   │
                                 │ final_category(Varchar)│
                                 │ final_risk_level (Var) │
                                 │ analyst_notes (Text)   │
                                 │ content_cluster_id (ID)│
                                 └───────────┬────────────┘
                                             │
                        ┌─────────────────────┼─────────────────────┐
                        │ 1                   │ 1                   │ 1
                        │                     │                     │
                        │ N                   │ N                   │ N
┌──────────────────────▼─┐    ┌──────────────▼─────────┐    ┌──────▼─────────────────┐
│   knowledge_entries    │    │     report_actors      │    │       audit_logs       │
├────────────────────────┤    ├────────────────────────┤    ├────────────────────────┤
│ id (PK, UUID)          │    │ report_id (PK, FK)     │    │ id (PK, UUID)          │
│ report_id (FK, UUID)   │    │ entity_id (PK, FK) ────┼─┐  │ actor_username (Varchar│
│ content_summary (Text) │    │ role (TARGET/MENTIONED)│ │  │ action (Varchar)       │
│ embedding (Vector-768) │    └────────────────────────┘ │  │ prev_hash (CHAR 64)    │
│ final_category(Varchar)│                               │  │ row_hash (CHAR 64)     │
│ is_active (Bool)       │    ┌────────────────────────┐ │  │ details (JSONB)        │
│ deactivated_at (Date)  │    │        entities        │ │  │ created_at (DateTime)  │
└────────────────────────┘    ├────────────────────────┤ │  └────────────────────────┘
                              │ id (PK, UUID)          │◄┘
                              │ name (Varchar, UQ)     │
                              │ category (TOPIC/ACTOR) │
                              │ status (APPROVED/MERGE)│
                              └────────────────────────┘
```

#### Rincian Tabel Tambahan:
- **`topics`**: `topic_code` (PK), `bidang` (IPOLEKSOSBUDHANKAM), `label`, `is_active`, `created_at`.
- **`report_revisions`**: `revision_id` (PK), `report_id` (FK), `old_label`, `new_label`, `reason_code`, `revised_by` (FK), `revised_at`.
- **`entity_aliases`**: `alias_id` (PK), `entity_id` (FK), `alias_text`, `alias_normalized`.
- **`config_taxonomy`**: `version`, `categories` (JSONB), `reason_codes` (JSONB), `is_current`.

---

### 3.5 Topologi Docker Compose 10 Service

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER NETWORK: internal-net (Isolasi Penuh)                    │
│                                                                                        │
│   [ db ] ── (PostgreSQL 16 + pgvector)                                                 │
│   [ redis ] ── (Default Broker & Server-Side Sessions)                                │
│   [ app ] ── (FastAPI REST Service)                                                   │
│   [ worker ] ── (Celery Task Processor: AI, OCR, Hash Verify)                         │
│   [ celery-beat ] ── (Scheduler Jangkar Audit & Backup Harian)                       │
│   [ backup ] ── (Automated pg_dump + Encrypted Storage Archive)                       │
│   [ proxy ] ── (Reverse Proxy Nginx / TLS Termination)                                │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                        DOCKER NETWORK: scrape-net (Terisolasi SSRF)                    │
│                                                                                        │
│   [ redis-scrape ] ── (Antrean Khusus Scraper Server)                                 │
│   [ scraper ] ── (Playwright Headless Container)                                       │
│       * Dilarang koneksi ke db, redis, dan intranet dinas (iptables rule terpasang)    │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                        DOCKER NETWORK: egress-net (Akses Keluar Terkontrol)            │
│                                                                                        │
│   [ egress-proxy ] ── (Squid Allowlist Proxy ke Domain Medsos Publik & Gemini API)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.6 REST API Specification

| Method | Endpoint | Hak Akses Minimal | Fungsi Operasional & Respons |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Publik | Otentikasi pengguna Web Dashboard & Ekstensi (mendukung 2FA TOTP). |
| `POST` | `/api/v1/auth/logout` | Terotentikasi | Mengakhiri sesi aktif dan menghapus token dari Redis server-side. |
| `POST` | `/api/v1/intake/extension` | OPERATOR | Menerima berkas gambar biner, snapshot DOM, URL, dan hash SHA-256 dari ekstensi. |
| `GET` | `/api/v1/dashboard/queue` | ANALYST | Mengambil daftar tiket yang menunggu validasi pada antrean kerja analis. |
| `POST` | `/api/v1/dashboard/decide` | ANALYST | Menyimpan keputusan validasi analis (`VALIDATED`, `MODIFIED`, `REJECTED`) + kode alasan. |
| `GET` | `/api/v1/dashboard/analytics` | ANALYST | Mengambil metrik agregat untuk 9 grafik analitik visual dashboard. |
| `GET` | `/api/v1/dashboard/reports` | ANALYST | Daftar detail tiket laporan terfilter untuk fitur *drill-down* interaktif. |
| `GET` | `/api/v1/dashboard/export/docx`| ANALYST | Mengunduh berkas laporan dinas resmi Microsoft Word (.docx) berstempel waktu. |
| `GET` | `/api/v1/dashboard/export/csv` | ANALYST | Mengekspor data temuan final ke format CSV aman (anti-CSV injection). |
| `POST` | `/api/v1/admin/revisions` | ADMIN | Konsol revisi keputusan analis sebelumnya yang dilindungi otentikasi TOTP. |
| `POST` | `/api/v1/admin/audit/verify` | ADMIN | Memvalidasi integritas rantai audit hash-chain terhadap nilai jangkar supervisor. |
| `GET/POST`| `/api/v1/admin/topics` | ADMIN | Mengelola daftar katalog topik terkontrol IPOLEKSOSBUDHANKAM. |
| `GET/POST`| `/api/v1/admin/entities` | ADMIN | Menyetujui atau menggabungkan entitas aktor publik (*Entity Resolution*). |
| `GET` | `/api/v1/admin/health` | ADMIN | Menampilkan metrik kesehatan teknis sistem, worker Celery, dan database. |

---

### 3.7 Mekanisme Keandalan Sistem

1. **Fail-Open Bertingkat**:
   - Jika modul embedding offline $\rightarrow$ Triase AI tetap berjalan dengan rujukan preseden kosong (`rag_mode = FAILED`).
   - Jika layanan Gemini AI offline $\rightarrow$ Tiket dialihkan ke antrean validasi manual dengan label `NO_AI`.
   - Jika capture ekstensi gagal $\rightarrow$ Sistem menyediakan form fallback unggah manual di dashboard.
2. **Idempotensi Penanganan Duplikasi**: Seluruh request ingest memeriksa keberadaan URL kanonikal dan nilai hash SHA-256. Duplikat terkonfirmasi langsung dihubungkan ke laporan pertama tanpa membebani antrean AI ganda.
3. **Saklar Fitur (Feature Flags)**: Konfigurasi `RAG_ENABLED`, `EVAL_BLIND_ENABLED`, dan `FALLBACK_SCRAPER_ENABLED` dapat diubah secara dinamis tanpa perlu merestart seluruh kontainer.

---

### 3.8 Observabilitas & Pemantauan Kesehatan Sistem

Konsol admin menyediakan halaman kesehatan sistem dengan **10 indikator alarm dini**:
1. Rasio error worker Celery $> 5\%$ dalam 15 menit terakhir.
2. Panjang antrean tugas Celery $> 100$ tugas tertunda.
3. Keberhasilan scraper Playwright server-side $< 70\%$.
4. Utilisasi kuota API Gemini bulanan $> 80\%$.
5. Waktu respons kueri database (p95) $> 1000$ ms.
6. Sisa kapasitas penyimpanan disk bukti digital $< 15\%$.
7. Deteksi *hash mismatch* pada transmisi bukti ekstensi.
8. Kegagalan integritas rantai audit *hash-chain*.
9. Jumlah antrean kurasi entitas baru $> 50$ item tertunda.
10. Insiden penolakan otentikasi login berturut-turut $> 10$ kali (indikasi *brute-force*).

---

## 4. Rencana Rilis Bertahap (Magang Scope)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ROADMAP RILIS BERTAHAP (3 FASE)                                 │
├────────────────────────────────┬───────────────────────────────┬───────────────────────┤
│ FASE 1: Fondasi & Akuisisi     │ FASE 2: Dashboard Analitik    │ FASE 3: RAG & Evaluasi│
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ • Ekstensi Browser MV3         │ • 9 Grafik Analitik Visual    │ • RAG Fail-Open Aktif │
│ • Client-First Capture SHA-256 │ • Filter & Drill-down Tiket   │ • Evaluasi Buta Dual  │
│ • Verifikasi Hash di Worker    │ • Ekspor DOCX & CSV Aman      │ • Pengujian Hipotesis │
│ • Antrean Validasi Dashboard   │ • Kurasi Entitas & Topik      │ • Go/No-Go Decision   │
│ • Deteksi Duplikat (pHash)     │ • Review Audit Hash-Chain     │ • Standardisasi Basis │
│ • KB Mode Bayangan (Shadow)    │ • Evaluasi Buta Baseline      │   Fase Ekspansi Lanjutan  │
└────────────────────────────────┴───────────────────────────────┴───────────────────────┘
```

### 4.1 Fase 1: Fondasi Data, Bukti, dan Keamanan
- **Fokus Scope**:
  1. Browser Extension MV3 (Chrome/Edge/Firefox) — capture tab aktif Full HD + DOM + SHA-256 di browser klien.
  2. Fallback server Playwright dalam kontainer `scraper` terisolasi.
  3. Re-verifikasi hash di worker backend (FR-03.2).
  4. Skema output AI 5W+1H (FR-04.1) dan isolasi input data boundary (FR-04.2).
  5. Antrean validasi Web Dashboard dengan tombol keputusan atomik dan kode alasan wajib.
  6. Deteksi duplikat berbasis URL kanonikal, SHA-256, dan perceptual hash (pHash).
  7. Modul OCR deterministik Tesseract.
  8. Modul RAG berjalan dalam mode bayangan (*shadow mode*, `RAG_ENABLED = False`).
  9. Audit log ber-hash-chain dengan jangkar eksternal harian.
  10. Otentikasi dashboard (Argon2id + 2FA TOTP bagi ADMIN).
  11. Topik terkontrol diinisialisasi berbasis 8 bidang IPOLEKSOSBUDHANKAM.
- **Gerbang Kelulusan Fase 1**:
  - Kriteria penerimaan AC-01 s.d. AC-05, AC-08 s.d. AC-13, AC-15 s.d. AC-22, AC-26, dan AC-28 s.d. AC-32 teruji lulus 100%.
  - Seluruh SLO operasional diukur selama 14 hari berturut-turut.
  - Nilai ambang batas RAG, pHash, dan sampling evaluasi buta terkalibrasi.

### 4.2 Fase 2: Dashboard Analitik & Tata Kelola
- **Fokus Scope**:
  1. Visualisasi 9 grafik analitik intelijen sosial pada Web Dashboard.
  2. Fitur penyaringan (*filter*) dan penelusuran mendalam (*drill-down*) laporan.
  3. Generator dokumen dinas resmi Microsoft Word (.docx) berstempel waktu dan ber-jangkar audit.
  4. Ekspor CSV aman dengan *escaping* formula anti-injeksi.
  5. Halaman konsol kesehatan sistem admin lengkap dengan 10 indikator alarm dini.
  6. Job batch normalisasi entitas dan kurasi topik IPOLEKSOSBUDHANKAM.
- **Gerbang Kelulusan Fase 2**:
  - Kriteria penerimaan AC-07, AC-14, AC-17, dan AC-25 teruji lulus 100%.
  - Uji pemulihan basis data (*restore test*) bulanan berhasil diverifikasi.
  - Review kepatuhan keamanan dashboard (OWASP ASVS Level 1).

### 4.3 Fase 3: Aktivasi RAG Penuh dengan Evaluasi Buta
- **Prasyarat Aktivasi**: Basis data Knowledge Base telah mengumpulkan $\ge 300$ entri tervalidasi aktif, dan setiap kategori dengan prevalensi $\ge 5\%$ memiliki minimal 20 entri preseden.
- **Fokus Scope**:
  1. Pengaktifan parameter `RAG_ENABLED = True`.
  2. Eksekusi evaluasi buta jalur ganda (Jalur A dengan RAG vs Jalur B tanpa RAG).
  3. Model fondasi, prompt instruksi, dan taksonomi dibekukan secara permanen selama pengujian.
  4. Pengujian kriteria penerimaan AC-06 dan AC-11 dengan modul RAG aktif.
- **Keputusan Go/No-Go**: Berdasarkan aturan keputusan pra-registrasi FR-13.5. Jika hasil evaluasi membuktikan RAG meningkatkan akurasi secara signifikan tanpa menambah salah vonis risiko tinggi, fitur dipertahankan permanen; jika tidak, fitur RAG dinonaktifkan otomatis.
- **Estimasi Durasi**: Dengan estimasi volume 100 tiket per hari, `EVAL_BLIND_RATE` 20%, dan 70% tiket memiliki rujukan preseden, terkumpul sekitar 14 pasangan data evaluasi per hari:
  - Margin $M = 7$ poin persentase ($\sim 320$ pasangan sampel): membutuhkan sekitar 23 hari kerja.
  - Margin $M = 5$ poin persentase ($\sim 620$ pasangan sampel): membutuhkan sekitar 44 hari kerja.

---

## 5. Asumsi dan 16 Keputusan Terbuka

| No | Parameter Keputusan | Rekomendasi Teknis Default | Pemilik Keputusan Akhir |
|---|---|---|---|
| 1 | **Model Embedding & Dimensi** | `gemini-embedding-001`, 768 dimensi, normalisasi L2. | Tim Teknis (Dikunci di Fase 1) |
| 2 | **Nilai $k$, Ambang Similarity, & pHash** | $k=5$; Ambang similarity $\ge 0.75$; Jarak pHash $\le 6$. | Tim Teknis setelah kalibrasi |
| 3 | **Mekanisme Otentikasi** | Username/Password (Argon2id) + 2FA TOTP ADMIN; SSO ditunda. | Kebijakan TI Instansi |
| 4 | **Cakupan Platform Media Sosial** | YouTube, TikTok, Instagram + Active-Tab Capture untuk X/Threads. | Pemilik Produk & Pembimbing |
| 5 | **Katalog Topik Awal** | 20–40 topik turunan dari 8 bidang IPOLEKSOSBUDHANKAM. | Analis Senior Dalinfo & ADMIN |
| 6 | **Akses Bukti Gambar di Dashboard** | Terbuka bagi ANALYST dan ADMIN; diunduh melalui token aman. | Pemilik Produk |
| 7 | **Penambahan Kategori Baru** | Dibekukan; tidak ditambah tanpa persetujuan tertulis resmi. | Pemangku Kepentingan Hukum |
| 8 | **Format KOP Dokumen Dinas** | Mengacu pada standar tata naskah dinas resmi instansi. | Pembimbing Lapangan |
| 9 | **Klasifikasi Data ke Gemini/Vertex AI** | Wajib menggunakan akun enterprise dengan jaminan tanpa pelatihan. | Pimpinan & Keamanan Informasi |
| 10 | **Periode Retensi Bukti Digital** | Mengikuti peraturan retensi arsip dinas dan UU PDP (default 30 hari). | Pimpinan & Bagian Hukum |
| 11 | **Batas Anggaran Bulanan AI** | Ditetapkan batas kredit dari baseline operasional Fase 1. | Pemilik Produk |
| 12 | **Volume Tiket Harian Rata-rata** | Puluhan hingga ratusan tiket per hari; diukur riil di Fase 1. | Diukur pada Fase 1 |
| 13 | **Eksposur Jaringan Dashboard** | Terbatas pada jaringan intranet dinas / VPN instansi. | Keamanan Informasi & Jaringan |
| 14 | **Peramban Target Ekstensi** | Google Chrome, Microsoft Edge, Mozilla Firefox (MV3). | Tim Teknis |
| 15 | **Penyimpanan Token Ekstensi** | Chrome Storage aman terenkripsi (WebCrypto API). | Tim Teknis |
| 16 | **Integrasi Langsung ke Sistem Luar** | Ditunda; pertukaran data cukup menggunakan ekspor CSV & DOCX. | Pemilik Produk |

---

## 6. Rencana Pengembangan Lanjutan (Roadmap Ekspansi Sistem)

Rancangan arsitektur PRD v3.1 sengaja dibangun secara modular agar hasil implementasi operasional di lokus D22 siap dikembangkan lebih lanjut pada fase berikutnya tanpa perombakan arsitektur inti:

| Domain Fungsional | Pilar Keamanan Siber | Inti Kapabilitas Sistem | Modul Fondasi yang Siap |
|---|---|---|---|
| **Rekayasa Forensik Digital & Kripto** | Kriptografi & Bukti Digital | Akuisisi bukti web berstandar forensik, verifikasi hash seketika di peramban klien, dan rantai audit *hash-chain* kekal. | FR-01, FR-03, FR-08, AC-08, AC-20, AC-28. |
| **Kecerdasan Buatan (Multimodal RAG)** | AI Terukur & Teruji | Evaluasi buta multimodal RAG untuk triase konten dinamis dengan kontrol *Human-in-the-Loop*. | FR-04, FR-09, FR-13, AC-05, AC-06, AC-11, AC-19. |
| **Data & Intelijen Sosial** | Intelijen Data & Analitik | Resolusi entitas kanonikal, pemantauan isu strategis IPOLEKSOSBUDHANKAM, dan *content clustering*. | FR-06, FR-10, FR-11, AC-07, AC-25, AC-32. |

> **Komponen yang Ditunda ke Fase Pengembangan Lanjutan:**
> 1. Analisis sentimen, emosi, dan sarkasme otomatis tingkat lanjut.
> 2. Model proyeksi dan prediksi eskalasi konflik sosial berbasis machine learning.
> 3. *Hybrid search* (gabungan BM25 + pgvector + Reciprocal Rank Fusion / RRF).
> 4. AI Gateway *on-premise* menggunakan LiteLLM/vLLM dengan model lokal (*open-source* LLM).
> 5. Scraper *server-side* penuh untuk platform login-wall ketat.
> 6. Pengujian reliabilitas penilaian kedua (*Inter-rater reliability / Cohen's Kappa*) skala besar.
> 7. Aplikasi verifikator audit eksternal mandiri berbasis GUI untuk pimpinan.

---

## 7. Lampiran A — Keputusan Review yang Dipertahankan

| Usulan Alternatif | Keputusan Final | Rasional & Dasar Keputusan |
|---|---|---|
| **Telegram sebagai Pintu Masuk** | **Diganti** Browser Extension | Arahan Bang Zazal: 100% personel bekerja di browser dinas; tidak semua menggunakan Telegram di PC piket. |
| **Kartu Validasi Inline Telegram** | **Dipindah** ke Antrean Web Dashboard | Mengintegrasikan seluruh proses triase dan validasi ke satu layar monitor terpadu. |
| **Role VIEWER pada Tahap MVP** | **Ditunda** ke Rilis Pasca-MVP | Realistis diselesaikan oleh 3 orang tim magang; pimpinan cukup menerima laporan DOCX/CSV. |
| **Autentikasi 2FA via OTP Telegram** | **Ditolak** (Gunakan Standar RFC 6238 TOTP) | Akun Telegram yang disusupi pihak ketiga dapat meruntuhkan lapisan keamanan 2FA. |
| **Scraping Server-Side untuk Semua Platform** | **Dikurangi** Menjadi Mode Fallback | *Client-first capture* via ekstensi jauh lebih tahan terhadap login-wall dan bot protection. |
| **Hybrid Search (BM25 + Vektor) di MVP** | **Ditunda** ke Fase Pengembangan Lanjutan | Kompleksitas indeks ganda belum diperlukan pada volume data tahap awal. |
| **Analisis Sentimen & Emosi Otomatis** | **Ditunda** ke Fase Pengembangan Lanjutan | Memerlukan korpus anotasi bahasa daerah dan persetujuan taksonomi tersendiri. |
| **AI Gateway On-Premise (LiteLLM/vLLM) di MVP** | **Ditunda** ke Fase Pengembangan Lanjutan | Keterbatasan kartu grafis (GPU) server workstation dinas selama periode magang. |
| **Bidang IPOLEKSOSBUDHANKAM Dijadikan Kategori** | **Dipetakan** ke Katalog Topik Terkontrol | Menjaga konsistensi 6 kategori pelanggaran baku tanpa merusak skema basis data. |
| **Failover Otomatis Model Embedding** | **Ditolak** Keras | Ruang vektor antar-model embedding berbeda tidak kompatibel untuk perbandingan kemiripan. |
| **Menyimpan Narasi Buatan AI ke Knowledge Base** | **Ditolak** Keras | Mencegah model AI mengutip hasil halusinasinya sendiri secara berulang (*circular bias*). |
| **Indeks Vektor HNSW / IVFFlat di Awal** | **Ditunda** (Gunakan Exact Scan) | Pada volume data $< 100.000$ entri, *exact scan* memberikan akurasi 100% dengan latensi $< 500$ ms. |
| **Notifikasi Otomatis Lonjakan Isu Real-Time** | **Non-Goal** Resmi | Sangat rawan memicu alarm palsu (*false positive*) pada volume data patroli harian. |

---

## 8. Pernyataan Penutup & Rekomendasi Tindak Lanjut

Dokumen ini merupakan **DRAF FINAL PRD v3.1 (Field-Aligned Final)** yang telah mengintegrasikan secara harmonis:
- Disiplin produk, model ancaman, dan metodologi evaluasi buta dari **PRD v3 Dosen Pembimbing**.
- Kebutuhan operasional riil di ruangan penugasan dari **Notulensi Rapat D22 Dalinfo BSSN**.
- Arahan teknis workstation dinas dari **Bang Zazal** (Browser Extension, automatic screenshot ber-SHA-256, dan antrean validasi web).
- Usulan awal arsitektur dan sistem dari **PRD v2**.

**Langkah Tindak Lanjut Menjelang Sign-Off Resmi:**
1. Menyampaikan dokumen PRD v3.1 ini kepada Bang Zazal dan Pak Giri melalui grup WhatsApp koordinasi untuk review akhir.
2. Mengonfirmasi daftar rincian subtopik awal IPOLEKSOSBUDHANKAM bersama analis senior Dalinfo.
3. Memastikan kesepakatan klasifikasi data dinas terkait penggunaan API model AI berbayar.
4. Menetapkan masa retensi arsip bukti digital sesuai ketentuan tata kelola instansi dan UU PDP.
5. Mengonfirmasi format KOP surat dinas resmi untuk generator dokumen rekapitulasi harian (.docx).
6. Menetapkan batas ambang kredit anggaran bulanan API berdasarkan baseline pengukuran Fase 1.

Setiap perubahan ruang lingkup (*scope*) setelah dokumen ini disahkan wajib melalui persetujuan tertulis pemilik produk dan dicatat sebagai nomor revisi resmi berikutnya.

---

**Akhir Dokumen — PRD v3.1 Field-Aligned Final.**
