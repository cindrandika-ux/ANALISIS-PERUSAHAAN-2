"""Deteksi Laporan Auditor Independen dan opini auditor.

Klasifikasi: WTP / WDP / TW / Disclaimer / TIDAK_DITEMUKAN.
Jika teks tidak memuat bukti, kembalikan 'tidak ditemukan' (jangan menebak).
"""
from __future__ import annotations


def deteksi_opini(teks: str) -> dict:
    """Deteksi keberadaan laporan auditor dan jenis opini.

    Args:
        teks: Teks hasil ekstraksi PDF (digabung seluruh halaman).

    Returns:
        dict: ada_laporan_auditor (bool), opini (str), peringatan (str|None).
        opini salah satu dari: WTP, WDP, TW, Disclaimer, TIDAK_DITEMUKAN.
    """
    if not teks or not teks.strip():
        return {
            "ada_laporan_auditor": False,
            "opini": "TIDAK_DITEMUKAN",
            "peringatan": "Teks dokumen tidak ditemukan/kosong.",
        }

    t = teks.lower()

    ada_laporan = any(k in t for k in [
        "laporan auditor independen",
        "laporan audit independen",
        "auditor independen",
        "kantor akuntan publik",
    ])
    if not ada_laporan:
        return {
            "ada_laporan_auditor": False,
            "opini": "TIDAK_DITEMUKAN",
            "peringatan": "Laporan Auditor Independen tidak ditemukan.",
        }

    # Urutan penting: cek yang paling parah dulu agar tidak tertutup kata 'wajar'.
    if any(k in t for k in [
        "tidak menyatakan pendapat",
        "menolak memberikan opini",
        "disclaimer of opinion",
        "disclaimer",
    ]):
        opini = "Disclaimer"
    elif any(k in t for k in [
        "pendapat tidak wajar",
        "opini tidak wajar",
        "adverse opinion",
        "adverse",
    ]):
        opini = "TW"
    elif any(k in t for k in [
        "wajar tanpa pengecualian",
        "tanpa modifikasian",
        "tanpa pengecualian",
        "wajar dalam semua hal yang material",
        "menyatakan pendapat wajar",
        "unmodified",
        "unqualified",
    ]):
        opini = "WTP"
    elif any(k in t for k in [
        "wajar dengan pengecualian",
        "dengan pengecualian",
        "qualified opinion",
        "qualified",
    ]):
        opini = "WDP"
    else:
        opini = "TIDAK_DITEMUKAN"

    peringatan = None
    if opini == "TIDAK_DITEMUKAN":
        peringatan = "Laporan auditor ada, tetapi jenis opini tidak ditemukan."
    elif opini != "WTP":
        peringatan = f"Opini auditor adalah {opini} (bukan WTP). Interpretasikan hasil dengan hati-hati."

    return {
        "ada_laporan_auditor": True,
        "opini": opini,
        "peringatan": peringatan,
    }
