"""Analisis tren antar tahun: absolut, persen, dan arah.

Arah: naik / turun / stabil (|persen| < 5%) / tidak_dapat_dihitung.
"""
from __future__ import annotations

AMBANG_STABIL_PERSEN = 5.0


def hitung_perubahan(nilai_lama: float | None, nilai_baru: float | None) -> dict:
    """Hitung perubahan absolut, persen, dan arah tren.

    Returns:
        dict: absolut (float|None), persen (float|None dalam %),
        arah (str), keterangan (str|None).
    """
    if nilai_lama is None or nilai_baru is None:
        return {"absolut": None, "persen": None,
                "arah": "tidak_dapat_dihitung",
                "keterangan": "tidak ditemukan: salah satu tahun hilang."}
    absolut = float(nilai_baru) - float(nilai_lama)
    if float(nilai_lama) == 0:
        return {"absolut": absolut, "persen": None,
                "arah": "tidak_dapat_dihitung",
                "keterangan": "Tahun dasar nol, persen tidak terdefinisi."}
    persen = absolut / abs(float(nilai_lama)) * 100.0
    if abs(persen) < AMBANG_STABIL_PERSEN:
        arah = "stabil"
    elif persen > 0:
        arah = "naik"
    else:
        arah = "turun"
    return {"absolut": absolut, "persen": persen,
            "arah": arah, "keterangan": None}


def tren_multi_tahun(seri: list[tuple[int, float | None]]) -> list[dict]:
    """Bandingkan berurutan untuk deret (tahun, nilai).

    Args:
        seri: Contoh [(2022, 100), (2023, 110), (2024, 105)].

    Returns:
        List dict per pasangan tahun: tahun_dari, tahun_ke, + hasil hitung_perubahan.
    """
    hasil: list[dict] = []
    terurut = sorted(seri, key=lambda x: x[0])
    for (t0, v0), (t1, v1) in zip(terurut, terurut[1:]):
        p = hitung_perubahan(v0, v1)
        hasil.append({"tahun_dari": t0, "tahun_ke": t1, **p})
    return hasil
