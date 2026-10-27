# PRD v3: Asisten Patroli Siber (RAG Terukur + Dashboard Analitik)

Dokumen Spesifikasi Produk, Model Ancaman, DFD, dan Arsitektur Sistem. Revisi dari PRD v2 (Oktober 2026).
Status: Draf untuk review pemilik produk. Tanggal: 27 Oktober 2026.
Proses: disusun lewat 10 ronde kritik independen oleh reviewer skeptis (read-only); skor ronde terakhir 8,5/10 tanpa temuan blocker/major, dan seluruh temuan minor ronde itu sudah diperbaiki. Jejak keputusan ada di Lampiran A.

---

## 0. Ringkasan Perubahan dari v2

Prinsip revisi: **keep it simple, efisien tapi efektif, kurangi risiko gagal.** Setiap fitur baru harus bisa diukur, bisa dimatikan, dan tidak boleh menghentikan triase jika gagal.

| Area | v2 | v3 | Alasan |
| --- | --- | --- | --- |
| Evaluasi RAG | Ditunda, di luar PRD | **Evaluasi buta (blind eval) bawaan** dengan kriteria lulus yang ditetapkan sebelum data dilihat (FR-13) | Tanpa ini klaim "AI makin pintar" tidak bisa dibuktikan, dan RAG bisa memperkuat kesalahan |
| Konteks RAG di prompt | Label, risiko, alasan AI, catatan | Hanya **keputusan analis** + cuplikan teks konten asli; **tidak ada teks buatan AI** (`ai_reasoning`, ringkasan AI, topik AI) | Mencegah AI "mengutip dirinya sendiri" dan mengurangi permukaan prompt injection |
| Catatan analis | Free-text wajib untuk Ubah/Tolak | **Kode alasan wajib** (tombol) + catatan opsional (wajib hanya bila `LAINNYA`) | Free-text wajib di Telegram memicu catatan asal-asalan; kode alasan menghasilkan data terstruktur |
| Koreksi topik/aktor/sumber | Sub-menu Telegram | **Dihapus dari Telegram**; koreksi lewat dashboard ADMIN | Mengurangi kompleksitas state percakapan bot |
| Topik | Free-text AI + normalisasi fuzzy | **Daftar topik terkontrol** dipilih AI; usulan topik hanya ditampilkan sebagai daftar frekuensi untuk ADMIN | Free-text menghasilkan ribuan variasi; antrian merge tidak akan terkejar |
| Aktor target | Semua nama tampil di dashboard | **Fail-closed**: nama hanya tampil jika entitas sudah disetujui ADMIN sebagai publik; individu privat tidak pernah masuk tabel entitas | UU PDP, perlindungan korban |
| Sumber konten | Seluruhnya ditebak AI | Dipisah: **akun pengunggah** (deterministik dari scrape) dan **media asal** (AI, mis. watermark) | Data yang sudah pasti tidak perlu ditebak |
| Duplikat | Tidak ditangani | **Deteksi duplikat** (URL kanonik, SHA-256, pHash) + `content_cluster_id` | Mencegah hitung ganda, kebocoran label saat retrieval, dan kerja ulang analis |
| Identitas | `patrol_users` + `dashboard_users` terpisah | **Satu tabel identitas** dengan role VIEWER baru | Satu sumber kebenaran, satu titik nonaktifkan akun |
| Sesi dashboard | JWT berumur pendek | **Sesi server-side di Redis** + TOTP wajib untuk ADMIN | Pencabutan instan, tanpa refresh token |
| Indeks vektor | HNSW/IVFFlat | **Exact scan** (tanpa indeks ANN) | Volume kecil; ANN + filter `is_active` bisa mengembalikan < k hasil |
| Teks OCR | Disebut, tanpa proses pembuat | **Langkah OCR deterministik** (Tesseract `ind+eng`) di worker | Embedding tidak boleh bergantung pada output AI |
| Frontend | Service `web` opsional | **Disajikan dari `app`** (Jinja2 + HTMX + Chart.js lokal) | Satu service lebih sedikit |
| Keamanan | NFR umum | **Model ancaman** (§1.8): SSRF scraper, poisoning KB, injection, kanal Telegram, insider | Celah terbesar v2 adalah SSRF lewat scraper |
| Integritas audit | Audit log biasa | **Hash-chain** + jangkar harian di luar sistem (DOCX rekap) | Audit di DB yang sama bisa ditulis ulang oleh pemegang DB |
| Operasional | Tidak diatur | **SLO, observabilitas, backup + uji restore, batas anggaran, migrasi v1** | Hal yang paling sering menggagalkan sistem di produksi |
| Rilis | Sekaligus | **3 fase dengan gerbang go/no-go** (§4) | RAG baru aktif setelah ada data dan bukti |

Yang tidak berubah: Dual Intake (link dan foto), scraper Playwright, SHA-256 dan Chain of Custody, Multi-Model Failover Gemini, HITL via Telegram, generator DOCX `/rekap_harian`, whitelist. Satu perubahan perilaku v1: manajemen whitelist dan perintah administratif lain pindah dari Telegram ke dashboard ADMIN ber-TOTP.

---

## 1. Product Requirement Document

### 1.1 Ringkasan Eksekutif

Asisten Patroli Siber mempercepat triase konten media sosial pada piket patroli siber. Petugas mengirim link atau file gambar lewat bot Telegram. Sistem mengambil bukti, menghitung SHA-256, lalu AI memberi klasifikasi **indikatif**. Keputusan tetap di tangan analis.

v3 menambahkan tiga kemampuan, masing-masing dengan pengaman:

1. **RAG dari keputusan analis.** Kasus serupa yang sudah diputuskan dipakai sebagai referensi bagi AI. RAG hanya diaktifkan permanen jika evaluasi buta menunjukkan RAG tidak memperburuk hasil (FR-13).
2. **Ekstraksi entitas.** Topik (dari daftar terkontrol), aktor target, dan media asal, untuk analitik agregat.
3. **Dashboard analitik** untuk pimpinan dan analis, dengan prinsip privasi fail-closed.

### 1.2 Masalah yang Diselesaikan

| No | Masalah | Solusi |
| --- | --- | --- |
| 1 | Konten dihapus sebelum dilaporkan | Screenshot Full HD dan metadata otomatis segera setelah link dikirim (target p95 ≤ 3 menit, §1.7) |
| 2 | Keabsahan bukti diragukan | SHA-256, chain of custody, audit hash-chain dengan jangkar eksternal |
| 3 | Link terblokir atau login-wall | Dual Intake (file gambar manual) |
| 4 | Kuota API AI habis | Multi-Model Failover dalam satu proyek berbayar, dengan batas anggaran |
| 5 | AI salah tafsir konteks lokal | HITL + RAG dari keputusan analis, **dibuktikan lewat evaluasi buta** |
| 6 | Rekap shift tidak seragam | Generator DOCX dinas |
| 7 | Tidak ada gambaran agregat | Dashboard topik, aktor publik, media asal, tren, platform, kategori, risiko |
| 8 | **(Baru)** Konten sama dilaporkan berulang | Deteksi duplikat, analis cukup konfirmasi |

### 1.3 Tujuan dan Non-Goals

**Tujuan v3:**

1. Triase lebih cepat dan konsisten tanpa mengurangi kendali analis.
2. Data keputusan analis terstruktur (kode alasan, entitas) sehingga dapat dianalisis dan dipakai ulang.
3. Bukti dan jejak audit yang dapat dipertanggungjawabkan.
4. Klaim kualitas AI yang didukung angka, bukan asumsi.

**Non-goals (eksplisit tidak dikerjakan di v3):**

1. Keputusan atau takedown otomatis tanpa analis.
2. Klaim "AI makin pintar" sebelum FR-13 menunjukkannya.
3. Fine-tuning model.
4. Alerting real-time atau deteksi lonjakan otomatis.
5. Platform di luar YouTube, TikTok, Instagram.
6. Kategori baru (mis. judi online, konten asusila) tanpa persetujuan tertulis pemangku kepentingan (lihat §5).
7. Analitik topik free-text.
8. Service frontend terpisah, aplikasi mobile, atau SSO (SSO ditunda sampai kebijakan instansi tersedia).
9. Profiling individu atau pemeringkatan aktor/sumber berdasarkan "kesalahan".
10. Pemakaian `skor_keyakinan` dari AI sebagai ambang keputusan (nilai ini tidak terkalibrasi; hanya ditampilkan sebagai informasi).

### 1.4 Profil Pengguna dan Role

Satu tabel identitas (`patrol_users`) untuk Telegram dan dashboard.

| Role | Telegram | Dashboard |
| --- | --- | --- |
| OPERATOR | Kirim link/file, `/status` tiket miliknya | Tidak ada akses |
| ANALYST | Hak OPERATOR + validasi, `/rekap_harian` | Grafik + drill-down (termasuk tautan konten), ekspor CSV, halaman penilaian kedua (FR-13.4) |
| ADMIN | Hak ANALYST (tanpa perintah administratif di Telegram) | Semua hak ANALYST + revisi keputusan, whitelist dan akun, KB, entitas, API key, verifikasi audit (bersama supervisor atau ADMIN kedua, FR-08.4), halaman kesehatan sistem |
| VIEWER (baru) | Tidak ada akses | Grafik agregat saja (tanpa tautan, tanpa bukti), ekspor CSV agregat. Pengguna VIEWER adalah pejabat internal yang berwenang; agregat tidak diklaim sebagai anonimisasi |

Pimpinan Piket/Supervisor menerima DOCX rekap dan dapat diberi role VIEWER.

Akses dashboard memerlukan `dashboard_enabled = true`, password, dan untuk ADMIN wajib TOTP.

### 1.5 Kebutuhan Fungsional

FR-01 sampai FR-08 dipertahankan dari v1 dengan perubahan berikut.

| FR | Status |
| --- | --- |
| FR-01 Dual Intake | Diperluas: FR-01.3 (file asli) |
| FR-02 Scraper Playwright | Diperluas: FR-02.7 (allowlist egress), FR-02.8 (batas kepercayaan) |
| FR-03 Kriptografi Forensik | Diperluas: FR-03.4 (hash di titik capture) |
| FR-04 Triase AI | Diperluas: FR-04.3 sampai FR-04.6 |
| FR-05 HITL | Diperluas: FR-05.3 sampai FR-05.5 |
| FR-06 Pelacakan Tiket | Diperluas: status `FAILED`, `MANUAL_FALLBACK`; atribut duplikat |
| FR-07 DOCX | Diperluas: FR-07.2 (jangkar audit) |
| FR-08 Keamanan dan Audit | Diperluas: FR-08.3 sampai FR-08.6 |

**FR-01.3 File asli.** Bot menganjurkan pengiriman gambar sebagai *file/dokumen* (bukan "foto") karena Telegram mengompresi foto. Gambar yang diterima sebagai foto tetap diterima, tetapi evidence diberi tanda `source_quality = TELEGRAM_COMPRESSED` dan ini tercantum di DOCX. Batas unggahan: 20 MB, tipe MIME diverifikasi dari isi file, batas piksel Pillow (`MAX_IMAGE_PIXELS`) aktif untuk mencegah decompression bomb.

**FR-02.7 Allowlist egress scraper.** Scraper hanya membuka URL navigasi utama yang domainnya cocok dengan allowlist platform (dicek ulang setelah setiap redirect). Sub-resource halaman (gambar, skrip CDN) boleh ke internet publik, tetapi koneksi ke alamat privat diblokir di level jaringan (§3.5). Browser berjalan di container terpisah.

**FR-02.8 Batas kepercayaan scraper.** Hasil dari `scraper` diperlakukan sebagai input tak tepercaya:

1. **Tanpa Celery di sisi scraper.** `scraper` adalah proses loop sederhana: `BRPOP` pekerjaan dari list `scrape:jobs`, kerjakan, `LPUSH` hasil (JSON) ke list `scrape:results` di `redis-scrape`. Proses kolektor di container `worker` (`scrape-collector`) mengambil hasil dengan `BRPOP`, memvalidasinya (butir 2–4), lalu memasukkan tugas lanjutan ke antrian Celery `default` di Redis utama. Tidak ada deserialisasi selain JSON; Celery di Redis utama juga dikunci ke JSON (`accept_content = ['json']`).
2. Worker membuat nonce acak per tiket, menyertakannya di pekerjaan scrape, dan menolak hasil yang nonce-nya tidak cocok.
3. Hasil divalidasi skema Pydantic (ukuran field dibatasi); path file wajib berada di `scratch/<ticket_id>/`, berupa file reguler (bukan symlink), dengan batas ukuran.
4. Worker hanya membaca file gambar hasil scrape lewat Pillow (batas FR-01.3) dan Tesseract. OCR dijalankan sebagai subprocess terpisah tanpa variabel environment kredensial, dengan batas waktu dan memori.
5. Nonce mencegah tercampurnya atau diputarnya ulang hasil antar-tiket, tetapi **tidak** melindungi dari scraper yang sudah dibobol (ia melihat nonce). Pertahanan untuk kasus itu adalah satu proses per tugas dan recreate container harian.

**FR-03.4 Hash di titik capture.** SHA-256 dihitung saat file pertama kali ditulis: oleh `scraper` ke volume `scratch/<ticket_id>/`, atau oleh handler unggahan di `app` ke volume `incoming/<ticket_id>/`. Worker lalu memverifikasi ulang sebelum mencatat ke `evidences`. Ketidakcocokan = tiket `FAILED` + audit `EVIDENCE_HASH_MISMATCH`.

**FR-04.3 Output AI diperluas.** Skema Pydantic `AIPatrolAnalysis` ditambah:

| Field | Tipe | Keterangan |
| --- | --- | --- |
| topik\_kode | Enum dinamis | Kode dari daftar topik terkontrol aktif (disisipkan ke prompt), atau `LAINNYA` |
| topik\_usulan | String, maks 80 karakter, nullable | Diisi hanya bila `topik_kode = LAINNYA` |
| aktor\_target | List[{nama: String, jenis: Enum}] | `jenis`: TOKOH\_PUBLIK, INSTITUSI, KELOMPOK, INDIVIDU\_PRIVAT. Boleh kosong, maks 5 |
| media\_asal | String, nullable | Media/kanal asal yang terlihat pada konten (watermark, logo, sebutan di caption), mis. "Tribunnews". Null bila tidak terlihat |
| tipe\_media\_asal | Enum, nullable | MEDIA\_ONLINE, MEDIA\_TV, KOMUNITAS, LAINNYA |

Field lama tetap. **Akun pengunggah tidak ditebak AI**: untuk jalur link diambil dari `accounts` (hasil scrape); untuk jalur file tidak diisi.

Nilai enum yang berlaku (taksonomi versi `v3.0`, dikelola di `config_taxonomy`):

- `kategori_utama` (output AI **dan** keputusan analis): HOAKS, UJARAN\_KEBENCIAN, PROVOKASI\_SARA, PENIPUAN\_FINANSIAL, DI\_LUAR\_KONTEKS, `BUKAN_PELANGGARAN`. AI wajib memilih `BUKAN_PELANGGARAN` bila tidak menemukan pelanggaran; field lama `indikasi_pelanggaran` harus konsisten dengannya (divalidasi Pydantic). Taksonomi ini **dibekukan selama masa berlaku v3**; perubahan kategori = rilis baru dengan rencana pelabelan ulang KB.
- `tingkat_risiko`: RENDAH, SEDANG, TINGGI untuk pelanggaran; **NULL** bila `kategori_utama = BUKAN_PELANGGARAN` (berlaku untuk output AI dan keputusan analis). Perbandingan risiko AI vs analis hanya dilakukan bila keduanya pelanggaran.

**FR-04.4 Analisis dengan konteks RAG.** Bila RAG aktif (FR-09.8), sistem menjalankan retrieval (FR-09.4) dan menyisipkan hasilnya ke prompt sebagai blok referensi. Pengecualian: jalur B evaluasi buta (FR-13.2) selalu tanpa RAG. Ketentuan:

1. Blok referensi hanya berisi: cuplikan teks konten asli (judul/caption/OCR, maks 280 karakter, di dalam blok data berpembatas), kategori final, risiko final, kode alasan, dan catatan analis (maks 300 karakter).
2. **Tidak ada teks buatan AI** yang disisipkan: `ai_reasoning`, ringkasan narasi AI, dan topik pilihan AI tidak dipakai sebagai referensi.
3. Prompt menyatakan referensi bersifat contoh, bukan kebenaran, dan konten dinilai berdasarkan isinya sendiri.
4. Bila KB kosong, tidak ada hasil di atas ambang, atau retrieval gagal: analisis berjalan tanpa konteks (perilaku v1), dicatat di `rag_mode`.

**FR-04.5 Isolasi input tak tepercaya.** Judul, caption, teks OCR, nama akun, dan teks di dalam gambar diperlakukan sebagai data. Prompt membungkusnya dengan pembatas eksplisit dan instruksi bahwa isinya tidak boleh diikuti sebagai perintah. Output divalidasi Pydantic strict; output yang gagal validasi diulang 1x, lalu failover model. Risiko residual diterima karena HITL adalah kontrol akhir (lihat T3 di §1.8).

**FR-04.6 Jejak model.** Setiap laporan mencatat `ai_model_id` (versi model yang benar-benar menjawab), `prompt_version`, `rag_mode`, `rag_context` (daftar `entry_id` + skor), dan biaya token. Temperatur generasi rendah dan tetap (konfigurasi).

**FR-05.3 Tombol keputusan dan kode alasan.** Prinsip: **status selalu diturunkan dari `final_label`** di semua mode. `final_label = BUKAN_PELANGGARAN` → REJECTED; selain itu VALIDATED (sama dengan label AI) atau MODIFIED (berbeda dari label AI, mode NORMAL). Kode alasan wajib bila dan hanya bila keputusan analis berbeda dari output AI.

| Output AI | Tombol di kartu | Hasil | Kode alasan |
| --- | --- | --- | --- |
| Pelanggaran (kategori X) | Setuju | X, status VALIDATED | Tidak |
| Pelanggaran (kategori X) | Ubah Kategori/Risiko | Kategori/risiko baru, status MODIFIED | Wajib |
| Pelanggaran (kategori X) | Bukan Pelanggaran | `BUKAN_PELANGGARAN`, status REJECTED | Wajib |
| `BUKAN_PELANGGARAN` | Setuju (bukan pelanggaran) | `BUKAN_PELANGGARAN`, status REJECTED | Tidak |
| `BUKAN_PELANGGARAN` | Ini pelanggaran | Pilih kategori + risiko, status MODIFIED | Wajib |

Perubahan risiko saja dengan kategori sama juga MODIFIED. Catatan selalu opsional.

Kode alasan awal (dapat dikonfigurasi, berversi): `SATIRE_ATAU_HUMOR`, `FAKTA_TERVERIFIKASI`, `KONTEKS_TIDAK_TERBACA_AI`, `SALAH_KATEGORI`, `RISIKO_TERLALU_TINGGI`, `RISIKO_TERLALU_RENDAH`, `KONTEN_TIDAK_RELEVAN`, `LAINNYA`. Catatan free-text wajib hanya bila kode = `LAINNYA`. Untuk `LAINNYA`, keputusan **baru disimpan (commit atomik) setelah catatan diterima**; sebelum itu pilihan analis hanya disimpan sementara di Redis. Bila catatan tidak datang dalam 10 menit, pilihan sementara dibuang, kartu tetap `WAITING_VALIDATION`, dan analis diingatkan. Untuk kode lain, keputusan langsung disimpan dan catatan opsional dapat ditambahkan satu kali dalam 10 menit setelah keputusan; setelah itu jendela catatan ditutup dan entri KB ditulis (FR-09.1).

**FR-05.3a Mode keputusan.** Setiap keputusan mencatat `decision_mode`:

| Mode | Kapan | Kode alasan | Pemetaan status |
| --- | --- | --- | --- |
| NORMAL | Kartu biasa | Sesuai tabel FR-05.3 | Sesuai tabel FR-05.3 |
| BLIND | Tiket evaluasi buta (FR-13) | Tidak diminta (NULL) | Pelanggaran = VALIDATED, `BUKAN_PELANGGARAN` = REJECTED |
| NO\_AI | AI tidak tersedia setelah semua failover | Tidak diminta (NULL) | Pelanggaran = VALIDATED, `BUKAN_PELANGGARAN` = REJECTED |
| DUPLICATE | Tombol "Sama dengan induk" | Tidak diminta | Status induk |

MODIFIED hanya diberikan oleh keputusan mode NORMAL; laporan DUPLICATE mewarisi status induk apa adanya, termasuk MODIFIED. Grafik 8 (ketidaksepakatan) hanya memakai mode NORMAL dan membandingkan **keputusan pertama** analis dengan output AI (lihat `original_decision`, §3.4), sehingga revisi tidak mengubah statistik ini.

**FR-05.4 Validasi atomik.** Transisi dari `WAITING_VALIDATION` dilakukan dengan update bersyarat (`... WHERE status = 'WAITING_VALIDATION'`). Klik kedua dari analis lain menerima pesan "sudah divalidasi oleh [nama] pukul [jam]". Kartu analis tidak lagi menampilkan tombol setelah divalidasi.

**FR-05.4a Topologi chat.** Semua kartu analis (NORMAL, BLIND, NO\_AI, DUPLICATE) dikirim ke **satu grup analis terdaftar**; siapa pun ANALYST di grup dapat memutuskan, dan FR-05.4 mencegah keputusan ganda. Notifikasi `/status` untuk OPERATOR dikirim lewat chat pribadi. Penilaian kedua untuk uji reliabilitas tidak memakai Telegram (FR-13.4).

**FR-05.5 Revisi keputusan (dashboard ADMIN).** Keputusan final hanya dapat diubah oleh ADMIN lewat halaman revisi di dashboard (dilindungi TOTP, FR-12.2), dengan keputusan baru + kode alasan wajib. Telegram tidak menyediakan perintah ADMIN yang mengubah data, karena akun Telegram yang dibobol tidak boleh cukup untuk mengubah keputusan atau whitelist (lihat T5). Revisi memperbarui keputusan berlaku di `reports`, memicu FR-09.7, dan dicatat `REPORT_REVISED`. Keputusan pertama tetap tersimpan di `original_decision`. Pemetaan status mengikuti FR-05.3/FR-05.3a. Untuk evaluasi FR-13 selalu dipakai **label buta asli** (`eval_runs`), bukan hasil revisi. Revisi pada laporan induk juga menerapkan keputusan baru ke laporan yang sebelumnya menyalin keputusan lewat "Sama dengan induk", masing-masing dengan audit sendiri.

**FR-06.3 Duplikat.**

1. **Jalur link:** URL kanonik yang sudah ada di `contents` → duplikat pasti. `duplicate_of` = laporan pertama untuk konten itu (sudah diputuskan atau belum).
2. **Jalur file:** SHA-256 identik → duplikat pasti. Jarak Hamming pHash ≤ ambang (default 6, dikalibrasi di Fase 1) → hanya **petunjuk** (`similar_to`) di kartu, tanpa status tambahan.
3. **Bukti tetap diambil dan di-hash.** Capture ulang punya nilai forensik (membuktikan konten masih ada pada waktu T).
4. Kartu analis menampilkan "Kemungkinan duplikat PS-xxxx" beserta keputusan induk (bila sudah ada) dan tombol tambahan **Sama dengan induk**. Pada kartu buta, petunjuk dan keputusan induk **tidak** ditampilkan agar penilaian tetap buta. Bila induk belum diputuskan, tombol ini nonaktif dan kartu menampilkan "Induk sedang diproses"; analis tetap boleh memutuskan sendiri.
5. **Sama dengan induk** menyalin keputusan induk dan menandai `is_duplicate = true`.
6. `content_cluster_id`: duplikat pasti (URL kanonik atau SHA-256 sama) **selalu** masuk cluster induk, apa pun keputusan analis. Petunjuk pHash masuk cluster induk hanya bila analis menekan **Sama dengan induk**; selain itu cluster sendiri.
7. **Satu entri KB per cluster:** entri KB ditulis oleh laporan pertama yang diputuskan dalam cluster; laporan berikutnya dalam cluster tidak menulis entri baru (kecuali lewat revisi ADMIN, FR-05.5 dan FR-09.7).
8. **Keputusan bertentangan:** bila laporan dalam cluster yang sama diputuskan berbeda (mis. induk belum diputuskan saat analis lain memutuskan sendiri), laporan diberi tanda `cluster_conflict`, muncul di halaman ADMIN, dan diselesaikan ADMIN lewat revisi (FR-05.5). Sampai diselesaikan, dashboard memakai keputusan laporan pertama yang diputuskan dalam cluster.
9. Dashboard menghitung satu cluster sekali (unit hitung default = konten unik, FR-11.1). Dipakai untuk mengecualikan diri sendiri saat retrieval.

**FR-07.2 Jangkar audit dan aksi administratif di DOCX.** Setiap DOCX `/rekap_harian` mencantumkan:

1. *Chain head* audit log (hash entri terakhir) dan jumlah entri hari itu. DOCX dikirim ke supervisor, sehingga salinan hash berada di luar sistem.
2. Daftar aksi administratif hari itu: penonaktifan entri KB, merge entitas, revisi keputusan, purge, dan perubahan akun. Ini menggantikan ringkasan mingguan terpisah.

**FR-08.3 Aksi audit tambahan.** `KB_ENTRY_CREATED`, `KB_ENTRY_DEACTIVATED`, `KB_ENTRY_SEEDED`, `KB_ENTRY_PURGED`, `ENTITY_APPROVED`, `ENTITY_MERGED`, `TOPIC_PROPOSED`, `REPORT_REVISED`, `BLIND_LABEL_RECORDED`, `EVIDENCE_HASH_MISMATCH`, `RAG_FAILED`, `BUDGET_THRESHOLD`, `DASHBOARD_LOGIN`, `DASHBOARD_LOGIN_FAILED`, `DASHBOARD_EXPORT`, `USER_MANAGED`.

**FR-08.4 Audit hash-chain.** Setiap baris `audit_logs` menyimpan `prev_hash` dan `row_hash = SHA-256(prev_hash || serialisasi kanonik baris)`. Penulisan audit diserialisasi (advisory lock). Verifikasi (halaman ADMIN di dashboard) menghitung ulang rantai dan membandingkannya dengan **hash jangkar dari salinan sah milik supervisor** (FR-08.6), bukan dari data di dalam sistem. Verifikasi dijalankan bersama supervisor atau oleh ADMIN kedua, bukan oleh ADMIN yang sedang diaudit.

**FR-08.6 Jangkar terjadwal.** Job terjadwal (`celery-beat`, pukul 23.55 WIB) mengirim jangkar berupa pasangan (`seq_no`, `row_hash`) entri terakhir dan jumlah entri hari itu langsung ke chat Telegram supervisor yang terdaftar (`SUPERVISOR_CHAT_IDS`), tidak bergantung pada `/rekap_harian`. Kegagalan kirim memicu alarm ADMIN dan dicoba ulang. Karena bot dapat mengedit atau menghapus pesannya sendiri, pesan bot **bukan** salinan yang aman. Balasan supervisor di chat pribadi juga tidak cukup, karena bot dapat menghapus pesan di chat pribadi dalam 48 jam. Salinan yang sah adalah catatan **di luar Telegram dan di luar sistem**: (a) supervisor menyalin (`seq_no`, `row_hash`) ke catatan miliknya sendiri (mis. buku log piket atau dokumen pribadi), minimal sekali per minggu, dan/atau (b) file DOCX rekap yang diunduh dan disimpan supervisor di luar sistem. Jendela manipulasi tak terdeteksi = sejak salinan sah terakhir (maksimal ±7 hari bila hanya balasan mingguan, ±24 jam bila DOCX diterima harian). Ini dicatat sebagai risiko residual.

**FR-08.5 Pemisahan hak DB.** Aplikasi (`app`, `worker`) terhubung dengan role DB non-pemilik yang tidak punya hak `ALTER`, `DROP`, `TRIGGER`, atau `UPDATE`/`DELETE` pada `audit_logs`. Migrasi berjalan dengan role pemilik terpisah yang kredensialnya tidak berada di container aplikasi.

Risiko residual yang diterima: pihak dengan hak pemilik/superuser DB dapat menulis ulang rantai setelah salinan sah terakhir (jendela maksimal ±7 hari, lebih pendek bila supervisor membalas atau menyimpan DOCX lebih sering; FR-08.6) dan menonaktifkan trigger. Hash-chain membuat manipulasi **terdeteksi** terhadap jangkar eksternal, bukan mustahil.

**FR-09 Knowledge Base RAG.**

- **FR-09.1 Penulisan.** Setiap keputusan final dari ANALYST/ADMIN yang merupakan keputusan pertama dalam cluster-nya (FR-06.3) membuat satu entri KB. Penulisan dijalankan setelah catatan opsional diterima atau jendela catatan 10 menit berakhir, sehingga catatan ikut tersimpan tanpa perlu mengubah entri (NFR-8).
- **FR-09.2 Isi entri.** `final_label` (kategori atau `BUKAN_PELANGGARAN`), `final_risk`, `reason_code`, `analyst_notes`, `decision_mode`, `ai_suggested` (true bila label final sama dengan label AI yang ditampilkan ke analis, yaitu Setuju pada mode NORMAL), `snippet_text` (cuplikan teks konten asli), `embed_text`, `embedding`, `embedding_model`, `taxonomy_version`, `content_cluster_id`, `decided_by`. Laporan REJECTED disimpan sebagai contoh negatif berlabel `BUKAN_PELANGGARAN`. `ai_suggested` dipakai untuk analisis stratifikasi di FR-13, tidak ditampilkan di prompt.
- **FR-09.3 Embedding.** Teks yang di-embed: judul + caption + teks OCR dari langkah OCR deterministik (proses 3.5). Tidak ada output AI di dalamnya, agar vektor merepresentasikan konten, bukan opini model. Bila teks kosong (mis. gambar tanpa tulisan), embedding tidak dibuat dan `rag_mode = NO_TEXT`. Model awal `gemini-embedding-001` dengan `output_dimensionality = 768`; vektor dinormalisasi L2 sebelum disimpan (wajib untuk dimensi terpotong). **Tidak ada failover model embedding**, karena vektor dari model berbeda tidak sebanding; kegagalan = `rag_mode = FAILED`. Ganti model = re-embed seluruh KB (job batch), dilacak lewat kolom `embedding_model`.
- **FR-09.4 Retrieval.** Embed teks kueri, exact scan cosine similarity atas entri `is_active = true` dengan `taxonomy_version` sama, kecualikan `content_cluster_id` yang sama, ambil top-k (default 5) di atas ambang.
- **FR-09.5 Kontrol kualitas.** ADMIN dapat menonaktifkan entri dengan kode alasan wajib. Entri nonaktif tidak ikut retrieval dan tidak dihapus. Penonaktifan tercantum di DOCX harian (FR-07.2).
- **FR-09.6 Cold start.** ADMIN dapat mengimpor entri awal dari kasus v1 yang ditinjau ulang (tidak otomatis; lihat §4.4).
- **FR-09.7 Satu entri aktif per cluster.** Revisi menonaktifkan entri aktif cluster dan membuat entri baru dalam satu transaksi.
- **FR-09.8 Saklar RAG.** `RAG_ENABLED` (konfigurasi). Default **mati** di Fase 1 dan 2; KB tetap ditulis (mode bayangan). Diaktifkan di Fase 3 sesuai gerbang §4.
- **FR-09.9 Kalibrasi ambang.** Ambang ditetapkan dari data, bukan tebakan (nilai 0,75 dari v2 tidak dipakai). Hitung distribusi similarity pasangan acak antar-konten (sampel ini mengandung sebagian pasangan yang sebenarnya berkaitan, sehingga hasilnya konservatif). Dengan N = jumlah entri aktif, ambang = persentil ke-(1 − 0,5/N) distribusi tersebut, sehingga rata-rata referensi "kebetulan mirip" per kueri ≤ 0,5. Ambang dibatasi tidak melebihi ambang near-duplicate dikurangi 0,05, agar RAG tidak menyusut menjadi pencari duplikat saja. Cakupan RAG (persentase tiket yang mendapat ≥ 1 referensi) dipantau; bila < 30%, ambang dan teks embedding ditinjau. Dihitung ulang bulanan karena N bertambah. Pada saat yang sama dihitung **ambang near-duplicate** (default 0,95, dikonfirmasi dengan contoh pasangan repost) untuk FR-13.3.

**FR-10 Entitas.**

- **FR-10.1 Topik terkontrol.** ADMIN mengelola daftar topik (awal 20 sampai 40 topik, berkode, berversi). AI memilih satu kode atau `LAINNYA` + usulan. Usulan hanya ditampilkan sebagai daftar frekuensi di halaman ADMIN; ADMIN dapat menambah topik baru secara manual (di luar jendela evaluasi FR-13.2). Tidak ada alur promosi otomatis.
- **FR-10.2 Aktor.** Nama aktor dinormalisasi (huruf kecil, hapus gelar dan tanda baca) lalu dicocokkan exact ke `entity_aliases`. Tidak cocok → entitas baru `PENDING_REVIEW`. ADMIN menyetujui atau menggabungkan secara manual; tidak ada pencocokan fuzzy di v3.
- **FR-10.3 Fail-closed privasi.** Aktor `INDIVIDU_PRIVAT` tidak dibuat sebagai entitas; namanya hanya tersimpan mentah di `reports.ai_actors_raw` (tunduk retensi §1.6). Di dashboard, aktor hanya tampil dengan nama bila entitas berstatus `APPROVED` dan jenisnya TOKOH\_PUBLIK, INSTITUSI, atau KELOMPOK. Sisanya tampil sebagai baris gabungan "Belum ditinjau (n)" atau "Individu privat (n)".
- **FR-10.4 Media asal (versi sederhana).** Tanpa alur persetujuan. Nama media dinormalisasi dan dicocokkan exact ke alias (ADMIN dapat menambah alias). Peringkat media asal hanya terlihat oleh ANALYST dan ADMIN, karena AI bisa saja menulis nama akun individu sebagai "media". Akun pengunggah tidak dijadikan entitas dashboard.

**FR-11 Dashboard Analitik.**

- **FR-11.1 Sumber dan unit hitung.** Laporan VALIDATED dan MODIFIED (setara `final_label ≠ BUKAN_PELANGGARAN`, FR-05.3), nilai **final**. Unit hitung default = konten unik (`content_cluster_id`), dengan opsi tampilan "jumlah laporan". Zona waktu agregasi Asia/Jakarta (WIB). Bila sumbu waktu = `posted_at`, laporan tanpa `posted_at` (jalur file) dikecualikan dan jumlahnya ditampilkan di keterangan grafik.
- **FR-11.2 Grafik.**

| No | Visual | Isi | Akses |
| --- | --- | --- | --- |
| 1 | Tren waktu | Temuan per hari/minggu/bulan | Semua |
| 2 | Per platform | YouTube, TikTok, Instagram | Semua |
| 3 | Per kategori | Taksonomi aktif | Semua |
| 4 | Tingkat risiko | Distribusi dan tren | Semua |
| 5 | Topik teratas | Top-N kode topik terkontrol | Semua |
| 6 | Aktor target teratas | Hanya entitas APPROVED publik (FR-10.3) | Semua |
| 7 | Media asal teratas | Nama ternormalisasi (FR-10.4) | ANALYST, ADMIN |
| 8 | Ketidaksepakatan AI-Analis | % Setuju/Ubah/Tolak per kategori AI, kode alasan terbanyak; hanya `decision_mode = NORMAL` | ANALYST, ADMIN |
| 9 | Evaluasi buta | Selama jendela evaluasi: hanya progres pengumpulan (jumlah pasangan, jumlah TINGGI, tingkat pengeluaran/kegagalan per jalur), **tanpa** Δ atau akurasi. Δ dan akurasi ditampilkan setelah analisis ukuran tetap dijalankan, lalu bulanan untuk pemantauan FR-13.6 | ADMIN |

Grafik 8 diberi keterangan bahwa angka ini adalah **tingkat ketidaksepakatan, bukan akurasi**, karena analis melihat output AI saat memutuskan.

- **FR-11.3 Filter.** Rentang tanggal, platform, kategori, risiko.
- **FR-11.4 Drill-down.** ANALYST dan ADMIN: daftar laporan (tiket, tautan, kategori final, tanggal). Bukti gambar: ADMIN saja. VIEWER tidak punya drill-down.
- **FR-11.5 Ekspor.** CSV dibuat di server dan dicatat di audit. VIEWER hanya dapat mengekspor agregat. Sel CSV yang diawali `=`, `+`, `-`, `@` di-escape (mencegah CSV injection). Unduh PNG memakai fitur klien Chart.js dan tidak diklaim teraudit.
- **FR-11.6 Pelabelan netral.** Grafik aktor dan media asal memuat keterangan bahwa angka adalah frekuensi kemunculan pada temuan yang disetujui analis, bukan penilaian kesalahan.

**FR-12 Autentikasi Dashboard.**

- **FR-12.1** Login username + password (argon2id). Sesi server-side di Redis, cookie `HttpOnly`, `Secure`, `SameSite=Strict`, token CSRF untuk semua request yang mengubah data. Timeout idle 30 menit, maks sesi 8 jam.
- **FR-12.2** TOTP (RFC 6238) wajib untuk ADMIN, opsional untuk role lain. OTP lewat Telegram **tidak** dipakai, karena akun Telegram yang dibobol akan sekaligus membobol faktor kedua.
- **FR-12.3** Rate limit login (mis. 5 gagal per 15 menit per akun dan per IP), lalu kunci sementara. Menonaktifkan akun langsung menghapus semua sesinya.
- **FR-12.4** ADMIN membuat, menonaktifkan, dan mengatur role akun. ADMIN tidak dapat menurunkan role atau menonaktifkan dirinya sendiri (mencegah terkunci tanpa admin).
- **FR-12.5 Bootstrap ADMIN pertama.** ADMIN pertama dibuat lewat perintah CLI di dalam container (`manage create-admin`), yang menampilkan URI/QR pendaftaran TOTP satu kali di terminal. Tidak ada jalur pendaftaran ADMIN lewat web atau Telegram. Reset TOTP ADMIN lain dilakukan oleh ADMIN berbeda dan dicatat di audit.

**FR-13 Evaluasi Buta RAG (baru).**

- **FR-13.1 Sampel buta.** Setelah cek duplikat (proses 3.3), tiket non-duplikat diundi acak (default 10%, `EVAL_BLIND_RATE`) menjadi `eval_blind`. Kartu buta dikirim segera setelah bukti tersimpan, tanpa menunggu AI (jalur AI berjalan di latar belakang). Kartu analis **tidak** menampilkan output AI. Analis langsung memilih kategori dan risiko, atau Bukan Pelanggaran (`decision_mode = BLIND`, FR-05.3a). Setelah keputusan tersimpan, kartu di grup hanya diperbarui menjadi "Tervalidasi oleh [nama]" tanpa label maupun output AI; label dan output AI dikirim ke pengambil keputusan lewat chat pribadi. `/status` dan dashboard tidak menampilkan output AI maupun referensi RAG untuk tiket buta sebelum diputuskan, dan menyembunyikan label serta output AI dari halaman Penilaian Kedua (FR-13.4).
- **FR-13.2 Dua jalur AI (Fase 3).** Untuk tiket buta, AI dijalankan dua kali: jalur A dengan RAG, jalur B tanpa RAG. Selama jendela evaluasi dibekukan (*frozen*): model generasi, model embedding, `prompt_version`, taksonomi, daftar topik, `RAG_THRESHOLD`, dan `RAG_TOP_K`. Kalibrasi ulang bulanan FR-09.9 ditunda sampai jendela selesai. Di gerbang Fase 1 dipastikan tanggal penghentian (*deprecation*) model yang dibekukan, menurut pengumuman penyedia, jatuh setelah perkiraan akhir jendela evaluasi. Bila penyedia tetap menghentikan model di tengah jendela, jendela dibatalkan dan dimulai ulang dengan model pengganti. Penanganan kegagalan per jalur (dicatat di `eval_runs`):
  - Model yang dibekukan tidak tersedia sementara → retry pada **model yang sama** dengan backoff hingga 30 menit. Jalur evaluasi tidak memakai failover ke model lain (operasional tiket tetap memakai failover normal).
  - Bila tetap tidak tersedia (`UNAVAILABLE`), pasangan dikeluarkan dari analisis; tingkat pengeluaran dilaporkan per jalur dan per risiko.
  - Penolakan model (`REFUSED`) atau output tidak valid setelah retry (`INVALID`) adalah perilaku model dan **dihitung salah**, karena penolakan cenderung terjadi pada konten berisiko tinggi.
  - Jika anggaran mencapai 100% (NFR-11), jalur ganda dijeda (undian buta dan label buta tetap berjalan). Biaya tambahan ≈ `EVAL_BLIND_RATE` × biaya AI (10–20%).
- **FR-13.3 Populasi dan kebocoran.**
  - Label buta ditulis ke KB seperti biasa. Retrieval untuk sebuah tiket hanya melihat entri yang ada sebelum tiket itu diputuskan dan selalu mengecualikan cluster-nya sendiri. Untuk tiket buta, jalur A juga mengecualikan entri dengan similarity ≥ ambang near-duplicate (FR-09.9) agar repost yang lolos dari cluster tidak membocorkan label.
  - **Populasi utama** = pasangan dengan `rag_mode = ON` pada jalur A (jalur A benar-benar menerima ≥ 1 referensi). Pasangan NO\_TEXT/EMPTY/FAILED identik di kedua jalur dan hanya mengencerkan selisih, sehingga dilaporkan terpisah sebagai cakupan RAG (persentase tiket yang mendapat referensi).
  - Analisis deskriptif tambahan (bukan input gerbang): stratifikasi menurut proporsi referensi `ai_suggested = true` dan menurut ada/tidaknya near-duplicate di KB.
  - Batasan yang diakui: karena near-duplicate dikecualikan, evaluasi **tidak** mengukur efek RAG yang paling kuat di produksi, yaitu menyalin label dari repost yang sangat mirip. Efek itu dipantau secara deskriptif lewat tingkat ketidaksepakatan (grafik 8) pada tiket dengan referensi near-duplicate.
- **FR-13.4 Reliabilitas label (penilaian kedua di dashboard).** Sampel tiket buta yang sudah diputuskan (60 pertama di Fase 1, lalu 20% tiket buta di Fase 3) masuk ke halaman **Penilaian Kedua** di dashboard. Analis lain (bukan pengambil keputusan pertama) menilai secara batch: hanya bukti dan metadata, tanpa label pertama dan tanpa output AI. Jawaban disimpan di `second_rater_label` dan tidak mengubah status. Selama tiket menunggu penilaian kedua (maks 7 hari), label pertama dan output AI-nya disembunyikan dari ANALYST di drill-down, `/status`, referensi RAG yang ditampilkan, dan DOCX `/rekap_harian` (ditampilkan sebagai "dalam penilaian kedua"), kecuali bagi penilai pertama. Penugasan: tiket di halaman Penilaian Kedua diklaim saat dibuka (update bersyarat satu kali; klaim kedaluwarsa setelah 24 jam tanpa jawaban). Kartu laporan duplikat dari tiket yang sedang menunggu penilaian kedua juga tidak menampilkan keputusan induk. Penilai kedua dapat melihat bukti gambar tiket yang ditugaskan kepadanya lewat endpoint khusus yang diaudit (pengecualian terbatas dari aturan bukti ADMIN-saja di FR-11.4). Label resmi tetap milik penilai pertama. Laporkan Cohen's kappa kategori beserta intervalnya; bila estimasi titik kappa < 0,6, definisi kategori dan kode alasan ditinjau sebelum Fase 3. Di Fase 3, Δ juga dilaporkan secara deskriptif pada subset yang kedua penilainya sepakat, karena noise label menarik Δ ke arah 0 dan menguntungkan kelulusan non-inferioritas.
- **FR-13.4a Ukuran sampel dan kelayakan (diputuskan di akhir Fase 1).** Satu analisis dengan ukuran sampel tetap (tanpa pemeriksaan antara, demi kesederhanaan). Ukuran sampel dihitung untuk power 80% saat Δ sebenarnya = 0 terhadap margin non-inferioritas M, dengan α satu sisi 0,05. Proporsi pasangan diskordan diasumsikan secara konservatif **25%** (ketidakstabilan antar-run yang diukur dengan menjalankan jalur tanpa RAG dua kali pada 50 tiket buta Fase 1 hanya dipakai bila lebih besar, karena angka ini meremehkan ketidaksepakatan RAG vs tanpa RAG). Gambaran: M = 5 pp memerlukan sekitar 620 pasangan; M = 7 pp sekitar 320 pasangan. Di akhir Fase 1, pemilik produk mengunci M (5 atau 7 pp) dan `EVAL_BLIND_RATE` (maks 20%) berdasarkan volume dan cakupan RAG yang terukur. Bila waktu yang dibutuhkan > 6 bulan, Fase 3 ditunda atau RAG tidak dilanjutkan.
- **FR-13.5 Aturan keputusan (pra-registrasi, dikunci di gerbang Fase 1).**
  - Metrik utama: Δ = akurasi(A) − akurasi(B) pada populasi utama, terhadap label buta. Label AI = `kategori_utama` (termasuk `BUKAN_PELANGGARAN`, FR-04.3).
  - Interval: interval skor Tango 90% untuk selisih proporsi berpasangan (setara uji satu sisi α 0,05).
  - Metrik keamanan: *miss* risiko tinggi = label buta TINGGI yang oleh AI diberi RENDAH atau `BUKAN_PELANGGARAN`. Uji tanda eksak satu sisi pada pasangan diskordan miss (miss hanya di A vs miss hanya di B). TINGGI → SEDANG dilaporkan terpisah.
  - Analisis dijalankan sekali saat ukuran sampel FR-13.4a tercapai **dan** populasi utama memuat ≥ 30 label buta TINGGI. Bila syarat TINGGI belum terpenuhi dalam batas 6 bulan, hasil = TIDAK MEYAKINKAN.
  - Urutan evaluasi aturan:
    1. **GAGAL** bila batas atas interval Δ < 0, **atau** uji tanda miss TINGGI p < 0,10 ke arah A lebih buruk, **atau** jumlah miss TINGGI yang hanya terjadi di A lebih banyak 3 atau lebih daripada yang hanya terjadi di B (aturan absolut, karena uji tanda baru bisa signifikan pada ≥ 4 pasangan diskordan). RAG dimatikan.
    2. **LULUS** bila tidak GAGAL **dan** batas bawah interval Δ ≥ −M (M dikunci di gerbang Fase 1). RAG dipertahankan.
    3. **TIDAK MEYAKINKAN** selain itu. RAG dimatikan (pilihan konservatif); evaluasi dapat diulang dengan sampel baru atas keputusan pemilik produk.
  - **Sebelum aturan dikunci** di gerbang Fase 1, karakteristik operasi aturan gabungan disimulasikan dengan parameter yang diusulkan (M, ukuran sampel, prevalensi TINGGI dan tingkat miss dari data Fase 1). Batas yang dapat diterima: P(LULUS | Δ = −M) ≤ 0,05, P(GAGAL | Δ = 0) ≤ 0,20, dan P(LULUS | Δ = 0) ≥ 0,70. Bila terlampaui, ambang aturan keamanan absolut atau ukuran sampel disesuaikan lalu disimulasikan ulang; versi akhir dikunci bersama hasil simulasinya.
  - Klaim "RAG meningkatkan akurasi" hanya boleh dibuat bila uji McNemar eksak memberi p < 0,05 ke arah jalur A.
  - Dalam semua hasil, KB tetap ditulis untuk evaluasi berikutnya.
- **FR-13.6 Pemantauan berkelanjutan.** Setelah gerbang dilewati, sampel buta tetap berjalan (default 5%) dengan dua jalur. Grafik 9 diperbarui bulanan. Alarm drift: uji McNemar eksak satu sisi pada 100 pasangan buta terakhir memberi p < 0,05 ke arah jalur A lebih buruk dari jalur B. Bila alarm berbunyi, ADMIN diberi notifikasi dan `RAG_ENABLED` dimatikan sampai evaluasi ulang. Tingkat alarm palsu aturan ini saat Δ = 0 ikut disimulasikan bersama FR-13.5. Pergantian model generasi atau embedding selalu memicu evaluasi ulang dengan aturan FR-13.5.
- **FR-13.7 Perhitungan teruji.** Fungsi penghitung metrik FR-13 diuji unit dengan data sintetis yang hasilnya diketahui (AC-19).

### 1.6 Persyaratan Non-Fungsional

| No | Area | Persyaratan |
| --- | --- | --- |
| 1 | Reliabilitas Telegram | Pool 16 koneksi, timeout 60s, Safe Reply/Safe Edit 3x retry (tetap) |
| 2 | Isolasi tugas | Playwright di service `scraper` terisolasi dengan Redis tersendiri; AI, OCR, dan embedding di `worker` |
| 3 | Penyimpanan | PostgreSQL 16 + pgvector, volume persisten |
| 4 | Retrieval | Exact scan cosine. Tinjau ulang (tambah indeks ANN) hanya bila KB > 100.000 entri atau p95 retrieval > 500 ms |
| 5 | Fail-open | Kegagalan embedding, retrieval, normalisasi entitas, atau penulisan KB tidak menghentikan triase atau validasi; dicatat (`RAG_FAILED`) dan dicoba ulang lewat antrian |
| 6 | Keamanan dashboard | TLS, sesi server-side, CSRF, rate limit, CSP ketat (tanpa CDN; aset lokal), secrets lewat environment/secret store, tidak di source code |
| 7 | Privasi | Agregat di grafik; nama hanya untuk entitas publik yang disetujui; akun pengunggah tidak tampil di grafik; minimisasi data di prompt (bio akun tidak dikirim ke AI) |
| 8 | Integritas KB | Isi entri tidak diedit (ditegakkan di DB: trigger menolak `UPDATE` selain kolom deaktivasi, kecuali dari role pemilik fungsi purge). Pengecualian satu-satunya: purge sesuai retensi (NFR-9), yang hanya dapat dilakukan lewat fungsi DB `purge_report()` (SECURITY DEFINER, milik role pemilik) |
| 9 | Retensi dan UU PDP | Periode retensi laporan, bukti, KB, dan nama mentah ditetapkan instansi (§5). Purge menghapus isi konten dan nama, menyisakan *tombstone* (ID, hash, waktu). Data yang dipurge masih ada di backup hingga backup tersebut kedaluwarsa (maks 30 hari, NFR-12); ini dicatat sebagai risiko residual. Baris `audit_logs` hanya berisi ID, kode aksi, hash, dan metadata non-pribadi (tanpa teks konten atau nama), sehingga purge tidak menyentuh rantai audit. Purge terjadwal berjalan otomatis sesuai retensi; purge di luar jadwal oleh ADMIN wajib disertai alasan dan tercantum di DOCX harian ke supervisor |
| 10 | Pemrosesan data AI | Hanya Gemini berbayar atau Vertex AI dengan region ditetapkan dan ketentuan tidak memakai data untuk pelatihan. Tidak ada rotasi banyak akun/key untuk menghindari kuota. Klasifikasi data dan persetujuan pimpinan didokumentasikan sebelum produksi |
| 11 | Anggaran | Batas biaya bulanan. Pada 80%: notifikasi ADMIN. Pada 100%: triase tetap jalan dengan model termurah dalam daftar failover; embedding dan jalur ganda evaluasi dijeda (undian dan label buta tetap berjalan) |
| 12 | Backup | Harian (service `backup`, §3.5): `pg_dump` + sinkronisasi folder bukti ke penyimpanan terpisah, terenkripsi, retensi 30 hari. Uji restore bulanan yang memverifikasi ulang SHA-256 semua bukti terhadap `evidences` |
| 13 | Observabilitas | Log terstruktur JSON. Halaman "Kesehatan Sistem" ADMIN (§3.8). Notifikasi Telegram ke grup ADMIN untuk kondisi alarm |
| 14 | Kanal Telegram | Token bot hanya ada di `app`; satu proses polling. Komponen lain (worker, celery-beat) mengirim pesan dengan menulis ke tabel `outbox`, yang dikirim oleh `app` dengan Safe Reply dan retry. Bot hanya melayani chat pribadi dan grup yang terdaftar. Whitelist dicek per pesan. Prosedur rotasi token bot. Diakui bahwa chat bot tidak terenkripsi end-to-end (lihat T5) |

### 1.7 Target Layanan (SLO) dan Metrik Keberhasilan

Target awal; angka dikonfirmasi setelah 2 minggu pengukuran Fase 1.

| Metrik | Target |
| --- | --- |
| Waktu kirim link sampai kartu analis (p95) | ≤ 3 menit |
| Waktu kirim file sampai kartu analis (p95) | ≤ 90 detik |
| Keberhasilan scrape otomatis per platform (7 hari bergulir) | ≥ 85% (di bawah 70% = alarm) |
| Ketersediaan bot pada jam piket | ≥ 99% |
| Validasi gagal karena race condition | 0 |
| Query dashboard (p95, data 12 bulan) | ≤ 2 detik |
| Presisi petunjuk duplikat pHash (dikonfirmasi analis lewat "Sama dengan induk") | ≥ 90% |
| Antrian review entitas ADMIN | < 50 item tertunda |
| Biaya per tiket | Dipantau; baseline ditetapkan di Fase 1 |
| Kualitas AI | Diukur hanya lewat FR-13 |

### 1.8 Model Ancaman (Ringkas)

| ID | Ancaman | Dampak | Mitigasi |
| --- | --- | --- | --- |
| T1 | **SSRF lewat scraper** atau **eksploitasi browser** oleh halaman berbahaya | Kebocoran data internal, pivot jaringan, serangan balik ke worker | Allowlist navigasi (FR-02.7); aturan firewall `scraper` hanya mengizinkan `redis-scrape:6379`, resolver DNS yang ditetapkan, dan internet publik (§3.5); `scraper` tidak memegang kredensial DB atau API key; Redis tersendiri; hasil scrape diperlakukan tak tepercaya: JSON saja, nonce per tiket, validasi path dan skema (FR-02.8). Risiko residual: eksploit yang bertahan di container `scraper` dapat memalsukan bukti tiket apa pun yang diproses sampai container di-recreate (maks ±24 jam), serta mencoba eksploit terautentikasi terhadap `redis-scrape` (dibatasi ACL dan jaringan `scrape_net`) |
| T2 | **Poisoning KB** oleh analis (sengaja atau keliru) | AI terarah ke label salah | Evaluasi buta berkelanjutan (FR-13.6) mendeteksi penurunan kualitas; penonaktifan entri oleh ADMIN dengan alasan; aksi administratif tercantum di DOCX harian. Risiko residual: dengan 2–3 analis, poisoning yang konsisten oleh satu analis hanya terdeteksi lewat metrik, tidak dicegah |
| T3 | **Prompt injection** lewat caption, OCR, teks dalam gambar, atau ringkasan di KB | Label/risiko dimanipulasi | Isolasi input (FR-04.5); KB hanya menyuntikkan keputusan analis dan cuplikan teks asli berpembatas (tanpa teks buatan AI); validasi skema; HITL. Uji: 20 kasus injection dalam acceptance test |
| T4 | **Pemalsuan atau penyangkalan bukti** | Bukti ditolak dalam proses hukum | Hash di titik capture lalu diverifikasi worker (FR-03.4) mendeteksi kerusakan/perubahan **setelah** capture; file asli (FR-01.3); hash bukti masuk audit hash-chain dengan jangkar eksternal (FR-08.4); `ai_model_id` tercatat. Batasan: scraper yang sudah dibobol dapat menulis file dan hash palsu sekaligus; mitigasinya adalah isolasi T1, bukan hash. Opsi lanjutan: timestamp RFC 3161 |
| T5 | **Paparan via Telegram**: server pihak ketiga, akun petugas dibobol, grup tak terkelola | Kebocoran bukti; intake palsu; keputusan palsu | Whitelist per pesan; tidak ada perintah administratif di Telegram (revisi, whitelist, audit hanya di dashboard ber-TOTP, FR-05.5); akun analis yang dibobol tetap dapat memberi keputusan palsu, terdeteksi lewat audit dan revisi; rotasi token; keputusan klasifikasi data (§5) |
| T6 | **Penyalahgunaan oleh ADMIN** (hapus jejak, nonaktifkan entri tanpa dasar) | Integritas hilang | Audit hash-chain + jangkar di salinan supervisor (FR-08.4); pemisahan hak DB (FR-08.5); semua aksi administratif tercantum di DOCX harian. Risiko residual: pemegang hak pemilik DB dapat menulis ulang rantai setelah jangkar terakhir; ini terdeteksi, tidak dicegah |
| T7 | **File berbahaya** (decompression bomb, file palsu) | Worker crash/DoS | Batas ukuran dan piksel, verifikasi MIME dari isi, pemrosesan di worker dengan batas memori |
| T8 | **Pengambilalihan sesi dashboard** | Akses data | Sesi server-side, CSRF, CSP, TOTP ADMIN, rate limit |

### 1.9 Kriteria Penerimaan (Acceptance Criteria)

| ID | Kriteria |
| --- | --- |
| AC-01 | URL ke host internal (mis. `http://10.0.0.5`, `http://169.254.169.254`, domain non-platform, redirect ke host internal) ditolak dan dicatat; tidak ada request keluar dari `scraper` ke jaringan internal (diuji dari dalam container) |
| AC-02 | Dua analis menekan tombol pada kartu yang sama dalam < 1 detik: tepat satu keputusan tersimpan, analis kedua menerima pemberitahuan |
| AC-03 | Ubah/Tolak tanpa kode alasan tidak dapat disimpan; `LAINNYA` tanpa catatan tidak dapat disimpan |
| AC-04 | Link yang sama dikirim dua kali: tiket kedua punya `duplicate_of`, bukti baru tetap di-hash, dashboard menghitung 1 konten unik |
| AC-05 | Retrieval tidak pernah mengembalikan entri dari `content_cluster_id` yang sama atau entri `is_active = false` (uji otomatis) |
| AC-06 | Embedding API dimatikan (simulasi): tiket tetap sampai ke kartu analis dengan `rag_mode = FAILED` |
| AC-07 | Nama aktor `INDIVIDU_PRIVAT` atau entitas `PENDING_REVIEW` tidak muncul di grafik, ekspor CSV, maupun respons API dashboard; VIEWER menerima 403 untuk peringkat media asal dan drill-down; CSV VIEWER hanya berisi agregat grafik 1–6 |
| AC-08 | (a) Mengubah satu baris `audit_logs` langsung di DB terdeteksi verifikasi; (b) mengubah satu baris yang `seq_no`-nya ≤ jangkar terakhir milik supervisor, lalu menghitung ulang seluruh hash sesudahnya (rantai konsisten secara internal), tetap terdeteksi saat dibandingkan dengan jangkar tersebut. Perubahan setelah jangkar terakhir memang tidak terdeteksi (risiko residual FR-08.5/FR-08.6) |
| AC-09 | Tiket `eval_blind`: kartu tidak memuat kategori, risiko, narasi, atau alasan AI sebelum keputusan; keputusan tersimpan dengan `decision_mode = BLIND` |
| AC-10 | Akun dinonaktifkan: sesi aktif hilang dalam ≤ 5 detik; ADMIN tanpa TOTP tidak bisa login |
| AC-11 | 20 kasus uji prompt injection, masing-masing dijalankan 3 kali dan dibandingkan dengan versi bersih (tanpa teks injeksi, juga 3 kali) dari konten yang sama; kasus dihitung "berhasil diinjeksi" bila label mayoritas berbeda dari label mayoritas versi bersih: maks 1 dari 20 kasus, dan setiap perubahan ditinjau serta prompt diperbaiki sebelum lanjut fase |
| AC-12 | Uji restore: database dan bukti dipulihkan ke lingkungan bersih, seluruh hash bukti cocok |
| AC-13 | UPDATE isi `knowledge_entries` ditolak oleh DB |
| AC-14 | Sel CSV berawalan `=`, `+`, `-`, `@` ter-escape |
| AC-15 | Unggahan decompression bomb dan file dengan ekstensi palsu ditolak tanpa worker crash |
| AC-16 | Dua file gambar yang sama dengan kompresi berbeda menghasilkan petunjuk `similar_to`; tanpa "Sama dengan induk", laporan kedua memiliki cluster sendiri |
| AC-17 | Revisi oleh ADMIN di dashboard (termasuk pada laporan BLIND, NO\_AI, DUPLICATE): status final berubah, baris `report_revisions` dengan kode alasan tercipta, `original_decision` tidak berubah, entri KB lama nonaktif dan entri baru aktif dalam satu transaksi; non-ADMIN ditolak |
| AC-18 | Simulasi anggaran 100%: triase tetap berjalan dengan model termurah, embedding dan jalur ganda evaluasi dijeda, audit `BUDGET_THRESHOLD` tercatat |
| AC-19 | Uji unit metrik FR-13 dengan data sintetis: Δ, interval skor Tango 90%, McNemar eksak, uji tanda miss TINGGI, dan aturan GAGAL/LULUS/TIDAK MEYAKINKAN sesuai nilai yang dihitung manual |
| AC-20 | Role DB aplikasi tidak dapat menjalankan `ALTER TABLE`, `DISABLE TRIGGER`, atau `UPDATE` pada `audit_logs` |
| AC-21 | Dari dalam container `scraper`, koneksi ke `db`, `redis` (sesi), alamat RFC1918/link-local, dan IPv6 gagal, sementara `redis-scrape` dan situs platform publik berhasil |
| AC-22 | Hasil scrape dengan nonce salah, path di luar `scratch/<ticket_id>/`, symlink, atau payload non-JSON ditolak `scrape-collector` dan dicatat di audit; user `scraper` di `redis-scrape` gagal menjalankan perintah selain yang diizinkan ACL |
| AC-23 | Job jangkar terkirim ke chat supervisor tanpa `/rekap_harian` dijalankan; kegagalan kirim memicu alarm; verifikasi berhasil memakai hash dari balasan supervisor |
| AC-24 | `POST /api/v1/patrol` tanpa API key valid atau dari luar jaringan internal ditolak; API key yang dicabut langsung tidak berlaku |
| AC-25 | Duplikat pasti yang diputuskan berbeda dari induknya ditandai `cluster_conflict`, tidak menulis entri KB kedua, dan dashboard tetap menghitung cluster sekali |
| AC-26 | Dari `app` dan `worker`, koneksi keluar ke domain di luar allowlist proxy gagal; koneksi ke `api.telegram.org` (app) dan endpoint Gemini (worker) berhasil |
| AC-27 | Untuk tiket yang menunggu penilaian kedua: label pertama dan output AI tidak terlihat oleh ANALYST lain di drill-down, `/status`, referensi RAG, DOCX, maupun kartu duplikat; dua penilai tidak dapat mengklaim tiket yang sama |

---

## 2. Data Flow Diagram

### 2.1 DFD Level 0

**Entitas eksternal:** (1) Petugas/Analis via Telegram, (2) Pengguna Dashboard (VIEWER, ANALYST, ADMIN), (3) Platform Media Sosial, (4) Google Gemini (generasi dan embedding), (5) **Supervisor** (penerima DOCX berisi jangkar audit dan aksi administratif harian; menyimpan salinan di luar sistem).

| Dari | Ke | Data |
| --- | --- | --- |
| Petugas/Analis | Sistem | URL, file bukti, keputusan, kode alasan, catatan, perintah |
| Sistem | Petugas/Analis | Kartu analis, status tiket, notifikasi |
| Pengguna Dashboard | Sistem | Kredensial + TOTP, filter, ekspor, aksi admin |
| Sistem | Pengguna Dashboard | Grafik, daftar laporan, CSV |
| Sistem | Platform | Request scraping (hanya domain allowlist) |
| Platform | Sistem | Halaman, metadata, media |
| Sistem | Gemini | Prompt (input dibungkus pembatas), gambar bukti, konteks RAG terbatas, teks untuk embedding |
| Gemini | Sistem | JSON triase, vektor embedding |
| Sistem | Supervisor | DOCX rekap + aksi administratif; pesan jangkar audit harian (terjadwal) |
| Supervisor | Sistem | Hash jangkar dari salinan DOCX saat verifikasi audit |

### 2.2 DFD Level 1

**Data store:**

| ID | Nama | Isi |
| --- | --- | --- |
| D1 | patrol\_users | Identitas tunggal: Telegram + dashboard, role, TOTP |
| D2 | accounts | Profil akun media sosial |
| D3 | contents | Metadata postingan |
| D4 | evidences | Path bukti, SHA-256, pHash, kualitas sumber |
| D5 | reports | Tiket, output AI, jejak model, keputusan, duplikat, eval |
| D6 | audit\_logs | Jejak forensik hash-chain |
| D7 | File Storage | evidences/, reports/ |
| D8 | knowledge\_entries | KB RAG |
| D9 | entities, entity\_aliases, topics | Entitas, alias, topik terkontrol |
| D10 | config\_taxonomy | Kategori, kode alasan, versi |
| D11 | Redis (`redis`) | Antrian `default`, sesi dashboard, pilihan sementara FR-05.3 |
| D12 | Redis (`redis-scrape`) | List `scrape:jobs` dan `scrape:results` saja (batas kepercayaan, §3.5) |

**Proses:**

| No | Proses | Input | Output |
| --- | --- | --- | --- |
| 1.0 | Validasi dan Intake | URL/file, D1 | Tiket |
| 2.0 | Capture Bukti (service `scraper`) | Tiket | PNG + hash awal, metadata |
| 3.0 | Verifikasi Hash, Simpan, Cek Duplikat, OCR, Undian Buta | PNG, metadata | D2, D3, D4, D7, `duplicate_of`, `ocr_text`, `eval_blind` |
| 4.0 | Retrieval RAG (jika aktif) | Teks konten | Referensi dari D8 |
| 5.0 | Triase AI | Bukti + metadata + referensi | D5, D6 |
| 6.0 | Validasi Analis (normal/buta/duplikat) | Kartu, tombol, kode alasan | D5, D6 |
| 7.0 | Penulisan KB dan Normalisasi Entitas (asinkron, fail-open) | Keputusan final | D8, D9, D6 |
| 8.0 | Query Status | `/status` | Rincian tiket |
| 9.0 | Rekap DOCX + Jangkar Audit | `/rekap_harian` | DOCX ke D7, Supervisor |
| 10.0 | Dashboard Analitik | Filter | Grafik dari D5, D9 |
| 11.0 | Administrasi | Aksi ADMIN | D1, D8, D9, D10, D6 |
| 12.0 | Evaluasi Buta | Tiket `eval_blind` | Dua output AI di D5, metrik grafik 9 |

**Alur utama:**

```
Petugas --URL/File--> 1.0 --tiket--> 2.0 [scraper, jaringan terisolasi]
                                       | PNG + sha256 awal + metadata
                                       v
                                      3.0 --verifikasi hash--> D4, D7
                                       |--upsert--> D2, D3
                                       |--cek duplikat (URL/SHA-256/pHash)--> D5.duplicate_of
                                       v
              teks konten --> 4.0 <--> D8 (is_active, taxonomy sama, bukan cluster sendiri)
                                       |  (dilewati bila RAG mati / jalur B buta / tanpa teks / gagal)
                                       v
              bukti + metadata + referensi --> 5.0 <--> Gemini (failover, proyek berbayar)
                                       |  [tiket buta: 2 jalur, dengan & tanpa RAG --> 12.0]
                                       v
                                  D5, D6 --> 6.0 --kartu--> Analis
                                              ^               |
                                              +-- keputusan + kode alasan (+ catatan)
                                       v
              keputusan final --> 7.0 (antrian, fail-open) --> D8, D9, D6

Pengguna Dashboard --filter--> 10.0 <-- D5 (final) + D9 --> grafik
ADMIN --aksi--> 11.0 --> D1/D8/D9/D10, log D6
/rekap_harian --> 9.0 --> DOCX (+ chain head D6) --> Supervisor
```

### 2.3 DFD Level 2: Proses 2.0 dan 3.0 (Capture dan Simpan)

- 2.1 Normalisasi URL, ikuti redirect, cek domain terhadap allowlist. Gagal → tolak + audit.
- 2.2 Deteksi platform, jalankan scraper (yt-dlp + Playwright 1080p untuk YouTube; TikTok; Instagram).
- 2.3 Auto-dismiss banner consent/login.
- 2.4 Cek screenshot > 20 KB; gagal → retry 1x → `MANUAL_FALLBACK`.
- 2.5 Tulis PNG ke volume `scratch/`, hitung SHA-256 saat tulis.
- 3.1 Worker menolak symlink dan file non-reguler di `scratch/`, membaca file, hitung ulang SHA-256, bandingkan. Cocok → pindah ke `storage/evidences/`; tidak cocok → `FAILED`.
- 3.2 Hitung pHash (jalur file dan screenshot).
- 3.3 Cek duplikat: URL kanonik → SHA-256 → pHash (petunjuk). Tetapkan `content_cluster_id` (FR-06.3).
- 3.4 Upsert `accounts`, `contents`.
- 3.5 OCR deterministik (Tesseract, bahasa `ind+eng`) atas screenshot/file, simpan ke `reports.ocr_text`. Gagal OCR tidak menghentikan proses (teks OCR kosong).
- 3.6 Undian evaluasi buta (hanya tiket non-duplikat pasti).

### 2.4 DFD Level 2: Proses 4.0 (Retrieval RAG)

- 4.1 Bila `RAG_ENABLED = false` atau jalur B evaluasi buta: `rag_mode = OFF`, selesai.
- 4.2 Susun teks kueri: judul + caption + teks OCR (hasil proses 3.5).
- 4.3 Embedding (retry dengan backoff, **tanpa** failover ke model lain), normalisasi L2. Teks kosong → `rag_mode = NO_TEXT`, selesai.
- 4.4 Exact scan cosine di D8 dengan filter: `is_active`, `taxonomy_version`, bukan `content_cluster_id` sendiri.
- 4.5 Ambil top-k di atas ambang terkalibrasi. Tidak ada hasil → `rag_mode = EMPTY`.
- 4.6 Format blok referensi (hanya field FR-04.4 butir 1). Catat `rag_context`.
- 4.7 Gagal → `rag_mode = FAILED`, audit `RAG_FAILED`, lanjut tanpa konteks.

### 2.5 DFD Level 2: Proses 7.0 (KB dan Entitas)

- 7.1 Terima keputusan final. Lewati bila cluster sudah memiliki entri aktif (bukan keputusan pertama dalam cluster), kecuali berasal dari revisi ADMIN.
- 7.2 Topik: pakai `topik_kode` (atau kode koreksi ADMIN); `LAINNYA` → simpan usulan ke antrian.
- 7.3 Aktor: normalisasi → exact alias → entitas `APPROVED` atau buat `PENDING_REVIEW` (kecuali `INDIVIDU_PRIVAT`). Media asal: normalisasi → exact alias atau nama ternormalisasi (FR-10.4).
- 7.4 Embedding `embed_text` (pakai ulang vektor kueri dari 4.3 bila ada).
- 7.5 Dalam satu transaksi: nonaktifkan entri aktif cluster (bila revisi), simpan entri baru, audit `KB_ENTRY_CREATED`.
- 7.6 Gagal di langkah mana pun → antrian ulang dengan backoff; keputusan analis tetap tersimpan.

### 2.6 DFD Level 2: Proses 12.0 (Evaluasi Buta)

- 12.1 Setelah cek duplikat (3.6), undian acak dengan peluang `EVAL_BLIND_RATE` → `eval_blind = true`.
- 12.2 Fase 1–2: AI dijalankan sekali tanpa RAG (untuk 50 tiket pertama dijalankan dua kali, FR-13.4a). Fase 3: jalur A (dengan RAG) dan jalur B (tanpa RAG), model/prompt/taksonomi dikunci. Jalur A menjadi output resmi laporan.
- 12.3 Kartu buta: bukti + metadata saja, tombol pilih kategori/risiko/Bukan Pelanggaran.
- 12.4 Setelah keputusan: tampilkan output AI sebagai informasi. Status mengikuti `decision_mode = BLIND` (FR-05.3a): pelanggaran = VALIDATED, bukan pelanggaran = REJECTED. Kode alasan tidak diminta.
- 12.5 Tiket buta terpilih untuk penilaian kedua masuk halaman Penilaian Kedua di dashboard; jawabannya hanya ke `second_rater_label` (FR-13.4).
- 12.6 Progres pengumpulan dihitung harian untuk grafik 9; metrik hasil FR-13.5 hanya dihitung saat ukuran sampel tercapai (tidak ada pengintipan hasil antara).

---

## 3. Arsitektur Sistem

### 3.1 Komponen

```
Pengguna Telegram                         Pengguna Dashboard (browser)
      |                                              |  TLS
Telegram Bot API (polling)                           v
      |                                FastAPI app (port 8000)
      |                                - REST API /api/v1/*
      |                                - Dashboard HTML (Jinja2 + HTMX + Chart.js lokal)
      |                                - Sesi Redis, CSRF, TOTP
      +------------------------+---------------------+
                               v
                 Redis `redis` (antrian Celery "default" + sesi)
                               |
                               v
                 service: worker  [jaringan internal + scrape_int]
                 - scrape-collector (BRPOP scrape:results, validasi FR-02.8)
                 - CryptoService (verifikasi hash, pHash), OCR subprocess
                 - AIService (Gemini, failover, Pydantic strict)
                 - RAGService (embedding, retrieval, tulis KB)
                 - EntityService, EvalService (FR-13)
                 - AnalyticsService, ReportService (DOCX), AuditService
                 |  LPUSH scrape:jobs        ^ BRPOP scrape:results
                 v                           |
        Redis `redis-scrape` (scrape_net + scrape_int, ACL per arah)
                 |  BRPOP scrape:jobs        ^ LPUSH scrape:results
                 v                           |
                 service: scraper  [scrape_net, egress internet publik saja]
                 - Playwright, yt-dlp, allowlist navigasi
                 - tanpa kredensial DB/API, tulis ke volume scratch/
                               |
             +-----------------+-----------------+
             v                                   v
   PostgreSQL 16 + pgvector             File Storage (evidences/, reports/)
```

### 3.2 Alur End-to-End

1. Petugas mengirim URL atau file ke bot.
2. Bot cek whitelist, buat tiket `PS-YYYYMMDD-XXXX`, kirim progres.
3. Service `scraper` mengambil bukti (atau handler menerima file), menghitung SHA-256 awal.
4. Worker memverifikasi hash, menyimpan bukti, menghitung pHash, mengecek duplikat, upsert `accounts`/`contents`.
5. Bila RAG aktif dan bukan jalur B evaluasi buta: retrieval referensi.
6. AI menganalisis (dua jalur untuk tiket buta). Output + jejak model disimpan.
7. Bot mengirim kartu: normal, buta, atau duplikat.
8. Analis memutuskan + kode alasan. Update atomik.
9. Kartu diperbarui "Tervalidasi oleh [nama]".
10. Asinkron: normalisasi entitas, penulisan KB (fail-open).
11. Dashboard menampilkan agregat dari keputusan final.
12. `/rekap_harian` menghasilkan DOCX dengan chain head audit, dikirim ke supervisor.

### 3.3 State Machine Tiket

```
[PENDING_ANALYSIS]
   |-- capture sukses (AI sukses, atau AI gagal → NO_AI) --> [WAITING_VALIDATION]
   |-- tiket buta: bukti tersimpan (tanpa menunggu AI) --> [WAITING_VALIDATION]
   |      hasil AI yang datang belakangan hanya menulis eval_runs/kolom AI, tidak pernah mengubah status;
   |      pesan pribadi berisi output AI ke pengambil keputusan dikirim setelah AI selesai
   |                              |-- final_label = label AI (pelanggaran) --> [VALIDATED] --+
   |                              |-- NORMAL: Ubah (+kode alasan)  --> [MODIFIED]  --+--> antrian: entitas + KB
   |                              |-- final_label = BUKAN_PELANGGARAN (semua mode) --> [REJECTED] --+   (lihat FR-09.1)
   |                              |-- BLIND / NO_AI: pelanggaran   --> [VALIDATED]
   |                              |-- Sama dengan induk (duplikat) --> status induk, is_duplicate = true
   |
   |-- capture gagal/blank --> [MANUAL_FALLBACK] --file manual--> [PENDING_ANALYSIS]
   |-- hash mismatch / gagal permanen --> [FAILED]

ADMIN revisi (dashboard) pada VALIDATED|MODIFIED|REJECTED --> status final baru (+ REPORT_REVISED, FR-09.7)
```

Catatan: kegagalan AI setelah seluruh failover habis membuat tiket tetap masuk `WAITING_VALIDATION` dengan kartu "AI tidak tersedia" (`decision_mode = NO_AI`, analis menilai manual seperti kartu buta). Triase tidak berhenti karena AI.

### 3.4 Skema Basis Data

Migrasi dikelola dengan Alembic; setiap perubahan di bawah adalah satu revisi migrasi yang dapat di-rollback.

**`patrol_users` (diperluas, identitas tunggal):** user\_id (UUID, PK), telegram\_id (BigInteger, unique, nullable untuk VIEWER), full\_name, role (OPERATOR, ANALYST, ADMIN, VIEWER), is\_active, **dashboard\_enabled** (Boolean), **username** (unique, nullable), **password\_hash** (argon2id, nullable), **totp\_secret\_enc** (terenkripsi, nullable), **last\_login\_at**, created\_at, last\_active\_at. Tabel `dashboard_users` dari v2 **tidak dibuat**.

**`accounts`, `contents`:** tidak berubah. Kolom `bio` tidak dikirim ke AI.

**`evidences` (diperluas):** + `phash` (String 16), `source_quality` (ORIGINAL, TELEGRAM\_COMPRESSED, SCREENSHOT), `capture_sha256` (hash di titik capture).

**`reports` (diperluas):** kolom v1, ditambah:

| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| topic\_code | String 50 | Kode topik terkontrol (setelah koreksi ADMIN bila ada) |
| topic\_proposal | String 80 | Usulan bila `LAINNYA` |
| ai\_actors\_raw | JSONB | [{nama, jenis}] mentah, tunduk retensi |
| ai\_media\_raw | String 255 | Media asal mentah |
| ai\_media\_type | String 50 | Tipe media asal |
| media\_entity\_id | UUID FK entities | Media asal kanonik |
| final\_label, final\_risk | String | Keputusan final (sudah ada di v1/v2, ditegaskan) |
| reason\_code | String 50, nullable | Kode alasan **keputusan pertama**. CHECK pada keputusan pertama: NOT NULL bila dan hanya bila `decision_mode = NORMAL` dan label atau risiko berbeda dari output AI (FR-05.3). Alasan revisi disimpan di `report_revisions` |
| decision\_mode | Enum | NORMAL, BLIND, NO\_AI, DUPLICATE (FR-05.3a) |
| ocr\_text | Text | Hasil OCR deterministik (proses 3.5) |
| analyst\_notes | Text | Catatan opsional (wajib bila `LAINNYA`) |
| decided\_by | UUID FK patrol\_users | Pengambil keputusan |
| decided\_at | DateTime | |
| duplicate\_of | UUID FK reports, nullable | Laporan induk (duplikat pasti) |
| similar\_to | UUID FK reports, nullable | Petunjuk kemiripan pHash (tidak mengubah status) |
| is\_duplicate | Boolean | Dikonfirmasi analis |
| content\_cluster\_id | UUID | Unit hitung dan pengecualian retrieval |
| eval\_blind | Boolean | Sampel evaluasi buta |
| eval\_runs | JSONB, nullable | Ditulis sekali per run (trigger menolak perubahan entri yang sudah ada); hash label buta dicatat di audit (`BLIND_LABEL_RECORDED`). Untuk tiket buta: label buta asli + daftar run AI {jalur (A/B/B2), model\_id, prompt\_version, status (OK/REFUSED/INVALID/UNAVAILABLE), output, biaya}. B2 = run ulang FR-13.4a |
| cluster\_conflict | Boolean | Keputusan berbeda dalam satu cluster (FR-06.3) |
| original\_decision | JSONB | Snapshot keputusan pertama {final\_label, final\_risk, reason\_code, decided\_by, decided\_at}; ditulis sekali, tidak berubah oleh revisi (trigger) |
| second\_rater\_label | JSONB, nullable | Label penilai kedua {label, risk, rater, at} (FR-13.4) |
| ai\_model\_id, prompt\_version | String | Jejak model |
| rag\_mode | Enum | ON, OFF, EMPTY, NO\_TEXT, FAILED |
| rag\_context | JSONB | [{entry\_id, score}] |
| ai\_cost\_usd | Numeric | Biaya token |
| taxonomy\_version | String 20 | Versi taksonomi saat dianalisis |

Enum `status`: PENDING\_ANALYSIS, WAITING\_VALIDATION, VALIDATED, MODIFIED, REJECTED, MANUAL\_FALLBACK, FAILED.

**`report_revisions` (baru):** revision\_id (UUID, PK), report\_id (FK), old\_label, old\_risk, new\_label, new\_risk, reason\_code (NOT NULL), notes, revised\_by (FK patrol\_users), revised\_at. Kolom keputusan berlaku di `reports` (`final_label`, `final_risk`, status) diperbarui oleh revisi; `original_decision` dan `reason_code` keputusan pertama tidak berubah.

**`report_actors`:** report\_id (FK), entity\_id (FK entities). Hanya aktor non-privat.

**`topics` (baru):** topic\_code (PK), label, is\_active, taxonomy\_version, created\_at.

**`entities`:** entity\_id (UUID, PK), entity\_type (ACTOR, MEDIA), canonical\_name, actor\_kind (TOKOH\_PUBLIK, INSTITUSI, KELOMPOK; null untuk MEDIA), media\_type (untuk MEDIA), status (PENDING\_REVIEW, APPROVED, MERGED), merged\_into (FK, nullable), created\_at, reviewed\_by, reviewed\_at. Unique (entity\_type, canonical\_name).

**`entity_aliases`:** alias\_id, entity\_id (FK), alias\_text, alias\_normalized (indeks unik per entity\_type), created\_at.

**`knowledge_entries`:**

| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| entry\_id | UUID PK | |
| report\_id | UUID FK reports | Laporan yang menulis entri |
| source | String | DECISION (keputusan analis) atau SEED (impor FR-09.6). SEED dikecualikan dari analisis stratifikasi FR-13.3 |
| content\_cluster\_id | UUID | Pengecualian retrieval. Indeks unik parsial `(content_cluster_id) WHERE is_active`: satu entri aktif per cluster |
| decision | String | VALIDATED, MODIFIED, REJECTED |
| decision\_mode | String | NORMAL, BLIND, NO\_AI |
| ai\_suggested | Boolean | Label final = label AI yang ditampilkan (untuk stratifikasi FR-13, tidak masuk prompt) |
| final\_label, final\_risk | String | |
| reason\_code | String | |
| analyst\_notes | Text | Maks 300 karakter dipakai di prompt |
| snippet\_text | Text | Cuplikan teks konten asli, maks 280 karakter dipakai di prompt |
| embed\_text | Text | Judul + caption + OCR deterministik |
| embedding | vector(768), NOT NULL | Ternormalisasi L2. Laporan dengan `rag_mode = NO_TEXT` (tanpa teks) tidak ditulis ke KB |
| embedding\_model | String | Mis. `gemini-embedding-001@768` |
| taxonomy\_version | String | |
| decided\_by | UUID FK patrol\_users | |
| is\_active | Boolean | |
| deactivated\_by, deactivated\_at, deactivation\_reason | | |
| purged\_at | DateTime, nullable | Tombstone retensi |
| created\_at | DateTime | |

Tanpa indeks ANN (NFR-4). Indeks B-tree pada (is\_active, taxonomy\_version). Trigger menolak UPDATE selain kolom deaktivasi; pengecualian hanya untuk role pemilik fungsi `purge_report()` (NFR-8).

**`api_keys` (baru):** key\_id (UUID, PK), label, key\_hash (argon2id), created\_by, created\_at, revoked\_at, last\_used\_at.

**`outbox` (baru):** message\_id (UUID, PK), chat\_id, payload (JSONB: teks, tombol, file), idempotency\_key (unique), status (PENDING, SENT, FAILED), attempts, created\_at, sent\_at. Diisi oleh worker dan celery-beat, dikirim oleh `app` (NFR-14).

**`config_taxonomy` (baru):** version, categories (JSONB), reason\_codes (JSONB), is\_current, approved\_by, created\_at.

**`audit_logs` (diperluas):** + `prev_hash`, `row_hash`; entity\_type ditambah KnowledgeEntry, Entity, Topic, PatrolUser.

### 3.5 Docker Compose

| Service | Image/isi | Jaringan | Secrets |
| --- | --- | --- | --- |
| `db` | `pgvector/pgvector:pg16` (versi di-pin), `CREATE EXTENSION vector` | `internal` | Password DB |
| `redis` | Redis 7 dengan password: broker antrian `default` + sesi dashboard | `internal` | Password Redis |
| `redis-scrape` (baru) | Redis 7 khusus list `scrape:jobs` dan `scrape:results` saja, tanpa data lain. ACL dengan selector Redis 7 per arah: user `scraper` hanya `BRPOP` pada `scrape:jobs` dan `LPUSH` pada `scrape:results`; user `worker` hanya `LPUSH`/`LLEN` pada `scrape:jobs` dan `BRPOP` pada `scrape:results`; keduanya `-@all` selain itu | `scrape_net` (bersama `scraper`) + `scrape_int` (jaringan `internal: true`, bersama `worker`) | Password terpisah per user (`scraper`, `worker`) |
| `egress-proxy` (baru) | Forward proxy keluar (mis. Squid) dengan allowlist domain/SNI per klien | `internal` + egress internet | Tidak ada |
| `proxy` (baru) | Reverse proxy TLS (mis. Caddy atau nginx) di depan `app`; hanya port dashboard yang diekspos, `/api/v1/patrol` tidak diteruskan | jaringan akses dashboard sesuai keputusan §5 no. 14 + `internal` | Sertifikat TLS |
| `app` | FastAPI + dashboard + **satu-satunya proses bot Telegram** (polling dan pengirim pesan keluar dari tabel `outbox`) | `internal`; egress hanya ke `api.telegram.org` | DB (role non-pemilik), Redis, token bot, kunci sesi, kunci enkripsi TOTP |
| `worker` | Celery queue `default`, proses `scrape-collector`, Tesseract OCR (`tesseract-ocr-ind`) | `internal` + `scrape_int` (hanya untuk `redis-scrape`; `worker` tidak berada di `scrape_net`, sehingga tidak ada rute langsung ke internet); egress hanya lewat `egress-proxy` ke endpoint Gemini/Vertex | DB (role non-pemilik), Redis, user `worker` di `redis-scrape`, kredensial Gemini |
| `scraper` (baru) | Image Playwright; loop `BRPOP`/`LPUSH` sederhana (bukan Celery); satu proses browser baru per pekerjaan; container di-recreate setiap hari oleh **timer host** (systemd timer/cron) | `scrape_net`: hanya egress internet publik; diblokir ke `internal`, RFC1918, link-local | Hanya kredensial user `scraper` di `redis-scrape` |
| `celery-beat` (baru) | Penjadwal yang **hanya memasukkan tugas ke antrian** (dieksekusi `worker`): jangkar audit (FR-08.6), timeout catatan `LAINNYA`, purge retensi, verifikasi audit harian, metrik FR-13, kalibrasi bulanan FR-09.9 (ditunda selama jendela evaluasi) | `internal` | Redis |
| `backup` (baru) | Container kecil dengan cron sendiri: `pg_dump` + salin bukti, enkripsi dengan **kunci publik** (kunci privat disimpan di luar server) | `internal` + egress ke penyimpanan backup | Role DB baca-saja khusus backup; mount `storage` baca-saja; kredensial tujuan backup |

Aturan jaringan `scraper` (ditulis sebagai aturan iptables di chain `DOCKER-USER`, karena Docker Compose tidak dapat menyatakannya):

1. Izinkan ke IP statis `redis-scrape` (dikonfigurasi lewat `ipv4_address`, `scraper` terhubung memakai IP, bukan nama) port 6379, dan ke resolver DNS publik yang ditetapkan (DNS internal Docker tidak dipakai `scraper`).
2. Tolak semua tujuan RFC1918, 100.64.0.0/10, 169.254.0.0/16, 127.0.0.0/8, dan subnet Docker lain.
3. Izinkan sisanya (internet publik) untuk TCP 80/443 saja; UDP 443 (QUIC) diblokir agar seluruh lalu lintas melewati aturan yang sama.
4. IPv6 dimatikan pada `scrape_net`.

Egress `app` dan `worker` dibatasi lewat forward proxy keluar (mis. Squid) dengan allowlist domain/SNI: `api.telegram.org` untuk `app`, endpoint Gemini/Vertex untuk `worker`, dan registry paket hanya saat build; koneksi keluar langsung dari jaringan `internal` diblokir (AC-26).

Prasyarat host: modul `br_netfilter` aktif dan `net.bridge.bridge-nf-call-iptables = 1`, karena `scraper` dan `redis-scrape` berbagi bridge `scrape_net`; tanpa ini aturan antar-container di bridge yang sama tidak berlaku. AC-21 menguji aturan ini dari dalam container.

Volume: `pgdata`, `storage` (app/worker), `scratch` (scraper tulis, worker baca-pindah), `incoming` (app tulis unggahan, worker baca-pindah), `backup` (target backup lokal sebelum disalin ke penyimpanan terpisah). Tidak ada service `web` terpisah. Migrasi Alembic dijalankan sebagai job sekali jalan dengan kredensial role pemilik DB (FR-08.5).

### 3.6 REST API

Tetap: `GET /health` (tanpa detail internal). `POST /api/v1/patrol` hanya untuk integrasi internal: tidak diekspos lewat reverse proxy publik, wajib API key per klien (disimpan sebagai hash, dapat dicabut), dan tunduk pada allowlist FR-02.7 yang sama. Seluruh endpoint di bawah (kecuali login) membutuhkan sesi valid; endpoint yang mengubah data membutuhkan token CSRF.

| Endpoint | Role | Fungsi |
| --- | --- | --- |
| POST /api/v1/auth/login | publik | Login (+ langkah TOTP) |
| POST /api/v1/auth/logout | semua | Hapus sesi |
| GET /api/v1/dashboard/summary | VIEWER+ | Total, distribusi |
| GET /api/v1/dashboard/timeseries | VIEWER+ | Tren |
| GET /api/v1/dashboard/breakdown?by=platform\|category\|risk | VIEWER+ | Distribusi |
| GET /api/v1/dashboard/top?type=topic\|actor\|media&limit=N | VIEWER+ (media: ANALYST+, VIEWER 403) | Peringkat (fail-closed FR-10.3, FR-10.4) |
| GET /api/v1/dashboard/disagreement | ANALYST+ | Grafik 8 |
| GET /api/v1/dashboard/reports | ANALYST+ | Drill-down |
| GET /api/v1/dashboard/export | VIEWER+ | CSV (VIEWER: agregat grafik 1–6 saja) |
| GET /api/v1/admin/eval | ADMIN | Grafik 9, metrik FR-13 |
| GET/PATCH /api/v1/admin/knowledge | ADMIN | Daftar, nonaktifkan, seeding |
| GET/POST /api/v1/admin/entities | ADMIN | Setujui, merge, antrian saran |
| GET/POST/PATCH /api/v1/admin/topics | ADMIN | Kelola topik, lihat frekuensi usulan |
| PATCH /api/v1/admin/reports/{id}/entities | ADMIN | Koreksi topik, aktor, media asal sebuah laporan (audit) |
| POST /api/v1/admin/audit/verify | ADMIN | Verifikasi rantai terhadap hash jangkar yang diberikan supervisor |
| POST /api/v1/admin/purge | ADMIN | Purge di luar jadwal (alasan wajib, FR-07.2) |
| GET/POST/PATCH /api/v1/admin/users | ADMIN | Akun, role, whitelist, reset TOTP |
| GET /api/v1/admin/audit | ADMIN | Audit log + verifikasi rantai |
| GET /api/v1/admin/health | ADMIN | Kesehatan sistem (§3.8) |
| POST /api/v1/admin/reports/{id}/revise | ADMIN | Revisi keputusan (FR-05.5) |
| GET /api/v1/admin/conflicts | ADMIN | Daftar `cluster_conflict` |
| GET/POST /api/v1/review/second | ANALYST+ | Halaman Penilaian Kedua (FR-13.4); tiket yang diputuskan sendiri tidak ditampilkan |
| GET /api/v1/review/second/{id}/evidence | ANALYST+ (hanya tiket yang sedang ditugaskan ke penilai tersebut) | Bukti untuk penilaian kedua (diaudit) |
| POST /api/v1/account/password | semua akun dashboard | Ganti password (wajib password lama) |
| POST /api/v1/account/totp-enroll | akun dashboard | Pendaftaran TOTP: wajib password + token pendaftaran sekali pakai (FR-12.5) atau sesi baru pertama bagi role non-ADMIN yang mengaktifkan TOTP sukarela |
| POST /api/v1/admin/users/{id}/totp-reset | ADMIN | Reset TOTP akun lain (bukan diri sendiri): menghasilkan token pendaftaran sekali pakai berlaku 24 jam, diserahkan langsung oleh ADMIN (di luar sistem); pendaftaran ulang memerlukan password + token |
| GET/POST/DELETE /api/v1/admin/api-keys | ADMIN | Kelola API key integrasi `POST /api/v1/patrol` |
| GET /api/v1/admin/evidence/{id} | ADMIN | Unduh bukti (diaudit) |

Filter umum: `date_from`, `date_to`, `platform`, `category`, `risk`, `unit=content|report`.

### 3.7 Mekanisme Keandalan

Seluruh mekanisme v1 dipertahankan (anti-blank, multi-model failover, Safe Reply/Edit). Tambahan:

1. **Fail-open bertingkat:** RAG, entitas, KB, dan evaluasi buta adalah lapisan tambahan; kegagalannya tidak memblokir jalur utama (intake → bukti → kartu → keputusan).
2. **Fallback AI total:** semua model gagal → kartu "AI tidak tersedia", analis menilai manual.
3. **Retry berantrian:** penulisan KB dan entitas memakai antrian dengan backoff eksponensial (maks 5 percobaan), lalu masuk daftar "gagal permanen" di halaman kesehatan. Saat embedding dijeda karena anggaran (NFR-11), penulisan KB tidak dihitung sebagai kegagalan: **tugas** penulisan ditahan di antrian tertunda (bukan baris KB tanpa embedding) dan diproses oleh job backfill begitu anggaran tersedia. Baris KB hanya dibuat setelah embedding tersedia.
4. **Idempotensi:** handler tombol dan tugas Celery memakai kunci idempoten (report\_id + aksi) agar retry Telegram tidak menggandakan keputusan atau entri KB.
5. **Saklar fitur:** `RAG_ENABLED`, `EVAL_BLIND_RATE`, `DEDUP_PHASH_THRESHOLD`, `RAG_TOP_K`, `RAG_THRESHOLD` adalah variabel environment; perubahan cukup dengan restart service terkait (tanpa build ulang image).

### 3.8 Observabilitas

Halaman "Kesehatan Sistem" (ADMIN), dihitung dari DB dan Redis:

| Indikator | Alarm ke grup ADMIN Telegram |
| --- | --- |
| Keberhasilan scrape per platform (20 percobaan terakhir) | < 70% |
| Kedalaman list `scrape:jobs` dan antrian `default` | > 50 tugas selama > 10 menit |
| Waktu kirim sampai kartu (p50, p95, 24 jam) | p95 > 2× target SLO |
| Kejadian failover AI dan `rag_mode = FAILED` (24 jam) | > 20% tiket |
| Biaya bulan berjalan vs batas | 80% dan 100% |
| Tugas KB/entitas gagal permanen | > 0 |
| Antrian review entitas dan usulan topik | > 50 |
| Hasil verifikasi audit harian dan pengiriman jangkar | Rantai putus atau jangkar gagal terkirim |
| Backup terakhir dan uji restore terakhir | Backup > 26 jam; restore > 35 hari |

---

## 4. Rencana Rilis Bertahap dan Migrasi

### 4.1 Fase 1: Fondasi Data dan Keamanan

Isi: model ancaman T1 (service `scraper` terisolasi), FR-01.3, FR-03.4, FR-04.3, FR-04.5, FR-04.6, FR-05.3 sampai FR-05.5, FR-05.3a, FR-06.3, FR-07.2, FR-02.8, FR-08.3 sampai FR-08.6, FR-09.3 (OCR + embedding), FR-09.1 sampai FR-09.7 dan FR-09.9 (KB mode bayangan, retrieval dan kalibrasi diuji tanpa disisipkan ke prompt), FR-10.1 (daftar topik awal), FR-12 (autentikasi, TOTP, bootstrap ADMIN), **dashboard ADMIN minimal** (akun dan whitelist, revisi keputusan, konflik cluster, KB, API key, verifikasi audit, kesehatan sistem dasar) dan halaman Penilaian Kedua, FR-13.1, FR-13.4, FR-13.4a, FR-13.7, penulisan KB mode bayangan (`RAG_ENABLED = false`), evaluasi buta mulai berjalan dengan AI dijalankan sekali (RAG mati, sehingga hanya ada jalur tanpa RAG); label buta terkumpul dan menjadi baseline akurasi tanpa RAG, backup + observabilitas dasar.

Gerbang ke Fase 2: AC-01 sampai AC-05, AC-08 sampai AC-13, AC-15 sampai AC-20, AC-21 sampai AC-27 lulus (untuk AC-04 dan AC-25, bagian penghitungan dashboard diuji di Fase 2); SLO diukur 2 minggu; ambang RAG, near-duplicate, dan pHash dikalibrasi (FR-09.9); kappa 60 tiket buta pertama dan noise antar-run dilaporkan; pemilik produk memutuskan margin, `EVAL_BLIND_RATE`, dan kelayakan durasi (FR-13.4a); aturan FR-13.5 dan ukuran sampel dikunci.

### 4.2 Fase 2: Dashboard Analitik

Isi: FR-10.2 sampai FR-10.4, FR-11, akses VIEWER, halaman kesehatan lengkap. Saat Fase 2 dimulai, job batch menjalankan normalisasi FR-10.2 atas `ai_actors_raw` dan `ai_media_raw` laporan Fase 1 (tanpa panggilan AI), sehingga data Fase 1 ikut tampil di grafik aktor dan media.

Gerbang ke Fase 3: AC-07, AC-14 dan bagian dashboard AC-04/AC-25 lulus; uji restore bulanan terakhir berhasil; review keamanan dashboard (OWASP ASVS level 1 sebagai checklist).

### 4.3 Fase 3: RAG Aktif dengan Evaluasi

Syarat aktivasi: KB ≥ 300 entri aktif **dan** setiap kategori dengan prevalensi ≥ 5% (60 hari terakhir) memiliki ≥ 20 entri. Kategori langka tidak memblokir aktivasi. `RAG_ENABLED = true`, evaluasi buta jalur ganda berjalan, model/prompt/taksonomi dibekukan.

AC-06 dan AC-11 (kali ini dengan RAG aktif, termasuk kasus injeksi yang ditanam di cuplikan entri KB) diuji pada awal Fase 3 sebelum evaluasi dimulai.

Go/no-go: terapkan aturan pra-registrasi FR-13.5 (LULUS / GAGAL / TIDAK MEYAKINKAN). Hasil dilaporkan ke pemilik produk; selain LULUS, RAG dimatikan dan KB tetap ditulis.

Estimasi durasi (contoh, ditetapkan ulang di akhir Fase 1 sesuai FR-13.4a): dengan 100 tiket/hari, `EVAL_BLIND_RATE` 20%, dan 70% tiket mendapat referensi, terkumpul sekitar 14 pasangan populasi utama per hari. M = 7 pp (±320 pasangan) selesai dalam sekitar 23 hari kerja; M = 5 pp (±620 pasangan) sekitar 44 hari kerja.

### 4.4 Migrasi dari v1/v2

1. Migrasi skema lewat Alembic, diuji pada salinan DB produksi sebelum dijalankan.
2. Enum status lama dipetakan langsung; tidak ada perubahan makna.
3. Laporan v1 tetap tampil di dashboard dengan topik "Tidak tersedia (v1)" dan tanpa aktor/media. Opsi isi ulang entitas lewat AI untuk data lama **tidak** dikerjakan (biaya dan risiko halusinasi).
4. Laporan v1 **tidak** otomatis masuk KB (tidak punya kode alasan). ADMIN dapat menyeleksi dan meninjau ulang kasus v1 untuk seeding (FR-09.6); entri seed ditandai `KB_ENTRY_SEEDED`.
5. Audit hash-chain dimulai dari entri pertama setelah migrasi; entri lama di-hash sekali sebagai blok genesis.
6. Akun dashboard dibuat di `patrol_users`; tidak ada migrasi dari `dashboard_users` karena tabel itu tidak pernah dibuat.

---

## 5. Asumsi dan Keputusan Terbuka

| No | Item | Usulan default | Pemilik keputusan |
| --- | --- | --- | --- |
| 1 | Model embedding dan dimensi | `gemini-embedding-001`, 768 dimensi, L2-normalized | Tim teknis (dikunci di Fase 1) |
| 2 | Nilai k, ambang similarity, ambang pHash | k=5; ambang dari kalibrasi FR-09.9; pHash 6 | Tim teknis setelah kalibrasi |
| 3 | Autentikasi | Username/password + TOTP ADMIN; SSO ditunda | Kebijakan instansi |
| 4 | Cakupan platform (PRD 3, proposal magang 5) | 3 platform di v3; platform lain = non-goal | Pemilik produk |
| 5 | Bukti gambar di dashboard | ADMIN saja | Pemilik produk |
| 6 | Kategori baru (judi online, konten asusila) | Tidak ditambah tanpa persetujuan. Catatan: konten asusila menimbulkan isu legal penyimpanan dan pengiriman ke pihak ketiga (Gemini) | Pemangku kepentingan + bagian hukum |
| 7 | KOP dokumen dinas (Kemkomdigi di v1, BSSN di proposal) | Perlu dikonfirmasi | Pemilik produk |
| 8 | Lanjutan kalimat terpotong pada permintaan fitur ("serta ...") | **Wajib diklarifikasi sebelum sign-off cakupan v3**; fitur yang muncul dari klarifikasi masuk v3.1 kecuali pemilik produk menyatakan blocker | Pemilik produk |
| 9 | **Klasifikasi data** konten patroli dan izin pengiriman ke Gemini (region, tier berbayar) dan transit via Telegram | Wajib diputuskan sebelum produksi | Pimpinan + pejabat keamanan informasi |
| 10 | **Periode retensi** laporan, bukti, KB, nama mentah | Mengikuti kebijakan instansi dan UU PDP | Pimpinan + bagian hukum |
| 11 | Batas anggaran AI bulanan | Ditetapkan dari baseline Fase 1 | Pemilik produk |
| 12 | Daftar topik awal (20 sampai 40) dan kode alasan | Disusun bersama analis senior sebelum Fase 1 | Analis senior + ADMIN |
| 13 | Volume tiket harian | Diasumsikan puluhan sampai ratusan; memengaruhi waktu evaluasi dan keputusan indeks | Diukur di Fase 1 |
| 14 | Eksposur dashboard (intranet saja, VPN, atau internet publik dengan TLS) | Usulan: intranet/VPN saja; internet publik hanya dengan persetujuan tertulis | Pejabat keamanan informasi |

---

## Lampiran A. Jejak Keputusan Review

Ringkasan usulan yang dipertimbangkan lalu **tidak** diambil, agar tidak diusulkan ulang tanpa alasan baru:

| Usulan | Keputusan | Alasan |
| --- | --- | --- |
| Holdout acak 15% tanpa RAG, metrik "kesepakatan AI-analis" | Diganti FR-13 | Kesepakatan dipengaruhi analis yang melihat output AI (mengukur daya bujuk, bukan kebenaran); holdout tidak berpasangan butuh sampel jauh lebih besar |
| Menampilkan referensi RAG di kartu analis | Ditolak | Menambah isyarat konsensus dan memperkuat anchoring; referensi tersedia di dashboard ADMIN (dan di `/status` setelah tiket diputuskan) |
| OTP 2FA via bot Telegram | Ditolak | Satu akun Telegram yang dibobol mengalahkan intake dan 2FA sekaligus |
| Deteksi duplikat dengan similarity embedding ≥ 0,95 | Ditolak | Ambang tak terkalibrasi; URL kanonik + SHA-256 + pHash sudah cukup |
| Indeks HNSW | Ditunda | Volume kecil; ANN dengan filter dapat mengembalikan < k hasil |
| Normalisasi topik free-text + fuzzy merge | Diganti topik terkontrol | Kardinalitas tinggi membanjiri antrian ADMIN |
| Notifikasi lonjakan topik | Non-goal v3 | Rawan alarm palsu pada jumlah kecil |
| Sub-menu koreksi entitas di Telegram | Dihapus | Kompleksitas state percakapan bot |
| Service frontend terpisah | Dihapus | Dashboard disajikan dari `app` |
| Batas maks 2 referensi per analis | Dihapus | Dengan 2–3 analis, batas ini mengosongkan top-k sementara perlindungannya terhadap poisoning kecil; diganti pemantauan lewat FR-13.6 |
| Failover model embedding | Dihapus | Vektor dari model berbeda tidak sebanding; satu model, gagal = fail-open |
| Ringkasan narasi AI sebagai konteks RAG | Diganti cuplikan teks asli | Mencegah AI melihat output lamanya sendiri, yang akan menggelembungkan hasil evaluasi |
| Alur persetujuan entitas media asal | Disederhanakan | Nama media adalah institusi publik; cukup normalisasi + alias, tampil untuk ANALYST/ADMIN |
| Ringkasan mingguan supervisor terpisah | Digabung ke DOCX harian | Satu kanal laporan, tanpa job tambahan |
| Purge dengan persetujuan dua ADMIN | Diganti alasan wajib + pelaporan di DOCX | Tim kecil mungkin hanya punya satu ADMIN |
| Aturan lulus RAG berbasis estimasi titik (≥ −2 pp, n = 150) | Diganti interval kepercayaan + tiga hasil (FR-13.5) | Pada n = 150 estimasi titik tidak dapat membedakan efek nyata dari noise |
| Perubahan konfigurasi "tanpa deploy" | Diganti environment + restart | Tidak perlu config store terpisah |
| Supresi sel kecil (n < 5) untuk VIEWER | Dihapus | Tidak mencegah differencing antar rentang tanggal; VIEWER adalah pejabat internal berwenang |
| Pemetaan taksonomi antar-versi | Dihapus | Taksonomi dibekukan selama v3; perubahan = rilis baru |
| Saran merge fuzzy dan promosi usulan topik | Dihapus | Tim kecil; alias exact + aksi manual ADMIN cukup |
| Status kandidat duplikat pHash | Diganti petunjuk di kartu | Mengurangi state; konfirmasi lewat tombol "Sama dengan induk" |
| Membuang pasangan evaluasi saat failover | Ditolak | Penolakan model cenderung terjadi pada konten TINGGI; membuangnya membuat sampel bias. Kegagalan dihitung salah |
| Pemeriksaan antara (Pocock) dan estimasi ulang sampel | Diganti satu analisis ukuran tetap | Lebih sederhana; kelayakan durasi diputuskan di akhir Fase 1 |
| Kartu buta kedua lewat chat pribadi dengan penugasan dan timeout | Diganti halaman Penilaian Kedua di dashboard | Tidak ada tiket tertahan; tanpa state penugasan di bot |
| Perintah ADMIN di Telegram (`/revisi`, whitelist, verifikasi audit) | Dipindah ke dashboard ber-TOTP | Akun Telegram yang dibobol tidak boleh cukup untuk tindakan administratif |
