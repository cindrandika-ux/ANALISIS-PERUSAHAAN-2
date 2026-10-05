"""Perhitungan rasio keuangan (pure functions, teruji pytest).

Semua pembagian memakai safe_div: kembalikan None jika input hilang/nol,
jangan menebak atau membagi nol.
"""
from __future__ import annotations

RASIO_INFO: dict[str, dict] = {
    "current_ratio": {"rumus": "Aset Lancar / Liabilitas Jangka Pendek",
                      "penjelasan": "Kemampuan membayar kewajiban <1 tahun. >1,5 umumnya aman untuk dagang.",
                      "baik_jika": "naik"},
    "quick_ratio": {"rumus": "(Aset Lancar - Persediaan) / Liabilitas Jangka Pendek",
                    "penjelasan": "Likuiditas tanpa menjual persediaan. Relevan untuk dagang yang persediaannya besar.",
                    "baik_jika": "naik"},
    "cash_ratio": {"rumus": "Kas / Liabilitas Jangka Pendek",
                   "penjelasan": "Porsi kewajiban lancar yang bisa dibayar tunai segera.",
                   "baik_jika": "naik"},
    "der": {"rumus": "Total Liabilitas / Ekuitas",
            "penjelasan": "Leverage. Makin tinggi makin berisiko (beban bunga).",
            "baik_jika": "turun"},
    "debt_ratio": {"rumus": "Total Liabilitas / Total Aset",
                   "penjelasan": "Porsi aset yang dibiayai utang.",
                   "baik_jika": "turun"},
    "interest_coverage": {"rumus": "Laba Usaha (EBIT) / Beban Bunga",
                          "penjelasan": "Berapa kali laba menutup bunga. <1,5 rawan gagal bayar.",
                          "baik_jika": "naik"},
    "gross_margin": {"rumus": "Laba Kotor / Pendapatan",
                     "penjelasan": "Margin dagang setelah HPP. HPP dagang = Pendapatan - Laba Kotor.",
                     "baik_jika": "naik"},
    "operating_margin": {"rumus": "Laba Usaha / Pendapatan",
                         "penjelasan": "Efisiensi operasi setelah beban usaha.",
                         "baik_jika": "naik"},
    "net_margin": {"rumus": "Laba Bersih / Pendapatan",
                   "penjelasan": "Sisa tiap Rp1 penjualan setelah semua beban & pajak.",
                   "baik_jika": "naik"},
    "roa": {"rumus": "Laba Bersih / Total Aset",
            "penjelasan": "Imbal tiap Rp1 aset.",
            "baik_jika": "naik"},
    "roe": {"rumus": "Laba Bersih / Ekuitas",
            "penjelasan": "Imbal bagi pemilik. Hati-hati jika ekuitas kecil karena rugi akumulasi.",
            "baik_jika": "naik"},
    "asset_turnover": {"rumus": "Pendapatan / Total Aset",
                       "penjelasan": "Efisiensi aset menghasilkan penjualan dagang.",
                       "baik_jika": "naik"},
    "perputaran_piutang": {"rumus": "Pendapatan / Piutang",
                           "penjelasan": "Makin tinggi makin cepat menagih. Turun bisa berarti piutang macet.",
                           "baik_jika": "naik"},
    "perputaran_persediaan": {"rumus": "(Pendapatan - Laba Kotor) / Persediaan",
                               "penjelasan": "HPP dagang dibagi persediaan. Rendah = barang menumpuk.",
                               "baik_jika": "naik"},
    "cfo_laba": {"rumus": "CFO / Laba Bersih",
                 "penjelasan": "Kualitas laba: >1 berarti laba didukung kas operasi.",
                 "baik_jika": "naik"},
    "cfo_liab_lancar": {"rumus": "CFO / Liabilitas Jangka Pendek",
                         "penjelasan": "Kemampuan kas operasi menutup kewajiban lancar.",
                         "baik_jika": "naik"},
}


def safe_div(a: float | None, b: float | None) -> float | None:
    """Bagi aman: None jika input hilang atau penyebut nol."""
    if a is None or b is None:
        return None
    try:
        if float(b) == 0:
            return None
        return float(a) / float(b)
    except (TypeError, ValueError):
        return None


def hitung_rasio(d: dict) -> dict:
    """Hitung 16 rasio dari satu tahun data keuangan.

    Args:
        d: dict akun (kas, piutang, persediaan, aset_lancar, total_aset,
            liab_pendek, total_liab, ekuitas, pendapatan, laba_kotor,
            laba_usaha, beban_bunga, laba_bersih, cfo). Nilai hilang = None.

    Returns:
        dict nama_rasio -> float|None (None = tidak dapat dihitung).
    """
    hpp = None
    if d.get("pendapatan") is not None and d.get("laba_kotor") is not None:
        hpp = float(d["pendapatan"]) - float(d["laba_kotor"])

    return {
        "current_ratio": safe_div(d.get("aset_lancar"), d.get("liab_pendek")),
        "quick_ratio": safe_div(
            (float(d["aset_lancar"]) - float(d["persediaan"]))
            if d.get("aset_lancar") is not None and d.get("persediaan") is not None else None,
            d.get("liab_pendek")),
        "cash_ratio": safe_div(d.get("kas"), d.get("liab_pendek")),
        "der": safe_div(d.get("total_liab"), d.get("ekuitas")),
        "debt_ratio": safe_div(d.get("total_liab"), d.get("total_aset")),
        "interest_coverage": safe_div(d.get("laba_usaha"), d.get("beban_bunga")),
        "gross_margin": safe_div(d.get("laba_kotor"), d.get("pendapatan")),
        "operating_margin": safe_div(d.get("laba_usaha"), d.get("pendapatan")),
        "net_margin": safe_div(d.get("laba_bersih"), d.get("pendapatan")),
        "roa": safe_div(d.get("laba_bersih"), d.get("total_aset")),
        "roe": safe_div(d.get("laba_bersih"), d.get("ekuitas")),
        "asset_turnover": safe_div(d.get("pendapatan"), d.get("total_aset")),
        "perputaran_piutang": safe_div(d.get("pendapatan"), d.get("piutang")),
        "perputaran_persediaan": safe_div(hpp, d.get("persediaan")),
        "cfo_laba": safe_div(d.get("cfo"), d.get("laba_bersih")),
        "cfo_liab_lancar": safe_div(d.get("cfo"), d.get("liab_pendek")),
    }
