from typing import List, Literal, Union
from pydantic import BaseModel, Field, field_validator


class AIPatrolAnalysis(BaseModel):
    """Structured JSON output expected from the multimodal AI model.

    Standardized schema for cyber patrol triage and intelligence analysis.
    Extended with PRD v3 fields: topik, aktor_target, sumber_konten, tipe_sumber.
    """
    status_keamanan: Literal["AMAN", "POTENSI_BAHAYA", "BERPOTENSI_BAHAYA"] = Field(
        default="AMAN",
        description="Klasifikasi keamanan: AMAN atau POTENSI_BAHAYA",
    )
    kategori_utama: Literal[
        "HOAKS",
        "UJARAN_KEBENCIAN",
        "PROVOKASI_SARA",
        "PENIPUAN_FINANSIAL",
        "DI_LUAR_KONTEKS",
        "NETRAL",
    ] = Field(
        default="NETRAL",
        description="Kategori pelanggaran konten utama.",
    )
    tingkat_risiko: Literal["RENDAH", "SEDANG", "TINGGI"] = Field(
        default="RENDAH",
        description="Tingkat risiko dampak konten: RENDAH, SEDANG, TINGGI",
    )
    skor_keyakinan: float = Field(
        ge=0.0,
        le=1.0,
        default=0.85,
        description="Keyakinan internal model AI (0.0 sampai 1.0).",
    )
    ringkasan_narasi: str = Field(
        default="",
        description="Deskripsi lugas mengenai inti klaim atau narasi yang dibangun dalam 1-2 kalimat.",
    )

    # --- PRD v3 Extensions ---
    topik: str = Field(
        default="",
        description="Topik utama konten, singkat (contoh: kenaikan harga BBM, pemilu, bansos).",
    )
    aktor_target: List[str] = Field(
        default_factory=list,
        description="Tokoh, institusi, atau kelompok yang menjadi sasaran konten (boleh kosong).",
    )
    sumber_konten: str = Field(
        default="",
        description="Nama media atau kanal asal konten (contoh: Tribunnews, Kompas, atau nama akun jika bukan media).",
    )
    tipe_sumber: Literal[
        "MEDIA_ONLINE",
        "MEDIA_TV",
        "AKUN_INDIVIDU",
        "KOMUNITAS",
        "LAINNYA",
    ] = Field(
        default="LAINNYA",
        description="Tipe sumber konten.",
    )

    poin_pengamatan: List[str] = Field(
        default_factory=list,
        description="Poin-poin temuan faktual pada teks, audio, atau visual.",
    )
    alasan_penilaian: Union[str, List[str]] = Field(
        default="",
        description="Penjelasan terstruktur mengapa konten digolongkan ke tingkat risiko dan kategori tersebut.",
    )
    indikasi_pelanggaran: str = Field(
        default="",
        description="Aturan/regulasi atau etika ruang siber yang berpotensi dilanggar (misal: UU ITE, KUHP, SE Kapolri).",
    )
    rekomendasi_tindak_lanjut: str = Field(
        default="",
        description="Prioritas verifikasi analis / rekomendasi klarifikasi fakta / pengawasan berkala.",
    )
    butuh_verifikasi_mendalam: bool = Field(
        default=False,
        description="True jika konten memerlukan pendalaman forensik atau klarifikasi fakta instansi terkait.",
    )

    @field_validator("alasan_penilaian", mode="before")
    @classmethod
    def normalize_alasan(cls, v):
        if isinstance(v, list):
            return "\n".join([f"- {item}" for item in v])
        return v or ""

    @field_validator("aktor_target", mode="before")
    @classmethod
    def normalize_aktor(cls, v):
        if isinstance(v, str):
            return [v]
        return v or []

    @property
    def kategori_isu(self) -> str:
        """Alias for backward compatibility."""
        return self.kategori_utama
