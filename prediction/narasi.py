"""Narasi rule-based Bahasa Indonesia (angka dari Python, bukan LLM).

Memilih 3 pendukung + 3 risiko dari sub-skor tertinggi/terendah,
lalu merangkai ringkasan + disclaimer wajib.
"""
from __future__ import annotations

DISCLAIMER = (
    "Disclaimer: hasil ini adalah estimasi berbasis data historis dan pola "
    "statistik sederhana, bukan jaminan kinerja masa depan dan bukan nasihat "
    "investasi/keuangan. Verifikasi dengan auditor/AKJ sebelum mengambil keputusan."
)

LABEL_ID: dict[str, str] = {
    "current_ratio": "Rasio lancar", "quick_ratio": "Rasio cepat",
    "cash_ratio": "Rasio kas", "der": "DER (utang/ekuitas)",
    "debt_ratio": "Rasio utang/aset", "interest_coverage": "Cakupan bunga",
    "net_margin": "Margin bersih", "roa": "ROA", "roe": "ROE",
    "asset_turnover": "Perputaran aset", "perputaran_persediaan": "Perputaran persediaan",
    "cfo_laba": "CFO/laba bersih", "gross_margin": "Margin kotor",
    "operating_margin": "Margin operasi", "perputaran_piutang": "Perputaran piutang",
    "cfo_liab_lancar": "CFO/kewajiban lancar",
}


def pilih_pendukung_risiko(skor_detail: dict) -> dict:
    """Pilih 3 pendukung (skor tertinggi) dan 3 risiko (skor terendah).

    Hanya dari skor yang tidak None. Jika <3 tersedia, kembalikan seadanya.
    """
    valid = [(k, v) for k, v in skor_detail.items() if v is not None]
    teratas = sorted(valid, key=lambda x: x[1], reverse=True)[:3]
    terbawah = sorted(valid, key=lambda x: x[1])[:3]
    return {"pendukung": teratas, "risiko": terbawah}


def kategori_final(kategori_skor: str, kategori_z: str) -> str:
    """Gabungan konservatif: Berisiko jika salah satu Berisiko;
    Sehat hanya jika keduanya Sehat; selain itu Waspada."""
    if "TIDAK" in kategori_skor or "TIDAK" in kategori_z:
        return "Waspada" if "Berisiko" not in (kategori_skor, kategori_z) else "Berisiko"
    if kategori_skor == "Berisiko" or kategori_z == "Berisiko":
        return "Berisiko"
    if kategori_skor == "Sehat" and kategori_z == "Sehat":
        return "Sehat"
    return "Waspada"


def buat_narasi(nama: str, tahun: int, skor_total: float | None,
                kategori: str, z: float | None, kat_z: str,
                pendukung: list, risiko: list, proyeksi_ok: bool) -> str:
    """Susun ringkasan Bahasa Indonesia + disclaimer."""
    def fmt(x):
        return "tidak ditemukan" if x is None else f"{x:,.2f}"

    p = ", ".join(f"{LABEL_ID.get(k, k)} ({v:.0f})" for k, v in pendukung) or "tidak cukup data"
    r = ", ".join(f"{LABEL_ID.get(k, k)} ({v:.0f})" for k, v in risiko) or "tidak cukup data"
    kal_proyeksi = ("Proyeksi tahun depan dihitung dengan regresri linear dari 3 tahun historis."
                    if proyeksi_ok else
                    "Proyeksi tidak ditampilkan karena data historis <3 tahun.")
    return (
        f"{nama} tahun {tahun}: kategori {kategori} dengan skor {fmt(skor_total)}/100 "
        f"dan Altman Z'' {fmt(z)} ({kat_z}). "
        f"Faktor pendukung: {p}. Faktor risiko: {r}. {kal_proyeksi} {DISCLAIMER}"
    )
