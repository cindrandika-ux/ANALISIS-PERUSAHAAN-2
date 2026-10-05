"""Buat PDF ringkasan analisis (Rupiah, Bahasa Indonesia)."""
from __future__ import annotations


def buat_pdf(nama: str, tahun: int, kategori: str, skor_total: float | None,
             z: float | None, kat_z: str, rasio: dict,
             pendukung: list, risiko: list, narasi: str, disclaimer: str) -> bytes:
    """Susun PDF satu halaman-plus, kembalikan byte siap diunduh.

    Args:
        nama: Nama perusahaan. tahun: Tahun laporan.
        kategori/skor_total/z/kat_z: Hasil prediksi.
        rasio: dict nama->nilai. pendukung/risiko: list[(nama, skor)].
        narasi/disclaimer: Teks Bahasa Indonesia.

    Returns:
        bytes PDF (diawali %PDF).
    """
    from fpdf import FPDF

    def fmt_rp(x):
        if x is None:
            return "tidak ditemukan"
        return f"Rp{x:,.0f}".replace(",", ".")

    def fmt_rasio(x, persen=False):
        if x is None:
            return "n/d"
        return f"{x*100:.1f}%" if persen else f"{x:.2f}"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def judul(txt: str, size: int = 12, bold: bool = True) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.multi_cell(0, 8, txt, new_x="LMARGIN", new_y="NEXT")

    def isi(txt: str, size: int = 10) -> None:
        pdf.set_font("Helvetica", "", size)
        pdf.multi_cell(0, 6, txt, new_x="LMARGIN", new_y="NEXT")

    judul(f"Prediktor Kesehatan Keuangan - {nama} ({tahun})", size=14)
    skor_txt = "tidak ditemukan" if skor_total is None else f"{skor_total:.1f}/100"
    z_txt = "tidak ditemukan" if z is None else f"{z:.2f} ({kat_z})"
    isi(f"Kategori: {kategori} | Skor: {skor_txt} | Altman Z'': {z_txt}", size=11)
    pdf.ln(2)
    judul("Rasio kunci")
    persen_keys = {"gross_margin", "operating_margin", "net_margin", "roa", "roe", "debt_ratio"}
    for k in ["current_ratio", "quick_ratio", "cash_ratio", "der", "debt_ratio",
              "interest_coverage", "gross_margin", "net_margin", "roa", "roe",
              "asset_turnover", "perputaran_persediaan", "cfo_laba"]:
        isi(f"- {k}: {fmt_rasio(rasio.get(k), k in persen_keys)}")
    pdf.ln(2)
    judul("Faktor pendukung & risiko")
    isi("Pendukung: " + (", ".join(f"{k} ({v:.0f})" for k, v in pendukung) or "-"))
    isi("Risiko: " + (", ".join(f"{k} ({v:.0f})" for k, v in risiko) or "-"))
    pdf.ln(2)
    judul("Ringkasan")
    isi(narasi)
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 6, disclaimer, new_x="LMARGIN", new_y="NEXT")
    _ = fmt_rp  # dipakai template lanjutan bila perlu nominal
    out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
