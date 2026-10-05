"""Fallback OCR untuk PDF hasil scan via pytesseract + PyMuPDF.

Jika biner Tesseract tidak tersedia, kembalikan pesan ramah (tidak crash).
Path biner dibaca dari env TESSERACT_CMD atau PATH sistem.
"""
from __future__ import annotations

import io
import os
import shutil


def cek_tesseract_tersedia() -> dict:
    """Cek ketersediaan biner Tesseract OCR.

    Returns:
        dict: tersedia (bool), path (str|None), pesan (str).
    """
    env_path = (os.getenv("TESSERACT_CMD") or "").strip()
    kandidat = [env_path] if env_path else []
    which = shutil.which("tesseract")
    if which:
        kandidat.append(which)
    for p in kandidat:
        if p and os.path.isfile(p):
            return {"tersedia": True, "path": p, "pesan": f"Tesseract ditemukan: {p}"}
    # Mungkin pytesseract memakai PATH tanpa path absolut
    if which:
        return {"tersedia": True, "path": which, "pesan": f"Tesseract ditemukan: {which}"}
    return {
        "tersedia": False,
        "path": None,
        "pesan": ("Tesseract tidak ditemukan. Instal Tesseract OCR Windows, "
                  "lalu isi TESSERACT_CMD di .env. "
                  "Contoh: C:\\Program Files\\Tesseract-OCR\\tesseract.exe"),
    }


def perlu_ocr(teks: str, ambang: int = 200) -> bool:
    """True jika teks terlalu sedikit sehingga diduga PDF scan."""
    return len((teks or "").strip()) < ambang


def ocr_pdf_scan(data: bytes, dpi: int = 300, bahasa: str = "ind+eng") -> dict:
    """Jalankan OCR per halaman PDF scan.

    Args:
        data: Isi PDF dalam byte.
        dpi: Resolusi render (makin tinggi makin akurat, makin lambat).
        bahasa: Kode bahasa Tesseract ('ind' butuh traineddata Indonesia).

    Returns:
        dict: ok (bool), teks (str), halaman (int), pesan (str|None).
    """
    status = cek_tesseract_tersedia()
    if not status["tersedia"]:
        return {"ok": False, "teks": "", "halaman": 0, "pesan": status["pesan"]}

    try:
        import fitz  # PyMuPDF untuk render halaman jadi gambar
        from PIL import Image
        import pytesseract
    except ImportError as e:
        return {"ok": False, "teks": "", "halaman": 0,
                "pesan": f"Library OCR belum terinstal: {e}"}

    if status["path"]:
        try:
            import pytesseract as _pt
            _pt.pytesseract.tesseract_cmd = status["path"]
        except Exception:
            pass

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        return {"ok": False, "teks": "", "halaman": 0,
                "pesan": f"Gagal membuka PDF untuk OCR: {e}"}

    zoom = dpi / 72.0
    hasil: list[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                t = pytesseract.image_to_string(img, lang=bahasa)
            except Exception:
                # Fallback ke Inggris bila traineddata 'ind' belum ada
                t = pytesseract.image_to_string(img, lang="eng")
            hasil.append(t or "")
    except Exception as e:
        doc.close()
        return {"ok": False, "teks": "", "halaman": 0,
                "pesan": f"OCR gagal di tengah jalan: {e}"}
    halaman = doc.page_count
    doc.close()
    teks = "\n".join(hasil)
    if not teks.strip():
        return {"ok": False, "teks": "", "halaman": halaman,
                "pesan": "OCR selesai tetapi tidak ada teks terbaca. Coba naikkan resolusi atau cek kualitas scan."}
    return {"ok": True, "teks": teks, "halaman": halaman, "pesan": None}
