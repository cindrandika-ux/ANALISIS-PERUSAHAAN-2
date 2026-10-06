"""Unit test akun database: hash, email, daftar, token verifikasi (fiktif)."""
import sqlite3
from datetime import datetime, timedelta, timezone

from auth import buat_hash, cek_hash, email_valid, link_verifikasi, nama_valid
from db.sqlite import (ambil_hash_pengguna, ambil_pengguna, daftar_pengguna,
                       init_db, tambah_pengguna, verifikasi_token)


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


def test_email_valid():
    assert email_valid("budi@contoh.id") is True
    assert email_valid("bukan-email") is False
    assert email_valid("") is False


def test_nama_valid():
    assert nama_valid("budi_01") is True
    assert nama_valid("ab") is False


def test_link_verifikasi():
    link = link_verifikasi("https://contoh.streamlit.app/", "tok123")
    assert link == "https://contoh.streamlit.app/?verifikasi=tok123"


def test_daftar_duplikat_ditolak():
    con = _mem()
    ok, _ = tambah_pengguna(con, "Budi", "budi@x.id", buat_hash("rahasia123"), "tok1",
                            (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    assert ok is True
    ok2, pesan = tambah_pengguna(con, "Budi Lain", "BUDI@x.id", buat_hash("lain"), "tok2",
                                 (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    assert ok2 is False and "terdaftar" in pesan


def test_alur_token_hingga_aktif():
    con = _mem()
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tambah_pengguna(con, "Ani", "ani@x.id", buat_hash("pw12345"), "tok-ani", exp)
    akun = ambil_pengguna(con, "ani@x.id")
    assert akun is not None and int(akun["terverifikasi"]) == 0
    ok, _ = verifikasi_token(con, "tok-ani")
    assert ok is True
    assert int(ambil_pengguna(con, "ani@x.id")["terverifikasi"]) == 1
    # Token bekas tidak bisa dipakai ulang untuk akun lain / token asing
    ok2, _ = verifikasi_token(con, "tok-asing")
    assert ok2 is False


def test_token_kedaluwarsa_ditolak():
    con = _mem()
    exp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    tambah_pengguna(con, "Tua", "tua@x.id", buat_hash("pw12345"), "tok-tua", exp)
    ok, pesan = verifikasi_token(con, "tok-tua")
    assert ok is False and "kedaluwarsa" in pesan


def test_migrasi_dari_skema_lama():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE perusahaan (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " nama TEXT NOT NULL UNIQUE)")
    con.execute("CREATE TABLE laporan_keuangan (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    con.execute("CREATE TABLE pengguna (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " username TEXT NOT NULL UNIQUE, pwd_hash TEXT NOT NULL)")
    con.execute("INSERT INTO pengguna(username, pwd_hash) VALUES('lama', 'hash-lama')")
    init_db(con)
    kolom = {r[1] for r in con.execute("PRAGMA table_info(pengguna)").fetchall()}
    assert {"nama", "email", "token", "token_exp", "terverifikasi"} <= kolom
    assert ambil_hash_pengguna(con, "lama") == "hash-lama"


def test_daftar_tanpa_sandi():
    con = _mem()
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tambah_pengguna(con, "Ani", "ani@x.id", buat_hash("x12345"), "t1", exp)
    tambah_pengguna(con, "Budi", "budi@x.id", buat_hash("y12345"), "t2", exp)
    daftar = daftar_pengguna(con)
    assert [p["email"] for p in daftar] == ["ani@x.id", "budi@x.id"]
    assert all("waktu_daftar" in p and "terverifikasi" in p for p in daftar)
    assert all("hash" not in k.lower() and "pwd" not in k.lower()
               for p in daftar for k in p)
