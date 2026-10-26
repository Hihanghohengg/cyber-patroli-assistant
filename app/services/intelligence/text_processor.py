"""Indonesian text processor for social intelligence analysis.

Provides text cleaning, normalization, Indonesian stopword filtering,
tokenization, keyword/hashtag extraction, and canonical slug generation.
"""

import re
import unicodedata
from collections import Counter
from typing import List, Set, Tuple

# Comprehensive Indonesian stopwords list
INDONESIAN_STOPWORDS: Set[str] = {
    "ada", "adanya", "adalah", "adapun", "agak", "agaknya", "agar", "akan", "akankah",
    "akhir", "akhiri", "akhirnya", "aku", "akulah", "amat", "amatlah", "anda", "andalah",
    "antar", "antara", "antaranya", "apa", "apaan", "apabila", "apakah", "apalagi",
    "apatah", "artinya", "asal", "asalkan", "atas", "atau", "ataukah", "ataupun", "awal",
    "awalnya", "bagai", "bagaikan", "bagaimana", "bagaimanakah", "bagaimanapun", "bagi",
    "bagian", "bahkan", "bahwa", "bahwasanya", "baik", "bakal", "bakalan", "balik",
    "banyak", "banyaknya", "bapak", "baru", "bawah", "beberapa", "begini", "beginian",
    "beginikah", "beginilah", "begitu", "begitukah", "begitulah", "begitupun", "bekerja",
    "belakang", "belakangan", "belum", "belumlah", "benar", "benarkah", "benarlah",
    "berada", "berakhir", "berakhirlah", "berakhirnya", "berapa", "berapakah", "berapalah",
    "berapapun", "berarti", "berawal", "berbagai", "berdatangan", "beri", "berikan",
    "berikut", "berikutnya", "berjumlah", "berkala", "berkali-kali", "berkata", "berkehendak",
    "berkeinginan", "berkenaan", "berlainan", "berlalu", "berlangsung", "berlebihan",
    "bermacam", "bermacam-macam", "bermaksud", "bermula", "bersama", "bersama-sama",
    "bersiap", "bersiap-siap", "bertanya", "bertanya-tanya", "berturut", "berturut-turut",
    "bertutur", "berujar", "berupa", "besar", "betul", "betulkah", "biasa", "biasanya",
    "bila", "bilakah", "bisa", "bisakah", "boleh", "bolehkah", "bolehlah", "buat",
    "bukan", "bukankah", "bukanlah", "bukannya", "cuma", "cukup", "cukupkah", "cukuplah",
    "dan", "dapat", "dari", "daripada", "dekat", "demi", "demikian", "demikianlah",
    "dengan", "depan", "di", "dia", "diakhiri", "diakhirinya", "dialah", "diantara",
    "diantaranya", "diberi", "diberikan", "diberikannya", "dibuat", "dibuatnya", "didapat",
    "didatangkan", "digunakan", "diibaratkan", "diibaratkannya", "diingat", "diingatkan",
    "diinginkan", "dijawab", "dijelaskan", "dijelaskannya", "dikarenakan", "dikatakan",
    "dikatakannya", "dikerjakan", "diketahui", "diketahuinya", "dikira", "dilakukan",
    "dilalui", "dilihat", "dimaksud", "dimaksudkan", "dimaksudkannya", "dimaksudnya",
    "diminta", "dimintai", "dimisalkan", "dimulai", "dimulailah", "dimulainya", "dimungkinkan",
    "dini", "dipastikan", "diperbuat", "diperbuatnya", "dipergunakan", "diperkirakan",
    "diperlihatkan", "diperlukan", "diperlukannya", "dipersoalkan", "dipertanyakan",
    "dipunyai", "diri", "dirinya", "disampaikan", "disebut", "disebutkan", "disebutkannya",
    "disini", "disinilah", "ditambahkan", "ditandaskan", "ditanya", "ditanyai", "ditanyakan",
    "ditegaskan", "ditemukan", "ditentukan", "ditentukannya", "dituturkan", "dituturkannya",
    "diucapkan", "diucapkannya", "diungkapkan", "dong", "dua", "dulu", "empat", "enggak",
    "gak", "nggak", "gua", "gue", "lo", "lu", "kamu", "kita", "kalian", "mereka", "ia",
    "ini", "itu", "jadi", "jangan", "jika", "kalau", "kami", "karena", "kepadanya",
    "ke", "pada", "oleh", "secara", "sebuah", "suatu", "tentang", "terhadap", "untuk",
    "yaitu", "yakni", "yang", "sudah", "telah", "sedang", "masih", "belum", "saja",
    "pun", "lagi", "pula", "deh", "kan", "kok", "sih", "ya", "yah", "nih", "tuh",
    "loh", "lah", "banget", "sangat", "paling", "terlalu", "cenderung", "terkait",
}

# Try loading Sastrawi stemmer if installed
_STEMMER = None
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    _STEMMER = StemmerFactory().create_stemmer()
except Exception:
    _STEMMER = None


class IndonesianTextProcessor:
    """Preprocesses and normalizes Indonesian text for topic modeling and clustering."""

    def __init__(self, use_stemmer: bool = False):
        self.use_stemmer = use_stemmer and (_STEMMER is not None)
        self.stopwords = INDONESIAN_STOPWORDS

    @staticmethod
    def remove_urls(text: str) -> str:
        """Remove http/https and www URLs."""
        return re.sub(r"https?://\S+|www\.\S+", " ", text)

    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extract hashtags (#tag) and normalize them."""
        raw_tags = re.findall(r"#([a-zA-Z0-9_]+)", text)
        return [f"#{tag.lower()}" for tag in raw_tags]

    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extract user mentions (@username)."""
        raw_mentions = re.findall(r"@([a-zA-Z0-9_]+)", text)
        return [f"@{m.lower()}" for m in raw_mentions]

    @classmethod
    def clean_text(cls, text: str, keep_hashtags: bool = True) -> str:
        """Clean raw text: remove URLs, strip emojis, normalize unicode, strip mentions."""
        if not text:
            return ""

        # Normalize unicode (decompose accents, ligature)
        text = unicodedata.normalize("NFKD", text)

        # Remove URLs
        text = cls.remove_urls(text)

        # Remove user mentions
        text = re.sub(r"@\w+", " ", text)

        # Handle hashtags
        if not keep_hashtags:
            text = re.sub(r"#\w+", " ", text)
        else:
            text = re.sub(r"#", " ", text)

        # Remove emojis and non-alphanumeric (keep spaces and standard punctuation for splitting)
        text = re.sub(r"[^\w\s-]", " ", text)

        # Collapse multiple whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def tokenize(self, text: str, filter_stopwords: bool = True) -> List[str]:
        """Clean, lowercase, and tokenize text into words, removing stopwords."""
        cleaned = self.clean_text(text).lower()
        # Extract word tokens with length >= 3
        words = re.findall(r"\b[a-z]{3,}\b", cleaned)

        if filter_stopwords:
            words = [w for w in words if w not in self.stopwords]

        if self.use_stemmer and _STEMMER is not None:
            words = [_STEMMER.stem(w) for w in words]

        return words

    def extract_keywords(
        self,
        text: str,
        top_k: int = 10,
        min_word_len: int = 3,
        include_bigrams: bool = True
    ) -> List[str]:
        """Extract prominent keywords and optional bigrams based on frequency."""
        tokens = self.tokenize(text, filter_stopwords=True)
        if not tokens:
            return []

        # Count unigrams
        unigram_counts = Counter(tokens)

        # Optionally build bigrams
        candidates = list(unigram_counts.items())
        if include_bigrams and len(tokens) >= 2:
            bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
            bigram_counts = Counter(bigrams)
            # Only consider bigrams that appear at least once
            candidates.extend(bigram_counts.items())

        # Sort by frequency descending, then by length
        candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)

        return [word for word, _ in candidates[:top_k]]

    @staticmethod
    def to_canonical_slug(text: str) -> str:
        """Create a standardized alphanumeric slug for canonical topic names."""
        cleaned = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", cleaned).strip("-")
        return slug[:100] or "topik-tidak-diketahui"

    def compute_jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard token overlap similarity (fast fallback metric)."""
        tokens_a = set(self.tokenize(text_a))
        tokens_b = set(self.tokenize(text_b))
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union > 0 else 0.0
