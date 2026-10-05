"""Ekstraksi akun kunci perusahaan dagang dari teks laporan.

Pendekatan transparan untuk tugas kuliah: cocokkan label baris (case-insensitive),
lalu ambil angka-angka di baris yang sama. Angka pertama = tahun berjalan,
angka kedua (jika ada) = tahun komparatif (PSAK 1).

Jika label tidak ditemukan, nilai = None ('tidak ditemukan', jangan menebak).
"""
from __future__ import annotations

import re

from .angka_parser import parse_angka_id

# Label tiap akun (urutan: yang paling spesifik dulu agar tidak tertukar,
# mis. 'total aset' sebelum 'aset lancar').
AKUN_LABELS: dict[str, list[str]] = {
    "kas": ["kas dan setara kas", "kas dan bank"],
    "piutang": ["piutang usaha", "piutang"],
    "persediaan": ["persediaan"],
    "aset_lancar": ["jumlah aset lancar", "total aset lancar", "aset lancar"],
    "total_aset": ["jumlah aset", "total aset", "total aktiva"],
    "liab_pendek": ["jumlah liabilitas jangka pendek", "jumlah liabilitas lancar",
                    "total liabilitas jangka pendek", "liabilitas jangka pendek",
                    "liabilitas lancar"],
    "liab_panjang": ["liabilitas jangka panjang", "liabilitas tidak lancar"],
    "total_liab": ["jumlah liabilitas", "total liabilitas", "jumlah kewajiban"],
    "ekuitas": ["jumlah ekuitas", "total ekuitas"],
    "laba_ditahan": ["saldo laba", "laba ditahan", "retained earnings"],
    "pendapatan": ["pendapatan", "penjualan bersih", "penjualan"],
    "laba_kotor": ["laba bruto", "laba kotor", "gross profit"],
    "laba_usaha": ["laba usaha", "laba operasi", "ebit", "operating profit"],
    "beban_bunga": ["beban bunga", "biaya bunga", "beban keuangan"],
    "laba_sebelum_pajak": ["laba sebelum pajak", "laba sebelum pajak penghasilan",
                           "profit before tax", "ebt"],
    "laba_bersih": ["laba bersih tahun berjalan", "laba tahun berjalan",
                    "laba bersih", "net income", "net profit"],
    "cfo": ["arus kas dari aktivitas operasi", "kas dari operasi",
            "arus kas operasi", "net cash from operating"],
    "cfi": ["arus kas dari aktivitas investasi", "arus kas investasi"],
    "cff": ["arus kas dari aktivitas pendanaan", "arus kas pendanaan"],
    "kas_akhir": ["kas dan setara kas akhir", "saldo kas akhir", "kas akhir tahun"],
}

# Pola angka: opsional kurung negatif, digit + titik/koma
POLA_ANGKA = re.compile(r"\(?[\d][\d\.\,]*\)?|-")

# Baris yang mengandung kata ini dikecualikan agar label umum
# tidak menabrak label rinci (mis. 'jumlah aset' vs 'jumlah aset lancar').
PENGECUALIAN: dict[str, list[str]] = {
    "kas": ["akhir"],
    "total_aset": ["lancar"],
    "total_liab": ["jangka pendek", "jangka panjang", "lancar", "tidak lancar"],
    "ekuitas": [],
    "pendapatan": [],
}


def _angka_di_baris(baris: str) -> list[float]:
    """Ambil semua angka valid di satu baris (abaikan tahun 4-digit)."""
    hasil: list[float] = []
    for m in POLA_ANGKA.finditer(baris):
        token = m.group(0)
        # Abaikan token tahun seperti '2024' yang berdiri sendiri tanpa pemisah
        if re.fullmatch(r"(19|20)\d{2}", token):
            continue
        nilai = parse_angka_id(token)
        if nilai is not None:
            hasil.append(nilai)
    return hasil


def ekstrak_akun(
    teks: str,
    pengali: float = 1.0,
    ambil_komparatif: bool = True,
) -> dict:
    """Ekstrak akun kunci dari teks.

    Args:
        teks: Teks dokumen gabungan.
        pengali: Pengali satuan (1 / 1000 / 1000000) ke Rupiah penuh.
        ambil_komparatif: Jika True, angka kedua baris disimpan sebagai
            tahun komparatif (t-1).

    Returns:
        dict tiap akun -> {'tahun_berjalan': float|None,
        'komparatif': float|None, 'bukti': str|None baris sumber}.
        Nilai None berarti 'tidak ditemukan'.
    """
    hasil: dict[str, dict] = {}
    if not teks or not teks.strip():
        for akun in AKUN_LABELS:
            hasil[akun] = {"tahun_berjalan": None, "komparatif": None, "bukti": None}
        return hasil

    baris_list = teks.splitlines()
    for akun, labels in AKUN_LABELS.items():
        cocok: str | None = None
        kecualikan = PENGECUALIAN.get(akun, [])
        for baris in baris_list:
            b_rendah = baris.lower()
            if any(lbl in b_rendah for lbl in labels):
                if any(k in b_rendah for k in kecualikan):
                    continue
                angka = _angka_di_baris(baris)
                if angka:
                    cocok = baris.strip()
                    berjalan = angka[0] * pengali
                    kompar = angka[1] * pengali if (ambil_komparatif and len(angka) > 1) else None
                    hasil[akun] = {"tahun_berjalan": berjalan,
                                   "komparatif": kompar, "bukti": cocok}
                    break
        if akun not in hasil:
            hasil[akun] = {"tahun_berjalan": None, "komparatif": None, "bukti": None}
    return hasil


def ringkas_ke_tabel(hasil_ekstrak: dict) -> list[dict]:
    """Ubah hasil ekstrak menjadi list baris untuk st.data_editor.

    Returns:
        List dict: akun, tahun_berjalan, komparatif, bukti.
    """
    baris: list[dict] = []
    for akun, v in hasil_ekstrak.items():
        baris.append({
            "akun": akun,
            "tahun_berjalan": v.get("tahun_berjalan"),
            "komparatif": v.get("komparatif"),
            "bukti": (v.get("bukti") or "")[:120],
        })
    return baris
