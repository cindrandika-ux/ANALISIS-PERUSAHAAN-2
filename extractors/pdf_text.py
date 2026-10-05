"""Ekstraksi teks dari PDF teks via pdfplumber (utama) + PyMuPDF (cadangan).

Menandai PDF scan (teks minim) agar diteruskan ke modul OCR.
"""
from __future__ import annotations

import io

AMBANG_KARAKTER_SCAN = 200  # di bawah ini dianggap hasil scan/gambar


def ekstrak_dengan_pdfplumber(data: bytes) -> tuple[str, int]:
    """Ekstrak teks memakai pdfplumber.

    Returns:
        (teks_gabungan, jumlah_halaman). Teks kosong jika gagal.
    """
    import pdfplumber

    teks_halaman: list[str] = []
    jumlah = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        jumlah = len(pdf.pages)
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            teks_halaman.append(t)
    return ("\n".join(teks_halaman), jumlah)


def ekstrak_dengan_pymupdf(data: bytes) -> tuple[str, int]:
    """Ekstrak teks memakai PyMuPDF (fitz). Dipakai jika pdfplumber gagal."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    jumlah = doc.page_count
    teks_halaman = [page.get_text("text") or "" for page in doc]
    doc.close()
    return ("\n".join(teks_halaman), jumlah)


def ekstrak_teks(data: bytes) -> dict:
    """Ekstrak teks PDF dengan fallback otomatis.

    Args:
        data: Isi PDF dalam byte (sudah lolos validasi_pdf).

    Returns:
        dict: teks, jumlah_halaman, metode ('pdfplumber'|'pymupdf'|'gagal'),
        jumlah_karakter, perlu_ocr (bool).
    """
    teks, jumlah = "", 0
    metode = "gagal"
    try:
        teks, jumlah = ekstrak_dengan_pdfplumber(data)
        metode = "pdfplumber"
    except Exception:
        teks, jumlah = "", 0
    if not teks.strip():
        try:
            teks, jumlah = ekstrak_dengan_pymupdf(data)
            metode = "pymupdf"
        except Exception:
            teks, jumlah = "", 0
            metode = "gagal"
    jumlah_karakter = len(teks.strip())
    perlu_ocr = jumlah_karakter < AMBANG_KARAKTER_SCAN
    return {
        "teks": teks,
        "jumlah_halaman": jumlah,
        "metode": metode,
        "jumlah_karakter": jumlah_karakter,
        "perlu_ocr": perlu_ocr,
    }
