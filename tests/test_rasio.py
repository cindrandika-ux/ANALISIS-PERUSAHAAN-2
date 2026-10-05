"""Unit test Modul 3: rasio, tren, common-size (angka fiktif PT Dagang)."""
import pytest

from analysis.commonsize import common_size_laba_rugi, common_size_neraca
from analysis.rasio import hitung_rasio
from analysis.tren import hitung_perubahan, tren_multi_tahun

# Fiktif 2024 (Rupiah penuh) — sama dengan seed_historis
D2024 = {
    "kas": 1050000000, "piutang": 1500000000, "persediaan": 2100000000,
    "aset_lancar": 5000000000, "total_aset": 9000000000,
    "liab_pendek": 2300000000, "liab_panjang": 1350000000, "total_liab": 3650000000,
    "ekuitas": 5350000000, "laba_ditahan": 3050000000,
    "pendapatan": 12000000000, "laba_kotor": 3600000000, "laba_usaha": 1500000000,
    "beban_bunga": 200000000, "laba_sebelum_pajak": 1300000000,
    "laba_bersih": 1000000000, "cfo": 1150000000,
}


def test_rasio_likuiditas_2024():
    r = hitung_rasio(D2024)
    assert r["current_ratio"] == pytest.approx(5000 / 2300)
    assert r["quick_ratio"] == pytest.approx((5000 - 2100) / 2300)
    assert r["cash_ratio"] == pytest.approx(1050 / 2300)


def test_rasio_solvabilitas_profitabilitas():
    r = hitung_rasio(D2024)
    assert r["der"] == pytest.approx(3650 / 5350)
    assert r["debt_ratio"] == pytest.approx(3650 / 9000)
    assert r["interest_coverage"] == pytest.approx(1500 / 200)
    assert r["gross_margin"] == pytest.approx(0.30)
    assert r["operating_margin"] == pytest.approx(0.125)
    assert r["net_margin"] == pytest.approx(1000 / 12000)
    assert r["roa"] == pytest.approx(1000 / 9000)
    assert r["roe"] == pytest.approx(1000 / 5350)


def test_rasio_aktivitas_aruskas():
    r = hitung_rasio(D2024)
    assert r["asset_turnover"] == pytest.approx(12000 / 9000)
    assert r["perputaran_piutang"] == pytest.approx(12000 / 1500)
    # HPP dagang = 12000-3600=8400; 8400/2100=4.0
    assert r["perputaran_persediaan"] == pytest.approx(4.0)
    assert r["cfo_laba"] == pytest.approx(1.15)
    assert r["cfo_liab_lancar"] == pytest.approx(0.5)


def test_rasio_aman_nol_dan_hilang():
    assert hitung_rasio({**D2024, "liab_pendek": 0})["current_ratio"] is None
    assert hitung_rasio({})["roa"] is None
    # Tanpa persediaan -> quick None, current tetap ada
    r = hitung_rasio({**D2024, "persediaan": None})
    assert r["quick_ratio"] is None
    assert r["current_ratio"] is not None


def test_tren_naik_turun_stabil():
    assert hitung_perubahan(100, 130)["arah"] == "naik"
    assert hitung_perubahan(100, 70)["arah"] == "turun"
    assert hitung_perubahan(100, 102)["arah"] == "stabil"
    assert hitung_perubahan(850000000, 1000000000)["persen"] == pytest.approx(17.647, abs=0.01)
    assert hitung_perubahan(None, 100)["arah"] == "tidak_dapat_dihitung"


def test_tren_multi_tahun_pendapatan():
    seri = [(2022, 9500000000), (2023, 10800000000), (2024, 12000000000)]
    hasil = tren_multi_tahun(seri)
    assert len(hasil) == 2
    assert hasil[0]["tahun_dari"] == 2022 and hasil[0]["arah"] == "naik"


def test_commonsize():
    n = common_size_neraca(D2024)
    assert n["kas"] == pytest.approx(1050 / 9000 * 100)
    assert n["ekuitas"] == pytest.approx(5350 / 9000 * 100)
    l = common_size_laba_rugi(D2024)
    assert l["laba_bersih"] == pytest.approx(1000 / 12000 * 100)
