"""Seed Validated Memory with 32 Realistic IPOLEKSOSBUDHANKAM Cases.

Provides high-quality cold-start precedents for MemPrompt Few-Shot In-Context Learning:
- 4 cases per category across all 8 strategic IPOLEKSOSBUDHANKAM categories
- Bilingual Indonesian and English representations
- Sharp, forensic analyst rationales
"""

import json
import os
import sys

# Ensure project path is accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.database import SessionLocal
from app.models.memory import ValidatedMemory
from app.services.memory_service import MemoryService

SEED_CASES = [
    # ── 1. IDEOLOGI (4 KASUS) ──
    {
        "text": "Pancasila sudah usang dan terbukti gagal mensejahterakan rakyat. Saatnya umat bersatu meruntuhkan sistem demokrasi thaghut ini dan mendeklarasikan kekhalifahan Islam secara kaffah di tanah Nusantara!",
        "category": "Ideologi",
        "rationale": "Narasi secara eksplisit menolak Pancasila dan konstitusi NKRI serta mempropagandakan pergantian ideologi negara dengan sistem khilafah.",
        "urgency": 5,
    },
    {
        "text": "Call to all true comrades: capitalism has destroyed the proletariat. We must revive Marxist-Leninist underground cells to dismantle the bourgeois state apparatus and establish a communist society.",
        "category": "Ideologi",
        "rationale": "Ajakan pembentukan sel komunis bawah tanah dan penyebaran marxisme-leninisme yang bertentangan dengan TAP MPRS No. XXV/1966 tentang larangan ideologi komunisme.",
        "urgency": 4,
    },
    {
        "text": "Bendera Merah Putih adalah bendera thaghut, tidak boleh dihormati dalam upacara sekolah. Siapa yang menghormatinya telah kafir dan keluar dari akidah murni.",
        "category": "Ideologi",
        "rationale": "Penolakan terhadap simbol kedaulatan negara dan doktrinasi anti-konsensus kebangsaan yang mengarah pada radikalisme ideologis.",
        "urgency": 4,
    },
    {
        "text": "Pendidikan Pancasila di sekolah harus dihapuskan total karena hanya menjadi alat propaganda pemerintah sekuler yang menindas syariat.",
        "category": "Ideologi",
        "rationale": "Upaya delegitimasi pendidikan dasar ideologi kebangsaan negara secara sistematis di ruang publik digital.",
        "urgency": 3,
    },

    # ── 2. POLITIK (4 KASUS) ──
    {
        "text": "BOCOR DOKUMEN RAHASIA! Server KPU telah diatur untuk memenangkan paslon nomor urut tertentu sebesar 62 persen. Ribuan kotak suara di Jawa Timur sudah dicoblos lebih dulu tadi malam oleh oknum berseragam!",
        "category": "Politik",
        "rationale": "Disinformasi elektoral berskala besar yang menargetkan integritas proses pemilu dan mendelegitimasi penyelenggara pemilu (KPU).",
        "urgency": 5,
    },
    {
        "text": "Presiden dan Ketua Mahkamah Konstitusi mengadakan pertemuan rahasia di Istana Bogor untuk merancang pembubaran paksa partai oposisi dan mengubah masa jabatan menjadi seumur hidup.",
        "category": "Politik",
        "rationale": "Kabar bohong bermuatan intrik politik tingkat tinggi yang menyerang pimpinan lembaga negara untuk memicu krisis ketidakpercayaan publik.",
        "urgency": 4,
    },
    {
        "text": "Leaked internal memo from the Electoral Commission confirms millions of phantom voters were injected into the voter registry to steal the upcoming regional election.",
        "category": "Politik",
        "rationale": "Narasi fitnah kecurangan elektoral berbahasa asing yang memprovokasi keraguan publik terhadap keabsahan daftar pemilih tetap (DPT).",
        "urgency": 4,
    },
    {
        "text": "Gubernur petahana dilaporkan menerima gratifikasi Rp 50 miliar dari sindikat pengembang tambang untuk mendanai kampanye periode kedua.",
        "category": "Politik",
        "rationale": "Isu korupsi politik dan suap kampanye pada momen pemilihan kepala daerah yang membutuhkan verifikasi faktual penegak hukum.",
        "urgency": 3,
    },

    # ── 3. EKONOMI (4 KASUS) ──
    {
        "text": "PERINGATAN KRISIS PERBANKAN! Bank BUMN terbesar nasional mengalami gagal bayar likuiditas parah dan akan dibekukan OJK besok pagi. Tarik seluruh tabungan dan deposito Anda di ATM sekarang juga sebelum hangus!",
        "category": "Ekonomi",
        "rationale": "Provokasi bank run terstruktur yang berpotensi memicu kepanikan finansial massal dan meruntuhkan stabilitas sistem perbankan nasional.",
        "urgency": 5,
    },
    {
        "text": "Sindikat kami menjual uang palsu emisi terbaru pecahan Rp 100.000 dengan kemiripan 99 persen tembus sinar UV dan mesin hitung. Siap kirim ke seluruh Indonesia melalui kurir ekspedisi.",
        "category": "Ekonomi",
        "rationale": "Tindak pidana moneter berupa peredaran uang rupiah palsu secara terbuka di media sosial yang merugikan perekonomian negara.",
        "urgency": 4,
    },
    {
        "text": "Investasi trading emas digital bergaransi profit 35 persen per minggu resmi berizin kementerian. Setor minimal Rp 5 juta hari ini langsung cair dividen harian tanpa risiko.",
        "category": "Ekonomi",
        "rationale": "Praktik penipuan investasi bodong skema ponzi ilegal yang mencatut nama kementerian dan menyasar dana masyarakat rentan.",
        "urgency": 3,
    },
    {
        "text": "Gudang distributor beras di kawasan industri menimbun ratusan ton beras SPHP bantuan pemerintah untuk dijual kembali ke pasar gelap dengan harga dua kali lipat.",
        "category": "Ekonomi",
        "rationale": "Spekulasi dan penimbunan komoditas pangan pokok strategis yang merusak rantai pasok dan membebani daya beli masyarakat.",
        "urgency": 3,
    },

    # ── 4. SOSIAL (4 KASUS) ──
    {
        "text": "Malam ini kita serbu kampung sebelah! Jangan kasih ampun orang-orang pendatang itu, bawa celurit dan molotov kita ratakan pemukiman mereka sekarang juga!",
        "category": "Sosial",
        "rationale": "Ajakan kekerasan fisik, tawuran massal, dan penyerangan antarkelompok masyarakat yang berisiko langsung menimbulkan korban jiwa.",
        "urgency": 5,
    },
    {
        "text": "Waspada suku tertentu yang datang merantau ke daerah kita. Mereka semua pencuri dan perusak moral anak-anak muda. Usir mereka keluar dari tanah kita sekarang juga!",
        "category": "Sosial",
        "rationale": "Ujaran kebencian berbasis SARA (Sentimen Antargolongan dan Etnis) yang merusak kohesi sosial dan memicu diskriminasi rasial.",
        "urgency": 4,
    },
    {
        "text": "A viral video shows a mob gathering at the central market calling for an ethnic boycott and forced expulsion of minority business owners.",
        "category": "Sosial",
        "rationale": "Provokasi boikot etnis dan segregasi sosial antarkelompok masyarakat yang berpotensi memantik kerusuhan komunal.",
        "urgency": 4,
    },
    {
        "text": "Rumah sakit dituduh mengkovidkan pasien lansia demi mencairkan klaim asuransi pemerintah ratusan juta rupiah per pasien.",
        "category": "Sosial",
        "rationale": "Desas-desus sosial di bidang layanan kesehatan masyarakat yang merusak kepercayaan publik terhadap tenaga medis.",
        "urgency": 3,
    },

    # ── 5. BUDAYA (4 KASUS) ──
    {
        "text": "Candi peninggalan leluhur ini adalah sarang kemusyrikan dan berhala! Patung-patung batu di situs cagar budaya itu wajib dihancurkan sampai rata dengan tanah agar bumi berkah.",
        "category": "Budaya",
        "rationale": "Ajakan vandalisme dan perusakan fisik situs warisan cagar budaya sejarah nasional bermotif intoleransi budaya.",
        "urgency": 4,
    },
    {
        "text": "Pakaian adat tradisional daerah dinilai tidak bermoral dan menjijikkan. Siapa pun perempuan yang memakainya di acara kebudayaan pantas dilempari kotoran.",
        "category": "Budaya",
        "rationale": "Pelecehan verbal dan perundungan terhadap busana adat warisan kebudayaan Nusantara yang dilindungi undang-undang pemajuan kebudayaan.",
        "urgency": 3,
    },
    {
        "text": "Negara tetangga secara sepihak mempatenkan tarian sakral tradisional dan musik gamelan sebagai warisan budaya asli mereka di UNESCO tanpa izin Indonesia.",
        "category": "Budaya",
        "rationale": "Polemik sengketa hak kekayaan intelektual komunal dan klaim unilateral warisan budaya tradisional di tingkat internasional.",
        "urgency": 3,
    },
    {
        "text": "Upacara adat laut sedekah bumi dituduh sebagai ritual pemanggil bencana tsunami dan diancam akan dibubarkan secara paksa oleh kelompok ormas tertentu.",
        "category": "Budaya",
        "rationale": "Ancaman persekusi dan pembubaran tradisi adat lokal maritim yang telah diwariskan turun-temurun oleh masyarakat pesisir.",
        "urgency": 3,
    },

    # ── 6. PERTAHANAN (4 KASUS) ──
    {
        "text": "DITEMUKAN DI FORUM DARKWEB: Blueprint koordinat bunker pertahanan bawah tanah pangkalan TNI AL di Natuna beserta frekuensi enkripsi sonar kapal selam KRI terbaru!",
        "category": "Pertahanan",
        "rationale": "Kebocoran data rahasia intelijen pertahanan negara menyangkut instalasi militer strategis dan alutsista di wilayah perbatasan kedaulatan.",
        "urgency": 5,
    },
    {
        "text": "Foreign military surveillance aircraft repeatedly breached sovereign airspace over the northern border undetected by radar systems due to maintenance downtime.",
        "category": "Pertahanan",
        "rationale": "Pelanggaran kedaulatan ruang udara teritorial negara oleh pesawat militer asing yang menyangkut kesiapsiagaan operasi pertahanan udara.",
        "urgency": 5,
    },
    {
        "text": "Prajurit perbatasan memposting rekaman video di TikTok memperlihatkan secara jelas letak pos pantau rahasia, jumlah amunisi aktif, dan jadwal rotasi patroli patroli hutan.",
        "category": "Pertahanan",
        "rationale": "Pelanggaran disiplin operasional militer (*operational security / OPSEC*) yang mengekspos titik kerentanan taktis pertahanan perbatasan darat.",
        "urgency": 4,
    },
    {
        "text": "Kapal perang asing tanpa izin mengawal puluhan kapal nelayan bersenjata masuk jauh ke dalam Zona Ekonomi Eksklusif (ZEE) Indonesia di Laut Natuna Utara.",
        "category": "Pertahanan",
        "rationale": "Ancaman terhadap kedaulatan maritim dan integritas wilayah perairan yurisdiksi pertahanan nasional oleh kekuatan asing.",
        "urgency": 4,
    },

    # ── 7. KEAMANAN (4 KASUS) ──
    {
        "text": "ANCAMAN BOM! Kami telah menanam 3 paket peledak C-4 di pusat perbelanjaan Jakarta Pusat. Bom akan meledak pukul 14.00 WIB jika uang tebusan 100 Bitcoin tidak ditransfer!",
        "category": "Keamanan",
        "rationale": "Tindak pidana terorisme berupa ancaman bom nyata di ruang publik yang menuntut respons kedaruratan taktis kepolisian dan penjinak bom segera.",
        "urgency": 5,
    },
    {
        "text": "Hacked database containing 50 million citizen biometric records and police records is currently for sale on breach forums. Sample dump verified authentic.",
        "category": "Keamanan",
        "rationale": "Serangan siber masif dan kebocoran data biometrik kependudukan serta catatan kepolisian yang mengancam keamanan siber nasional.",
        "urgency": 5,
    },
    {
        "text": "Menyediakan senjata api rakitan kaliber 9mm, revolver, dan amunisi aktif tanpa izin. Transaksi aman via escrow rekening bersama dan kirim kurir instan.",
        "category": "Keamanan",
        "rationale": "Peredaran gelap senjata api dan amunisi ilegal yang melanggar UU Darurat No. 12 Tahun 1951 dan mengancam kamtibmas masyarakat.",
        "urgency": 4,
    },
    {
        "text": "Tutorial lengkap peracikan zat kimia beracun dan detonator sederhana menggunakan bahan-bahan pupuk yang mudah dibeli di toko pertanian bebas.",
        "category": "Keamanan",
        "rationale": "Penyebaran materi berbahaya instruksi pembuatan bahan peledak (IED) yang biasa digunakan oleh jaringan sel terorisme.",
        "urgency": 4,
    },

    # ── 8. NON-ISU (4 KASUS) ──
    {
        "text": "Resep rahasia rendang daging sapi khas Minang Padang warisan nenek moyang. Bumbu rempah asli meresap sempurna, empuk tahan berminggu-minggu tanpa bahan pengawet kimia.",
        "category": "Non-Isu",
        "rationale": "Konten murni seputar kuliner dan resep masakan tradisional. Tidak mengandung anasir provokasi, pelanggaran hukum, atau ancaman keamanan.",
        "urgency": 1,
    },
    {
        "text": "Tips belajar pemrograman Python untuk pemula dari nol sampai mahir. Pelajari struktur data list, dictionary, fungsi, dan pengenalan framework FastAPI.",
        "category": "Non-Isu",
        "rationale": "Konten edukasi teknologi informasi positif dan pengembangan keahlian digital masyarakat umum.",
        "urgency": 1,
    },
    {
        "text": "Exploring the majestic underwater paradise of Raja Ampat Papua. Crystal clear waters, vibrant coral reefs, and exotic manta rays swimming freely.",
        "category": "Non-Isu",
        "rationale": "Dokumentasi promosi pariwisata alam dan keindahan bahari Indonesia berbahasa Inggris yang bernilai promosi positif.",
        "urgency": 1,
    },
    {
        "text": "Panduan olahraga kardio ringan 15 menit setiap pagi untuk menjaga kesehatan jantung dan mencegah lonjakan kadar gula darah bagi pekerja kantoran.",
        "category": "Non-Isu",
        "rationale": "Edukasi pola hidup sehat dan kesehatan jasmani masyarakat tanpa muatan isu strategis IPOLEKSOSBUDHANKAM.",
        "urgency": 1,
    },
]


def seed_memory():
    """Seed the database with 32 ground-truth cases."""
    print("===============================================================================")
    print("  [*] MEMULAI SEEDING 32 KASUS PRESEDEN HISTORIS (MEMPROMPT FEW-SHOT)")
    print("===============================================================================")

    db = SessionLocal()
    seeded_count = 0
    updated_count = 0

    try:
        for idx, item in enumerate(SEED_CASES, 1):
            text = item["text"].strip()
            cat = item["category"]
            rationale = item["rationale"]
            urgency = item["urgency"]

            # Compute embedding
            emb = MemoryService.compute_embedding(text)
            emb_json = json.dumps(emb)

            # Check if this exact text is already seeded
            existing = db.query(ValidatedMemory).filter(ValidatedMemory.content_text == text).first()
            if existing:
                existing.embedding_vector = emb_json
                existing.validated_category = cat
                existing.analyst_rationale = rationale
                existing.urgency_score = urgency
                updated_count += 1
            else:
                new_mem = ValidatedMemory(
                    content_text=text,
                    embedding_vector=emb_json,
                    validated_category=cat,
                    analyst_rationale=rationale,
                    validated_by="Principal Analyst (Cold-Start Seed)",
                    urgency_score=urgency,
                )
                db.add(new_mem)
                seeded_count += 1

            if idx % 8 == 0:
                print(f"  [>] Memproses {idx}/32 kasus ({cat})...")

        db.commit()
        print("-------------------------------------------------------------------------------")
        print(f"  [v] SEEDING SUKSES: {seeded_count} kasus baru ditambahkan, {updated_count} diperbarui.")
        print(f"  [*] Total preseden aktif di ValidatedMemory: {db.query(ValidatedMemory).count()}")
        print("===============================================================================")
    except Exception as ex:
        db.rollback()
        print(f"  [ERROR] Gagal melakukan seeding: {ex}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_memory()
