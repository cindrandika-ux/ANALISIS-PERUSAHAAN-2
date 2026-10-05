"""Cek kelengkapan PSAK 1 dan deteksi kerangka pelaporan.

PSAK 1 mewajibkan: posisi keuangan, laba rugi + penghasilan komprehensif lain,
perubahan ekuitas, arus kas, dan CALK. Kerangka: SAK Umum / SAK EP / SAK EMKM.
Jika tidak ditemukan, tandai 'tidak ditemukan' (jangan menebak).
"""
from __future__ import annotations

KOMPONEN_KEYWORDS: dict[str, list[str]] = {
    "posisi_keuangan": ["laporan posisi keuangan", "neraca"],
    "laba_rugi_komprehensif": ["laporan laba rugi", "penghasilan komprehensif"],
    "perubahan_ekuitas": ["laporan perubahan ekuitas", "perubahan ekuitas"],
    "arus_kas": ["laporan arus kas", "arus kas"],
    "calk": ["catatan atas laporan keuangan", "calk"],
}


def cek_kelengkapan_psak1(teks: str) -> dict:
    """Cek kehadiran 5 komponen laporan menurut PSAK 1.

    Args:
        teks: Teks dokumen gabungan (lowercase-insensitive).

    Returns:
        dict: komponen (dict[str,bool]), lengkap (bool), hilang (list[str]).
    """
    if not teks or not teks.strip():
        return {
            "komponen": {k: False for k in KOMPONEN_KEYWORDS},
            "lengkap": False,
            "hilang": list(KOMPONEN_KEYWORDS.keys()),
        }
    t = teks.lower()
    komponen = {
        nama: any(k in t for k in keywords)
        for nama, keywords in KOMPONEN_KEYWORDS.items()
    }
    hilang = [k for k, ada in komponen.items() if not ada]
    return {"komponen": komponen, "lengkap": len(hilang) == 0, "hilang": hilang}


def deteksi_kerangka(teks: str) -> dict:
    """Deteksi kerangka SAK dari bagian CALK/kebijakan akuntansi.

    Args:
        teks: Teks dokumen gabungan.

    Returns:
        dict: kerangka (str), ditemukan (bool).
        kerangka: 'SAK EMKM' | 'SAK EP' | 'SAK Umum (IFRS)' | 'TIDAK_DITEMUKAN'.
    """
    if not teks or not teks.strip():
        return {"kerangka": "TIDAK_DITEMUKAN", "ditemukan": False}
    t = teks.lower()
    if "sak emkm" in t or "standar akuntansi keuangan entitas mikro" in t:
        return {"kerangka": "SAK EMKM", "ditemukan": True}
    if "sak ep" in t or "entitas privat" in t:
        return {"kerangka": "SAK EP", "ditemukan": True}
    if "psak" in t or "sak umum" in t or "ifrs" in t \
            or "standar akuntansi keuangan" in t:
        return {"kerangka": "SAK Umum (IFRS)", "ditemukan": True}
    return {"kerangka": "TIDAK_DITEMUKAN", "ditemukan": False}
