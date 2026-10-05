"""Altman Z'' untuk perusahaan non-manufaktur / emerging market.

Alasan pilih Z'' (bukan Z original):
- Z original memakai Market Value of Equity (nilai pasar saham) sehingga hanya
  cocok untuk manufaktur Tbk. Perusahaan dagang tertutup/tidak Tbk tidak punya
  harga pasar yang andal.
- Z'' mengganti market value dengan Book Value of Equity (nilai buku ekuitas)
  dan koefisiennya dikalibrasi ulang untuk non-manufaktur + emerging market.

Rumus: Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
  X1 = Modal kerja / Total aset = (Aset lancar - Liabilitas pendek) / Total aset
  X2 = Laba ditahan / Total aset
  X3 = EBIT (laba usaha) / Total aset
  X4 = Nilai buku ekuitas / Total liabilitas
Cutoff emerging market: >2.6 Sehat, 1.1-2.6 Waspada (grey), <1.1 Berisiko.
"""
from __future__ import annotations

PENJELASAN_Z = (
    "Varian Z'' dipakai karena perusahaan dagang non-manufaktur dan konteks "
    "emerging market (Indonesia): memakai nilai buku ekuitas, bukan nilai pasar saham."
)


def hitung_zpp(data: dict) -> dict:
    """Hitung Altman Z'' dari satu tahun data.

    Args:
        data: dict akun (aset_lancar, liab_pendek, total_aset, laba_ditahan,
            laba_usaha sebagai EBIT, ekuitas, total_liab).

    Returns:
        dict: x1..x4, z (float|None), kategori, penjelasan.
        z None berarti 'tidak ditemukan' (input hilang/penyebut nol).
    """
    def bagi(a, b):
        if a is None or b is None or float(b) == 0:
            return None
        return float(a) / float(b)

    wc = None
    if data.get("aset_lancar") is not None and data.get("liab_pendek") is not None:
        wc = float(data["aset_lancar"]) - float(data["liab_pendek"])
    x1 = bagi(wc, data.get("total_aset"))
    x2 = bagi(data.get("laba_ditahan"), data.get("total_aset"))
    x3 = bagi(data.get("laba_usaha"), data.get("total_aset"))
    x4 = bagi(data.get("ekuitas"), data.get("total_liab"))

    if None in (x1, x2, x3, x4):
        return {"x1": x1, "x2": x2, "x3": x3, "x4": x4, "z": None,
                "kategori": "TIDAK_DAPAT_DINILAI",
                "penjelasan": PENJELASAN_Z + " Input tidak lengkap."}
    z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    if z > 2.6:
        kat = "Sehat"
    elif z >= 1.1:
        kat = "Waspada"
    else:
        kat = "Berisiko"
    return {"x1": x1, "x2": x2, "x3": x3, "x4": x4, "z": z,
            "kategori": kat, "penjelasan": PENJELASAN_Z}
