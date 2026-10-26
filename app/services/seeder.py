"""Proposal-compliant simulation dataset seeder (Proposal pages 43–44).

Seeds 10 standardized simulation reports with:
- 9 validated findings (6 VALIDATED, 3 MODIFIED) + 1 REJECTED (Bukan pelanggaran)
- Platforms for 9 findings: 4 Instagram, 3 TikTok, 2 YouTube
- Final labels for 9 findings: 3 HOAKS, 3 DI_LUAR_KONTEKS, 2 UJARAN_KEBENCIAN, 1 PROVOKASI_SARA
- Final risks for 9 findings: 4 SEDANG (44%), 3 TINGGI (33%), 2 RENDAH (22%)
- REJECTED report: final_risk = None, mandatory analyst notes
- Neutral fictional entities: Topics, Actors, Sources
- Composite PK ReportActor records
- Forensic Evidences with valid 64-hex SHA-256 and size > 20 KB
- Versioned KnowledgeEntries (NFR-07)
"""

import os
import hashlib
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.models.report import Report, Content, Account
from app.models.evidence import Evidence
from app.models.entities import Entity, ReportActor
from app.models.knowledge import KnowledgeEntry
from app.models.user import PatrolUser
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def seed_proposal_data_if_needed(db: Session):
    """Seed 10 proposal simulation reports and default patrol users if database has no reports."""
    # 1. Seed patrol users if empty
    if db.query(PatrolUser).count() == 0:
        default_patrol_users = [
            PatrolUser(
                telegram_id=100101,
                full_name="Briptu Agus (Operator Piket)",
                role="OPERATOR",
                is_active=True,
            ),
            PatrolUser(
                telegram_id=100102,
                full_name="Ipda Budi (Analis Siber)",
                role="ANALYST",
                is_active=True,
            ),
            PatrolUser(
                telegram_id=100103,
                full_name="Kompol Citra (Admin Pengawas)",
                role="ADMIN",
                is_active=True,
            ),
        ]
        db.add_all(default_patrol_users)
        db.commit()
        logger.info("Seeded 3 default patrol users (OPERATOR, ANALYST, ADMIN)")

    # 2. Check if reports already exist
    existing_reports_count = db.query(Report).count()
    if existing_reports_count > 0:
        logger.info("Reports table already contains %d records. Skipping proposal seeder.", existing_reports_count)
        return

    logger.info("Seeding 10 Proposal-compliant simulation reports (Pages 43-44)...")
    os.makedirs("storage/evidences", exist_ok=True)

    # 3. Seed canonical entities
    topic_data = [
        ("Layanan Publik", "PELAYANAN_PUBLIK"),
        ("Kesehatan Publik", "KESEHATAN"),
        ("Kerukunan Sosial", "SOSIAL"),
        ("Pendidikan", "PENDIDIKAN"),
        ("Lingkungan", "LINGKUNGAN"),
        ("Kebencanaan", "KEBENCANAAN"),
    ]
    topic_entities = {}
    for name, cat in topic_data:
        ent = db.query(Entity).filter_by(canonical_name=name, entity_type="TOPIC").first()
        if not ent:
            ent = Entity(canonical_name=name, entity_type="TOPIC", category=cat, status="CANONICAL")
            db.add(ent)
            db.flush()
        topic_entities[name] = ent

    actor_data = [
        ("Unit Pelayanan A", "INSTANSI"),
        ("Lembaga Kesehatan B", "INSTANSI"),
        ("Kelompok Anonim D", "KELOMPOK"),
        ("Sekolah Fiktif E", "INSTANSI"),
        ("Komunitas F", "KOMUNITAS"),
        ("Unit Layanan G", "INSTANSI"),
        ("Kelompok Anonim H", "KELOMPOK"),
    ]
    actor_entities = {}
    for name, cat in actor_data:
        ent = db.query(Entity).filter_by(canonical_name=name, entity_type="ACTOR").first()
        if not ent:
            ent = Entity(canonical_name=name, entity_type="ACTOR", category=cat, status="CANONICAL")
            db.add(ent)
            db.flush()
        actor_entities[name] = ent

    source_data = [
        ("Kanal video B", "CHANNEL"),
        ("Kanal informasi A", "CHANNEL"),
        ("Akun edukasi C", "USER_ACCOUNT"),
        ("Portal warta D", "MEDIA_OUTLET"),
        ("Akun opini E", "USER_ACCOUNT"),
        ("Kanal siar F", "CHANNEL"),
    ]
    source_entities = {}
    for name, cat in source_data:
        ent = db.query(Entity).filter_by(canonical_name=name, entity_type="SOURCE").first()
        if not ent:
            ent = Entity(canonical_name=name, entity_type="SOURCE", category=cat, status="CANONICAL")
            db.add(ent)
            db.flush()
        source_entities[name] = ent

    db.commit()

    # 4. Specification for the 10 Proposal Reports
    # Note: 9 validated findings (6 VALIDATED + 3 MODIFIED) + 1 REJECTED (Bukan pelanggaran)
    # Platforms: 4 Instagram, 3 TikTok, 2 YouTube (plus 1 YouTube rejected)
    # Categories: 3 HOAKS, 3 DI_LUAR_KONTEKS, 2 UJARAN_KEBENCIAN, 1 PROVOKASI_SARA
    # Risks: 4 SEDANG (44%), 3 TINGGI (33%), 2 RENDAH (22%)
    simulation_specs = [
        {
            "ticket": "PS-20261022-SIM01",
            "platform": "instagram",
            "status": "VALIDATED",
            "ai_label": "HOAKS",
            "final_label": "HOAKS",
            "ai_risk": "SEDANG",
            "final_risk": "SEDANG",
            "topic": "Kesehatan Publik",
            "actor": "Lembaga Kesehatan B",
            "source": "Kanal informasi A",
            "username": "info_kesehatan_fiktif",
            "title": "Klaim Vaksinasi Khusus Tanpa Bukti Ilmiah",
            "caption": "Pemberitahuan darurat mengenai suplemen pengganti vaksin resmi yang belum diuji klinis.",
            "notes": "Disetujui: Konten terbukti memuat narasi hoaks kesehatan publik.",
            "decision": "APPROVED",
            "days_ago": 3,
        },
        {
            "ticket": "PS-20261022-SIM02",
            "platform": "instagram",
            "status": "VALIDATED",
            "ai_label": "DI_LUAR_KONTEKS",
            "final_label": "DI_LUAR_KONTEKS",
            "ai_risk": "SEDANG",
            "final_risk": "SEDANG",
            "topic": "Layanan Publik",
            "actor": "Unit Pelayanan A",
            "source": "Akun edukasi C",
            "username": "edukasi_publik_id",
            "title": "Potongan Video Antrean Disinformasi Layanan",
            "caption": "Video antrean lama diunggah ulang dengan narasi kegagalan sistem layanan publik hari ini.",
            "notes": "Disetujui: Bukti visual menunjukkan manipulasi konteks waktu.",
            "decision": "APPROVED",
            "days_ago": 3,
        },
        {
            "ticket": "PS-20261022-SIM03",
            "platform": "instagram",
            "status": "VALIDATED",
            "ai_label": "UJARAN_KEBENCIAN",
            "final_label": "UJARAN_KEBENCIAN",
            "ai_risk": "TINGGI",
            "final_risk": "TINGGI",
            "topic": "Kerukunan Sosial",
            "actor": "Kelompok Anonim D",
            "source": "Portal warta D",
            "username": "warta_suara_rakyat",
            "title": "Ajakan Persekusi Terhadap Kelompok Masyarakat Tertentu",
            "caption": "Pernyataan provokatif yang menuduh kelompok masyarakat tertentu sebagai dalang kriminalitas.",
            "notes": "Disetujui: Memenuhi unsur ujaran kebencian berisiko eskalasi fisik.",
            "decision": "APPROVED",
            "days_ago": 2,
        },
        {
            "ticket": "PS-20261022-SIM04",
            "platform": "instagram",
            "status": "MODIFIED",
            "ai_label": "HOAKS",
            "final_label": "DI_LUAR_KONTEKS",
            "ai_risk": "TINGGI",
            "final_risk": "SEDANG",
            "topic": "Kebencanaan",
            "actor": "Unit Layanan G",
            "source": "Akun opini E",
            "username": "opini_kritis_warga",
            "title": "Rekaman Banjir 2020 Diklaim Kejadian Hari Ini",
            "caption": "Unggahan video banjir bandang dengan narasi tanggul kota jebol pagi tadi.",
            "notes": "Penyesuaian analis: Rekaman asli valid namun konteks waktu diputarbalikkan. Kategori diubah ke DI_LUAR_KONTEKS, risiko diturunkan ke SEDANG.",
            "decision": "MODIFIED",
            "days_ago": 2,
        },
        {
            "ticket": "PS-20261022-SIM05",
            "platform": "tiktok",
            "status": "VALIDATED",
            "ai_label": "HOAKS",
            "final_label": "HOAKS",
            "ai_risk": "TINGGI",
            "final_risk": "TINGGI",
            "topic": "Kesehatan Publik",
            "actor": "Lembaga Kesehatan B",
            "source": "Kanal video B",
            "username": "video_viral_fakta",
            "title": "Palsu: Air Rebusan Bahan Dapur Sembuhkan Penyakit Kronis",
            "caption": "Video narasi dokter palsu mengklaim obat kimia rumah sakit berbahaya dan dapat diganti air garam pekat.",
            "notes": "Disetujui: Hoaks medis berbahaya yang mengancam keselamatan nyawa pasien.",
            "decision": "APPROVED",
            "days_ago": 2,
        },
        {
            "ticket": "PS-20261022-SIM06",
            "platform": "tiktok",
            "status": "VALIDATED",
            "ai_label": "PROVOKASI_SARA",
            "final_label": "PROVOKASI_SARA",
            "ai_risk": "TINGGI",
            "final_risk": "TINGGI",
            "topic": "Kerukunan Sosial",
            "actor": "Kelompok Anonim H",
            "source": "Kanal siar F",
            "username": "siar_suara_muda",
            "title": "Narasi Adu Domba Antargolongan Beragama",
            "caption": "Konten memutarbalikkan dialog keagamaan untuk menyulut sentimen kebencian primordial.",
            "notes": "Disetujui: Indikasi provokasi SARA terverifikasi dengan tingkat risiko TINGGI.",
            "decision": "APPROVED",
            "days_ago": 1,
        },
        {
            "ticket": "PS-20261022-SIM07",
            "platform": "tiktok",
            "status": "MODIFIED",
            "ai_label": "DI_LUAR_KONTEKS",
            "final_label": "HOAKS",
            "ai_risk": "SEDANG",
            "final_risk": "RENDAH",
            "topic": "Pendidikan",
            "actor": "Sekolah Fiktif E",
            "source": "Akun edukasi C",
            "username": "edukasi_update_tik",
            "title": "Klaim Beasiswa Fiktif Berbayar Mengatasnamakan Sekolah E",
            "caption": "Formulir pendaftaran beasiswa fiktif yang meminta biaya administrasi ilegal.",
            "notes": "Penyesuaian analis: Fakta menunjukkan program beasiswa tersebut sepenuhnya fiktif (HOAKS murni), namun sebaran terbatas sehingga risiko RENDAH.",
            "decision": "MODIFIED",
            "days_ago": 1,
        },
        {
            "ticket": "PS-20261022-SIM08",
            "platform": "youtube",
            "status": "VALIDATED",
            "ai_label": "DI_LUAR_KONTEKS",
            "final_label": "DI_LUAR_KONTEKS",
            "ai_risk": "SEDANG",
            "final_risk": "SEDANG",
            "topic": "Layanan Publik",
            "actor": "Unit Pelayanan A",
            "source": "Kanal informasi A",
            "username": "info_publik_terkini",
            "title": "Manipulasi Judul Kebijakan Tarif Subsidi Listrik",
            "caption": "Judul video menyebut subsidi dicabut total, padahal isi video membahas penyesuaian golongan komersial.",
            "notes": "Disetujui: Clickbait menyesatkan yang memicu keresahan publik (DI_LUAR_KONTEKS).",
            "decision": "APPROVED",
            "days_ago": 1,
        },
        {
            "ticket": "PS-20261022-SIM09",
            "platform": "youtube",
            "status": "MODIFIED",
            "ai_label": "PROVOKASI_SARA",
            "final_label": "UJARAN_KEBENCIAN",
            "ai_risk": "TINGGI",
            "final_risk": "RENDAH",
            "topic": "Lingkungan",
            "actor": "Komunitas F",
            "source": "Kanal video B",
            "username": "green_voice_channel",
            "title": "Kritik Pedas Aktivis Lingkungan Terhadap Komunitas F",
            "caption": "Video debat warga lokal mengenai pembuangan limbah komersial dengan kata-kata kasar.",
            "notes": "Penyesuaian analis: Mengandung hinaan kasar personal (UJARAN_KEBENCIAN) tanpa unsur SARA sistemik, risiko diturunkan ke RENDAH.",
            "decision": "MODIFIED",
            "days_ago": 0,
        },
        {
            "ticket": "PS-20261022-SIM10",
            "platform": "youtube",
            "status": "REJECTED",
            "ai_label": "HOAKS",
            "final_label": "BUKAN_PELANGGARAN",
            "ai_risk": "SEDANG",
            "final_risk": None,  # WAJIB None per Proposal
            "topic": "Layanan Publik",
            "actor": "Unit Pelayanan A",
            "source": "Kanal informasi A",
            "username": "satir_humor_publik",
            "title": "Video Satir Sketsa Pelayanan Publik",
            "caption": "Sketsa komedi teatrikal tentang birokrasi berbelit dengan watermark jelas parodi hiburan.",
            "notes": "Bukan pelanggaran: Konten parodi berizin dan tidak memenuhi unsur penyebaran hoaks berbahaya.",
            "decision": "FALSE_POSITIVE",
            "days_ago": 0,
        },
    ]

    base_time = datetime.utcnow()

    for idx, item in enumerate(simulation_specs, 1):
        created_dt = base_time - timedelta(days=item["days_ago"], hours=idx * 2)

        # 1. Upsert Account
        acct = db.query(Account).filter_by(platform=item["platform"], username=item["username"]).first()
        if not acct:
            acct = Account(
                platform=item["platform"],
                username=item["username"],
                display_name=item["username"].replace("_", " ").title(),
                profile_url=f"https://{item['platform']}.com/{item['username']}",
                followers_count=12000 * idx,
                total_posts=45 + idx * 5,
                is_verified=False,
                account_created_at=created_dt - timedelta(days=180),
            )
            db.add(acct)
            db.flush()

        # 2. Upsert Content
        canonical_url = f"https://www.{item['platform']}.com/watch?v={item['ticket'].lower()}"
        content = db.query(Content).filter_by(canonical_url=canonical_url).first()
        if not content:
            content = Content(
                account_id=acct.account_id,
                platform=item["platform"],
                canonical_url=canonical_url,
                platform_content_id=f"cnt_{idx:03d}",
                title=item["title"],
                caption_text=item["caption"],
                likes_count=150 * idx,
                views_count=3500 * idx,
                comments_count=45 * idx,
                posted_at=created_dt - timedelta(hours=3),
                extra_metadata={"seed": True, "proposal_spec": "Halaman 43-44"},
            )
            db.add(content)
            db.flush()

        # 3. Create Report
        topic_ent = topic_entities.get(item["topic"])
        source_ent = source_entities.get(item["source"])

        report = Report(
            ticket_number=item["ticket"],
            reporter_telegram_id=100101,
            reviewer_telegram_id=100102,
            content_id=content.content_id,
            intake_type="LINK",
            status=item["status"],
            ai_status="ANALYZED",
            ai_predicted_label=item["ai_label"],
            ai_risk_level=item["ai_risk"],
            ai_confidence_score=0.88,
            ai_summary=item["caption"],
            ai_reasoning={
                "poin_pengamatan": [item["title"]],
                "alasan_penilaian": f"Indikasi {item['ai_label']} berbasis observasi multimodal awal.",
                "indikasi_pelanggaran": [item["ai_label"]],
                "rekomendasi_tindak_lanjut": "Verifikasi manual oleh analis siber",
            },
            ai_output={"raw_prediction": item["ai_label"], "risk": item["ai_risk"]},
            ai_topic_raw=item["topic"],
            ai_actors_raw=[item["actor"]],
            ai_source_raw=item["source"],
            ai_source_type="CHANNEL" if "Kanal" in item["source"] else "USER_ACCOUNT",
            topic_id=topic_ent.entity_id if topic_ent else None,
            source_id=source_ent.entity_id if source_ent else None,
            review_decision=item["decision"],
            final_label=item["final_label"],
            final_risk=item["final_risk"],
            analyst_notes=item["notes"],
            created_at=created_dt,
            validated_at=created_dt + timedelta(minutes=45),
        )
        db.add(report)
        db.flush()

        # 4. Link ReportActor (composite PK: report_id, entity_id)
        actor_ent = actor_entities.get(item["actor"])
        if actor_ent:
            rep_actor = ReportActor(
                report_id=report.report_id,
                entity_id=actor_ent.entity_id,
                role="TARGET",
            )
            db.add(rep_actor)
            db.flush()

        # 5. Create Forensic Evidence (> 20 KB valid file)
        filename = f"{item['ticket']}_post.png"
        filepath = os.path.join("storage", "evidences", filename)
        if not os.path.exists(filepath):
            # Create a valid file > 20 KB (25,000 bytes) with header PNG
            with open(filepath, "wb") as f:
                # 8-byte PNG signature
                f.write(b"\x89PNG\r\n\x1a\n")
                # Padding to exceed 20 KB threshold
                f.write(b"\x00" * 25000)

        with open(filepath, "rb") as f:
            computed_sha = hashlib.sha256(f.read()).hexdigest()

        evidence = Evidence(
            report_id=report.report_id,
            source_type="SCRAPER_SCREENSHOT",
            storage_path=filepath,
            sha256=computed_sha,
            created_at=created_dt,
        )
        db.add(evidence)
        db.flush()

        # 6. Versioned KnowledgeEntry (NFR-07)
        # 1 active KB entry for validated/modified, inactive for rejected
        is_active = (item["status"] in ["VALIDATED", "MODIFIED"])
        deactivated_at = None if is_active else (created_dt + timedelta(minutes=46))

        # 768-D dummy normalized vector
        dummy_embedding = [0.0] * 768
        dummy_embedding[idx % 768] = 1.0

        kb_entry = KnowledgeEntry(
            report_id=report.report_id,
            ticket_number=item["ticket"],
            source_platform=item["platform"],
            account_username=item["username"],
            decision=item["status"],
            embedding=dummy_embedding,
            final_label=item["final_label"],
            final_risk=item["final_risk"],
            notes=item["notes"],
            summary_text=item["caption"],
            topic_id=topic_ent.entity_id if topic_ent else None,
            source_id=source_ent.entity_id if source_ent else None,
            is_active=is_active,
            deactivated_at=deactivated_at,
            created_at=created_dt + timedelta(minutes=45),
        )
        db.add(kb_entry)

        # 7. Audit log for report creation and validation
        db.add(
            AuditLog(
                action="REPORT_CREATED",
                actor_telegram_id=100101,
                entity_type="Report",
                entity_id=str(report.report_id),
                timestamp=created_dt,
            )
        )
        db.add(
            AuditLog(
                action=f"VALIDATION_{item['status']}",
                actor_telegram_id=100102,
                entity_type="Report",
                entity_id=str(report.report_id),
                details={"final_label": item["final_label"], "final_risk": item["final_risk"]},
                timestamp=created_dt + timedelta(minutes=45),
            )
        )

    db.commit()
    logger.info("Successfully seeded all 10 Proposal-compliant simulation reports!")
