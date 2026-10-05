"""Parser angka format Indonesia dan normalisasi satuan.

Aturan:
- Titik = pemisah ribuan, koma = desimal (mis. '1.234.567,89').
- Tanda kurung = negatif (mis. '(1.234)' = -1234).
- Satuan: penuh / ribuan / jutaan (mis. 'dalam jutaan Rupiah' x1.000.000).
- Jika tidak ditemukan/kosong/'-', kembalikan None (jangan menebak).
"""
from __future__ import annotations

import re


def parse_angka_id(teks: str | None) -> float | None:
    """Ubah string angka Indonesia menjadi float.

    Args:
        teks: Contoh '1.234.567', '1.234,56', '(5.000)', 'Rp 1.200', '-', ''.

    Returns:
        float atau None jika tidak dapat diuraikan (jangan menebak).
    """
    if teks is None:
        return None
    s = str(teks).strip()
    if not s:
        return None
    # Hilangkan simbol Rp, spasi biasa & non-breaking space
    s = s.replace("Rp", "").replace("RP", "").replace("\xa0", " ").strip()
    s = s.replace(" ", "")
    if s in ("-", "–", "—", "--", ".", ","):
        return None

    negatif = False
    if s.startswith("(") and s.endswith(")"):
        negatif = True
        s = s[1:-1].strip()
        if not s:
            return None

    # Hanya izinkan digit, titik, koma, minus depan
    if s.startswith("-"):
        negatif = not negatif
        s = s[1:]
    if not re.fullmatch(r"[\d\.,]+", s):
        return None

    try:
        if "." in s and "," in s:
            # Indonesia: titik ribuan, koma desimal
            s_bersih = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            # Satu koma: desimal jika 1-2 digit di akhir, else ribuan
            if re.search(r",\d{1,2}$", s):
                s_bersih = s.replace(",", ".")
            else:
                s_bersih = s.replace(",", "")
        elif "." in s and "," not in s:
            # Titik saja: ribuan jika pola .000, else desimal
            bagian = s.split(".")
            if all(len(b) == 3 for b in bagian[1:]) and len(bagian) > 1:
                s_bersih = s.replace(".", "")
            elif len(bagian) == 2 and len(bagian[1]) <= 2:
                s_bersih = s  # desimal Inggris, biarkan
            else:
                # Ambigu (mis. '1.2.3'): anggap ribuan jika >1 titik
                s_bersih = s.replace(".", "") if s.count(".") > 1 else s
        else:
            s_bersih = s
        nilai = float(s_bersih)
        return -nilai if negatif else nilai
    except ValueError:
        return None


def deteksi_satuan(teks: str | None) -> dict:
    """Deteksi satuan penyajian dari teks (header/CALK).

    Args:
        teks: Teks dokumen gabungan.

    Returns:
        dict: satuan ('penuh'|'ribu'|'juta'), pengali (1|1000|1000000),
        bukti (str|None potongan teks yang cocok).
    """
    if not teks:
        return {"satuan": "penuh", "pengali": 1, "bukti": None}
    t = teks.lower()
    pola_juta = ["dalam jutaan rupiah", "jutaan rupiah", "dalam jutaan",
                 "rp juta", "(jutaan)", "dinyatakan dalam jutaan"]
    pola_ribu = ["dalam ribuan rupiah", "ribuan rupiah", "dalam ribuan",
                 "rp ribu", "(ribuan)", "dinyatakan dalam ribuan"]
    for p in pola_juta:
        if p in t:
            return {"satuan": "juta", "pengali": 1_000_000, "bukti": p}
    for p in pola_ribu:
        if p in t:
            return {"satuan": "ribu", "pengali": 1_000, "bukti": p}
    return {"satuan": "penuh", "pengali": 1, "bukti": None}


def normalisasi_nilai(nilai: float | None, pengali: int | float) -> float | None:
    """Kalikan nilai terbaca dengan pengali satuan ke Rupiah penuh."""
    if nilai is None:
        return None
    return float(nilai) * float(pengali)
