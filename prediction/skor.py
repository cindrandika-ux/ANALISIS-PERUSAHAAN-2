"""Skor kesehatan 0-100 berbasis rasio dengan bobot yang bisa diatur.

Setiap rasio dinilai 0-100 via interpolasi linear antara batas buruk-baik,
lalu dirata-rata per grup dan dibobot. Transparan untuk presentasi.
"""
from __future__ import annotations

BOBOT_DEFAULT: dict[str, float] = {
    "likuiditas": 0.25,
    "solvabilitas": 0.25,
    "profitabilitas": 0.30,
    "aktivitas_kas": 0.20,
}

# (batas_buruk -> 0, batas_baik -> 100). 'naik' = makin tinggi makin baik.
KONFIG_NAIK: dict[str, tuple[float, float]] = {
    "current_ratio": (1.0, 2.0),
    "quick_ratio": (0.5, 1.2),
    "cash_ratio": (0.1, 0.5),
    "interest_coverage": (1.5, 5.0),
    "gross_margin": (0.10, 0.35),
    "operating_margin": (0.03, 0.15),
    "net_margin": (0.0, 0.15),
    "roa": (0.0, 0.15),
    "roe": (0.0, 0.20),
    "asset_turnover": (0.5, 1.5),
    "perputaran_piutang": (2.0, 8.0),
    "perputaran_persediaan": (1.0, 5.0),
    "cfo_laba": (0.0, 1.2),
    "cfo_liab_lancar": (0.0, 0.6),
}
# 'turun' = makin rendah makin baik (baik, buruk).
KONFIG_TURUN: dict[str, tuple[float, float]] = {
    "der": (0.5, 2.0),
    "debt_ratio": (0.3, 0.8),
}

GRUP: dict[str, list[str]] = {
    "likuiditas": ["current_ratio", "quick_ratio", "cash_ratio"],
    "solvabilitas": ["der", "debt_ratio", "interest_coverage"],
    "profitabilitas": ["net_margin", "roa", "roe"],
    "aktivitas_kas": ["asset_turnover", "perputaran_persediaan", "cfo_laba"],
}


def _skor_naik(nilai: float | None, buruk: float, baik: float) -> float | None:
    if nilai is None:
        return None
    if nilai <= buruk:
        return 0.0
    if nilai >= baik:
        return 100.0
    return (nilai - buruk) / (baik - buruk) * 100.0


def _skor_turun(nilai: float | None, baik: float, buruk: float) -> float | None:
    if nilai is None:
        return None
    if nilai <= baik:
        return 100.0
    if nilai >= buruk:
        return 0.0
    return (buruk - nilai) / (buruk - baik) * 100.0


def skor_sub_rasio(nama: str, nilai: float | None) -> float | None:
    """Nilai 0-100 untuk satu rasio (None jika input hilang)."""
    if nilai is None:
        return None
    if nama in KONFIG_NAIK:
        buruk, baik = KONFIG_NAIK[nama]
        return _skor_naik(nilai, buruk, baik)
    if nama in KONFIG_TURUN:
        baik, buruk = KONFIG_TURUN[nama]
        return _skor_turun(nilai, baik, buruk)
    return None


def hitung_skor(rasio: dict, bobot: dict | None = None) -> dict:
    """Hitung skor total dan per grup.

    Args:
        rasio: dict nama_rasio -> float|None (dari analysis.hitung_rasio).
        bobot: dict grup -> bobot (dinormalisasi otomatis). Default BOBOT_DEFAULT.

    Returns:
        dict: skor_total (float|None), skor_grup, skor_detail, bobot_dipakai.
    """
    b = dict(BOBOT_DEFAULT if bobot is None else bobot)
    total_b = sum(v for v in b.values() if v > 0) or 1.0
    b = {k: v / total_b for k, v in b.items()}

    skor_detail: dict[str, float | None] = {}
    for nama in list(KONFIG_NAIK.keys()) + list(KONFIG_TURUN.keys()):
        skor_detail[nama] = skor_sub_rasio(nama, rasio.get(nama))

    skor_grup: dict[str, float | None] = {}
    for grup, anggota in GRUP.items():
        nilai = [skor_detail[a] for a in anggota if skor_detail.get(a) is not None]
        skor_grup[grup] = sum(nilai) / len(nilai) if nilai else None

    pembilang = sum(skor_grup[g] * b[g] for g in skor_grup
                    if skor_grup[g] is not None and g in b)
    penyebut = sum(b[g] for g in skor_grup if skor_grup[g] is not None and g in b)
    skor_total = pembilang / penyebut if penyebut > 0 else None
    return {"skor_total": skor_total, "skor_grup": skor_grup,
            "skor_detail": skor_detail, "bobot_dipakai": b}


def kategori_dari_skor(skor_total: float | None) -> str:
    """Sehat (>=70) / Waspada (50-70) / Berisiko (<50) / TIDAK_DAPAT_DINILAI."""
    if skor_total is None:
        return "TIDAK_DAPAT_DINILAI"
    if skor_total >= 70:
        return "Sehat"
    if skor_total >= 50:
        return "Waspada"
    return "Berisiko"
