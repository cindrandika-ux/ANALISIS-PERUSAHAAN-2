"""Validasi tipe dan ukuran file PDF.

Memeriksa isi sebenarnya (magic bytes), bukan hanya ekstensi.
"""
from __future__ import annotations


def validasi_pdf(nama_file: str, data: bytes, max_mb: float = 20.0) -> dict:
    """Validasi file PDF dari nama dan isi byte.

    Args:
        nama_file: Nama file unggahan (mis. 'laporan.pdf').
        data: Isi file dalam byte.
        max_mb: Batas ukuran dalam megabyte.

    Returns:
        dict dengan kunci: ok (bool), errors (list[str]),
        ukuran_byte (int), ukuran_mb (float).
    """
    errors: list[str] = []
    ukuran_byte = len(data) if data is not None else 0
    ukuran_mb = ukuran_byte / (1024 * 1024) if ukuran_byte else 0.0

    if not data:
        errors.append("File kosong atau gagal dibaca.")
        return {"ok": False, "errors": errors,
                "ukuran_byte": 0, "ukuran_mb": 0.0}

    nama_rendah = (nama_file or "").lower()
    if not nama_rendah.endswith(".pdf"):
        errors.append("Ekstensi file harus .pdf.")

    # Magic bytes PDF: file valid diawali '%PDF'
    if not data.startswith(b"%PDF"):
        errors.append("Isi file bukan PDF valid (magic bytes '%PDF' tidak ditemukan).")

    if ukuran_mb > max_mb:
        errors.append(
            f"Ukuran {ukuran_mb:.2f} MB melebihi batas {max_mb:.0f} MB."
        )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "ukuran_byte": ukuran_byte,
        "ukuran_mb": round(ukuran_mb, 3),
    }
