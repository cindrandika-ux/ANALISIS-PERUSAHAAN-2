"""Unit test Modul 2: parser angka Indonesia, satuan, dan akun dagang (fiktif)."""
from extractors.akun_dagang import ekstrak_akun
from extractors.angka_parser import deteksi_satuan, normalisasi_nilai, parse_angka_id
from extractors.ocr_fallback import perlu_ocr


def test_parse_ribuan_desimal():
    assert parse_angka_id("1.234.567") == 1234567.0
    assert parse_angka_id("1.234,56") == 1234.56
    assert parse_angka_id("850.000.000") == 850000000.0


def test_parse_kurung_negatif():
    assert parse_angka_id("(5.000)") == -5000.0
    assert parse_angka_id("(1.234,50)") == -1234.5


def test_parse_rp_dan_strip():
    assert parse_angka_id("Rp 1.200.000") == 1200000.0
    assert parse_angka_id("-") is None
    assert parse_angka_id("") is None
    assert parse_angka_id(None) is None
    assert parse_angka_id("abc") is None


def test_deteksi_satuan_jutaan_dan_ribuan():
    j = deteksi_satuan("Disajikan dalam jutaan Rupiah, kecuali dinyatakan lain.")
    assert j["pengali"] == 1_000_000
    r = deteksi_satuan("Angka disajikan dalam ribuan rupiah.")
    assert r["pengali"] == 1_000
    p = deteksi_satuan("Laporan posisi keuangan biasa.")
    assert p["pengali"] == 1


def test_normalisasi_nilai():
    assert normalisasi_nilai(850.0, 1_000_000) == 850000000.0
    assert normalisasi_nilai(None, 1000) is None


def test_perlu_ocr():
    assert perlu_ocr("") is True
    assert perlu_ocr("x" * 50) is True
    assert perlu_ocr("x" * 500) is False


def test_ekstrak_akun_dagang_fiktif():
    # Teks fiktif meniru baris laporan dagang (tahun berjalan + komparatif)
    teks = (
        "Laporan Posisi Keuangan\n"
        "Kas dan setara kas 1.050.000.000 950.000.000\n"
        "Piutang usaha 1.500.000.000 1.350.000.000\n"
        "Persediaan 2.100.000.000 1.950.000.000\n"
        "Jumlah aset lancar 5.000.000.000 4.550.000.000\n"
        "Jumlah aset 9.000.000.000 8.200.000.000\n"
        "Liabilitas jangka pendek 2.300.000.000 2.150.000.000\n"
        "Liabilitas jangka panjang 1.350.000.000 1.300.000.000\n"
        "Jumlah liabilitas 3.650.000.000 3.450.000.000\n"
        "Jumlah ekuitas 5.350.000.000 4.750.000.000\n"
        "Saldo laba 3.050.000.000 2.550.000.000\n"
        "Pendapatan 12.000.000.000 10.800.000.000\n"
        "Laba kotor 3.600.000.000 3.240.000.000\n"
        "Laba usaha 1.500.000.000 1.300.000.000\n"
        "Beban bunga 200.000.000 190.000.000\n"
        "Laba sebelum pajak 1.300.000.000 1.110.000.000\n"
        "Laba bersih 1.000.000.000 850.000.000\n"
    )
    hasil = ekstrak_akun(teks, pengali=1.0)
    assert hasil["kas"]["tahun_berjalan"] == 1050000000.0
    assert hasil["kas"]["komparatif"] == 950000000.0
    assert hasil["total_aset"]["tahun_berjalan"] == 9000000000.0
    assert hasil["laba_bersih"]["tahun_berjalan"] == 1000000000.0


def test_ekstrak_tidak_ditemukan_jangan_menebak():
    hasil = ekstrak_akun("Hanya teks acak tanpa akun.", pengali=1.0)
    assert hasil["kas"]["tahun_berjalan"] is None
    assert hasil["laba_bersih"]["komparatif"] is None
