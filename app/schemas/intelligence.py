"""Pydantic schemas for intelligence pipeline outputs.

Defines the structured 5W+1H extraction schema expected from Gemini AI
and response schemas used by the dashboard API.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Analysis5W1H(BaseModel):
    """Structured 5W+1H extraction output from Gemini AI.

    Each field can be None / 'unknown' — the AI must NOT fabricate facts.
    """
    what: Optional[str] = Field(None, description="Apa isu atau peristiwa yang dibahas?")
    who: Optional[str] = Field(None, description="Siapa pihak yang disebutkan atau terlibat?")
    when_info: Optional[str] = Field(None, description="Kapan peristiwa terjadi atau dibahas?")
    where_info: Optional[str] = Field(None, description="Di mana peristiwa terjadi?")
    why: Optional[str] = Field(None, description="Apa penyebab atau latar belakang?")
    how: Optional[str] = Field(None, description="Bagaimana peristiwa terjadi atau berkembang?")

    summary: str = Field("", description="Ringkasan konten dalam 1-2 kalimat.")
    main_topic: Optional[str] = Field(None, description="Topik utama konten.")
    sub_topics: List[str] = Field(default_factory=list, description="Sub-topik terkait.")
    keywords: List[str] = Field(default_factory=list, description="Kata kunci penting.")
    hashtags: List[str] = Field(default_factory=list, description="Hashtag yang ditemukan.")
    named_entities: List[str] = Field(default_factory=list, description="Entitas bernama (orang, organisasi, lokasi).")

    sentiment: Literal["POSITIF", "NEGATIF", "NETRAL", "CAMPURAN"] = Field(
        "NETRAL", description="Sentimen keseluruhan konten."
    )
    tone: Optional[str] = Field(None, description="Nada percakapan (informatif, provokatif, satiris, dsb).")

    category: Literal[
        "Politik", "Bencana Alam", "Lingkungan", "Keamanan",
        "Ekonomi", "Sosial", "Teknologi", "Kesehatan",
        "Pendidikan", "Hukum", "Lainnya",
    ] = Field("Lainnya", description="Kategori isu.")

    relevance_score: float = Field(0.5, ge=0.0, le=1.0, description="Skor relevansi konten.")
    urgency_score: float = Field(0.3, ge=0.0, le=1.0, description="Skor urgensi konten.")
    confidence_score: float = Field(0.5, ge=0.0, le=1.0, description="Keyakinan AI terhadap analisis ini.")

    misinfo_indicators: List[str] = Field(
        default_factory=list,
        description="Indikator potensi misinformasi. Kosong jika tidak terdeteksi."
    )

    information_basis: Literal["EKSPLISIT", "INFERENSI", "CAMPURAN"] = Field(
        "CAMPURAN",
        description="Apakah informasi dinyatakan eksplisit, merupakan inferensi AI, atau campuran."
    )

    @field_validator("keywords", "hashtags", "named_entities", "sub_topics", "misinfo_indicators", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v or []
