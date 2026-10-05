"""Unit test Modul 4: skor, Altman Z'', proyeksi, narasi (fiktif)."""
import pytest

from analysis.rasio import hitung_rasio
from prediction.altman import hitung_zpp
from prediction.narasi import (DISCLAIMER, buat_narasi, kategori_final,
                               pilih_pendukung_risiko)
from prediction.proyeksi import cagr, proyeksi_regresi
from prediction.skor import hitung_skor, kategori_dari_skor

D2024 = {
    "kas": 1050000000, "piutang": 1500000000, "persediaan": 2100000000,
    "aset_lancar": 5000000000, "total_aset": 9000000000,
    "liab_pendek": 2300000000, "liab_panjang": 1350000000, "total_liab": 3650000000,
    "ekuitas": 5350000000, "laba_ditahan": 3050000000,
    "pendapatan": 12000000000, "laba_kotor": 3600000000, "laba_usaha": 1500000000,
    "beban_bunga": 200000000, "laba_sebelum_pajak": 1300000000,
    "laba_bersih": 1000000000, "cfo": 1150000000,
}


def test_skor_2024_sehat():
    rasio = hitung_rasio(D2024)
    hasil = hitung_skor(rasio)
    assert hasil["skor_total"] == pytest.approx(85.0, abs=5.0)
    assert kategori_dari_skor(hasil["skor_total"]) == "Sehat"
    # Bobot bisa diatur: semua ke profitabilitas tetap jalan
    h2 = hitung_skor(rasio, bobot={"profitabilitas": 1.0})
    assert h2["skor_total"] is not None


def test_altman_zpp_2024():
    h = hitung_zpp(D2024)
    # X1=0.3, X2=0.3389, X3=0.1667, X4=1.4658 -> Z~5.73
    assert h["z"] == pytest.approx(5.73, abs=0.05)
    assert h["kategori"] == "Sehat"
    assert "buku" in h["penjelasan"].lower()


def test_altman_hilang_jangan_menebak():
    h = hitung_zpp({})
    assert h["z"] is None
    assert h["kategori"] == "TIDAK_DAPAT_DINILAI"


def test_proyeksi_butuh_3_tahun():
    ok = proyeksi_regresi([2022, 2023, 2024], [9500000000, 10800000000, 12000000000])
    assert ok["bisa_dipakai"] is True
    assert ok["tahun_prediksi"] == 2025
    assert ok["prediksi"] > 12000000000  # tren naik
    kurang = proyeksi_regresi([2023, 2024], [10800000000, 12000000000])
    assert kurang["bisa_dipakai"] is False
    assert kurang["prediksi"] is None
    assert "3" in kurang["pesan"]


def test_cagr():
    assert cagr(100, 121, 2) == pytest.approx(0.10)
    assert cagr(0, 100, 1) is None
    assert cagr(None, 100, 1) is None


def test_narasi_dan_kategori_final():
    rasio = hitung_rasio(D2024)
    skor = hitung_skor(rasio)
    pr = pilih_pendukung_risiko(skor["skor_detail"])
    assert len(pr["pendukung"]) == 3 and len(pr["risiko"]) == 3
    assert kategori_final("Sehat", "Sehat") == "Sehat"
    assert kategori_final("Sehat", "Berisiko") == "Berisiko"
    teks = buat_narasi("PT Dagang Fiktif", 2024, skor["skor_total"], "Sehat",
                       5.73, "Sehat", pr["pendukung"], pr["risiko"], True)
    assert "PT Dagang Fiktif" in teks
    assert DISCLAIMER.split(":")[0] in teks
    assert "bukan nasihat" in teks.lower()
