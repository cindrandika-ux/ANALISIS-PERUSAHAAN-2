"""Unit test akun database: hash, validasi nama, daftar + masuk (fiktif)."""
import sqlite3

from auth import buat_hash, cek_hash, nama_valid
from db.sqlite import ambil_hash_pengguna, init_db, tambah_pengguna


def _mem():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    init_db(con)
    return con


def test_hash_cocok_dan_salah():
    h = buat_hash("katasandi")
    assert "$" in h and "katasandi" not in h
    assert cek_hash("katasandi", h) is True
    assert cek_hash("salah", h) is False
    assert cek_hash("x", "rusak") is False


def test_nama_valid():
    assert nama_valid("budi_01") is True
    assert nama_valid("ab") is False
    assert nama_valid("ada spasi") is False


def test_daftar_lalu_verifikasi():
    con = _mem()
    assert tambah_pengguna(con, "budi", buat_hash("rahasia123")) is True
    # Nama ganda ditolak
    assert tambah_pengguna(con, "budi", buat_hash("lain")) is False
    tersimpan = ambil_hash_pengguna(con, "budi")
    assert tersimpan is not None and cek_hash("rahasia123", tersimpan) is True
    assert ambil_hash_pengguna(con, "takada") is None
