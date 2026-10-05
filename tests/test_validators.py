"""Unit test Modul 1: validators (data fiktif, bukan data riil)."""
from validators.file_check import validasi_pdf
from validators.opini_audit import deteksi_opini
from validators.psak1_check import cek_kelengkapan_psak1, deteksi_kerangka
from validators.konsistensi import cek_keseimbangan_neraca, cek_kas_akhir


def test_validasi_pdf_valid():
    data = b"%PDF-1.7 dummy" + b"x" * 100
    hasil = validasi_pdf("laporan.pdf", data, max_mb=20)
    assert hasil["ok"] is True
    assert hasil["errors"] == []


def test_validasi_pdf_bukan_pdf():
    hasil = validasi_pdf("laporan.pdf", b"Bukan PDF", max_mb=20)
    assert hasil["ok"] is False
    assert any("magic bytes" in e for e in hasil["errors"])


def test_validasi_pdf_ekstensi_salah():
    data = b"%PDF-1.7 dummy"
    hasil = validasi_pdf("laporan.txt", data)
    assert hasil["ok"] is False


def test_validasi_pdf_terlalu_besar():
    data = b"%PDF" + b"x" * 10
    hasil = validasi_pdf("a.pdf", data, max_mb=0.000001)
    assert hasil["ok"] is False


def test_opini_wtp():
    teks = "Laporan Auditor Independen oleh Kantor Akuntan Publik. Opini wajar tanpa pengecualian."
    hasil = deteksi_opini(teks)
    assert hasil["ada_laporan_auditor"] is True
    assert hasil["opini"] == "WTP"
    assert hasil["peringatan"] is None


def test_opini_wdp_memberi_peringatan():
    teks = "Laporan auditor independen menyatakan opini wajar dengan pengecualian atas persediaan."
    hasil = deteksi_opini(teks)
    assert hasil["opini"] == "WDP"
    assert hasil["peringatan"] is not None


def test_opini_tidak_ada_laporan():
    hasil = deteksi_opini("Hanya ada neraca dan laba rugi.")
    assert hasil["opini"] == "TIDAK_DITEMUKAN"
    assert hasil["ada_laporan_auditor"] is False


def test_psak1_lengkap():
    teks = ("Laporan Posisi Keuangan, Laporan Laba Rugi dan Penghasilan Komprehensif Lain, "
            "Laporan Perubahan Ekuitas, Laporan Arus Kas, Catatan Atas Laporan Keuangan. "
            "Disusun sesuai PSAK / SAK Umum berbasis IFRS.")
    hasil = cek_kelengkapan_psak1(teks)
    assert hasil["lengkap"] is True
    kerangka = deteksi_kerangka(teks)
    assert kerangka["kerangka"] == "SAK Umum (IFRS)"


def test_psak1_tidak_lengkap_dan_emkm():
    teks = "Laporan posisi keuangan dan laporan laba rugi SAK EMKM."
    hasil = cek_kelengkapan_psak1(teks)
    assert hasil["lengkap"] is False
    assert "arus_kas" in hasil["hilang"]
    assert deteksi_kerangka(teks)["kerangka"] == "SAK EMKM"


def test_konsistensi_fiktif_2024():
    # Angka fiktif PT Dagang Sejahtera 2024 (Rupiah penuh)
    r = cek_keseimbangan_neraca(9000000000, 3650000000, 5350000000)
    assert r["ok"] is True
    k = cek_kas_akhir(1050000000, 1050000000)
    assert k["ok"] is True


def test_konsistensi_selisih_terdeteksi():
    r = cek_keseimbangan_neraca(9000000000, 3650000000, 5000000000)
    assert r["ok"] is False
    assert r["selisih"] != 0
