"""Analisis common-size: neraca terhadap total aset, laba rugi terhadap pendapatan."""
from __future__ import annotations

from .rasio import safe_div

POS_NERACA = ["kas", "piutang", "persediaan", "aset_lancar",
              "liab_pendek", "liab_panjang", "total_liab", "ekuitas", "laba_ditahan"]
POS_LABA_RUGI = ["laba_kotor", "laba_usaha", "beban_bunga",
                 "laba_sebelum_pajak", "laba_bersih"]


def common_size_neraca(d: dict) -> dict:
    """Ubah pos neraca menjadi % terhadap total_aset."""
    total = d.get("total_aset")
    return {pos: (safe_div(d.get(pos), total) * 100
                  if safe_div(d.get(pos), total) is not None else None)
            for pos in POS_NERACA}


def common_size_laba_rugi(d: dict) -> dict:
    """Ubah pos laba rugi menjadi % terhadap pendapatan."""
    pend = d.get("pendapatan")
    return {pos: (safe_div(d.get(pos), pend) * 100
                  if safe_div(d.get(pos), pend) is not None else None)
            for pos in POS_LABA_RUGI}
