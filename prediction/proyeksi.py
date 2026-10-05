"""Proyeksi sederhana tahun depan via regresi linear (numpy polyfit).

Syarat jujur: minimal 3 titik historis valid. Jika kurang, kembalikan
bisa_dipakai=False dengan pesan keterbatasan (jangan memaksakan proyeksi).
"""
from __future__ import annotations

import numpy as np


def proyeksi_regresi(tahun: list[int], nilai: list[float | None]) -> dict:
    """Proyeksikan nilai tahun berikutnya dari deret historis.

    Args:
        tahun: Contoh [2022, 2023, 2024].
        nilai: Nilai sejajar tahun (boleh ada None, akan dibuang).

    Returns:
        dict: bisa_dipakai (bool), prediksi, slope, intercept,
        tahun_prediksi, n_data, pesan.
    """
    pasangan = [(t, float(v)) for t, v in zip(tahun, nilai) if v is not None]
    if len(pasangan) < 3:
        return {"bisa_dipakai": False, "prediksi": None, "slope": None,
                "intercept": None, "tahun_prediksi": (max(tahun) + 1) if tahun else None,
                "n_data": len(pasangan),
                "pesan": (f"Data historis hanya {len(pasangan)} titik (<3). "
                          "Proyeksi disembunyikan; tampilkan skor + Z-Score saja.")}
    xs = np.array([t for t, _ in pasangan], dtype=float)
    ys = np.array([v for _, v in pasangan], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    tahun_pred = int(max(t for t, _ in pasangan) + 1)
    prediksi = float(slope * tahun_pred + intercept)
    return {"bisa_dipakai": True, "prediksi": prediksi,
            "slope": float(slope), "intercept": float(intercept),
            "tahun_prediksi": tahun_pred, "n_data": len(pasangan), "pesan": None}


def cagr(nilai_awal: float | None, nilai_akhir: float | None, n_periode: int) -> float | None:
    """Rata-rata pertumbuhan tahunan majemuk. None jika tak terdefinisi."""
    if nilai_awal is None or nilai_akhir is None or n_periode <= 0:
        return None
    if float(nilai_awal) <= 0 or float(nilai_akhir) <= 0:
        return None
    return (float(nilai_akhir) / float(nilai_awal)) ** (1.0 / n_periode) - 1.0
