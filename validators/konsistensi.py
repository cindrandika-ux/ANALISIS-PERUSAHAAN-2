"""Cek konsistensi dasar: A = L + E dan kas akhir.

Toleransi default Rp1.000 untuk selisih pembulatan.
"""
from __future__ import annotations


def cek_keseimbangan_neraca(
    total_aset: float | None,
    total_liab: float | None,
    ekuitas: float | None,
    toleransi: float = 1000.0,
) -> dict:
    """Cek Aset = Liabilitas + Ekuitas.

    Returns:
        dict: ok (bool), selisih (float|None), pesan (str|None).
        Jika salah satu input hilang (None), kembalikan ok=False
        dengan selisih 'tidak ditemukan'.
    """
    if total_aset is None or total_liab is None or ekuitas is None:
        return {
            "ok": False,
            "selisih": None,
            "pesan": "tidak ditemukan: salah satu dari aset/liabilitas/ekuitas hilang.",
        }
    selisih = float(total_aset) - (float(total_liab) + float(ekuitas))
    ok = abs(selisih) <= toleransi
    return {
        "ok": ok,
        "selisih": selisih,
        "pesan": None if ok else f"Selisih neraca Rp{selisih:,.0f}. Periksa ekstraksi.",
    }


def cek_kas_akhir(
    kas_neraca: float | None,
    kas_akhir_arus_kas: float | None,
    toleransi: float = 1000.0,
) -> dict:
    """Cek kas di neraca = kas akhir di laporan arus kas."""
    if kas_neraca is None or kas_akhir_arus_kas is None:
        return {
            "ok": False,
            "selisih": None,
            "pesan": "tidak ditemukan: kas neraca atau kas akhir arus kas hilang.",
        }
    selisih = float(kas_neraca) - float(kas_akhir_arus_kas)
    ok = abs(selisih) <= toleransi
    return {
        "ok": ok,
        "selisih": selisih,
        "pesan": None if ok else f"Selisih kas Rp{selisih:,.0f}. Periksa ekstraksi.",
    }
