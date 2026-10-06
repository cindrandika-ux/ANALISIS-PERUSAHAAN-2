"""Unit test login (logika verifikasi murni, kredensial fiktif)."""
from auth import verifikasi

KRED = {"tamu": "demo123", "admin": "rahasia"}


def test_login_benar():
    assert verifikasi("tamu", "demo123", KRED) is True


def test_login_salah_password():
    assert verifikasi("tamu", "salah", KRED) is False


def test_login_tak_dikenal_dan_kosong():
    assert verifikasi("asing", "demo123", KRED) is False
    assert verifikasi("", "demo123", KRED) is False
    assert verifikasi("tamu", "", KRED) is False
