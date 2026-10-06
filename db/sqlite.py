"""Lapisan database SQLite: simpan hasil edit pengguna + ambil historis.

Tabel mengikuti db/schema.sql. Upsert per (perusahaan, tahun).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

KOLOM_AKUN = ["kas", "piutang", "persediaan", "aset_lancar", "total_aset",
              "liab_pendek", "liab_panjang", "total_liab", "ekuitas", "laba_ditahan",
              "pendapatan", "laba_kotor", "laba_usaha", "beban_bunga",
              "laba_sebelum_pajak", "laba_bersih", "cfo", "cfi", "cff"]


def db_path_default() -> str:
    """Path DB dari env DB_PATH atau 'keuangan.db' di root proyek."""
    return os.getenv("DB_PATH", "keuangan.db")


def konek(path: str | None = None) -> sqlite3.Connection:
    """Buka koneksi SQLite (buat file bila belum ada)."""
    p = path or db_path_default()
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    """Buat tabel sesuai db/schema.sql (idempotent)."""
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    con.executescript(schema)
    con.commit()


def perusahaan_id(con: sqlite3.Connection, nama: str) -> int:
    """Ambil id perusahaan, buat baru bila belum ada."""
    nama = (nama or "").strip() or "PT Dagang Fiktif"
    con.execute("INSERT OR IGNORE INTO perusahaan(nama) VALUES(?)", (nama,))
    con.commit()
    row = con.execute("SELECT id FROM perusahaan WHERE nama=?", (nama,)).fetchone()
    return int(row["id"])


def simpan_laporan(con: sqlite3.Connection, nama_perusahaan: str, tahun: int,
                   data: dict, sumber: str = "pdf-edit") -> None:
    """Simpan/upsert satu tahun laporan (data: akun -> float|None)."""
    pid = perusahaan_id(con, nama_perusahaan)
    kolom = ["perusahaan_id", "tahun"] + KOLOM_AKUN + ["sumber"]
    nilai = [pid, int(tahun)] + [data.get(k) for k in KOLOM_AKUN] + [sumber]
    placeholders = ",".join(["?"] * len(kolom))
    update = ",".join(f"{k}=excluded.{k}" for k in KOLOM_AKUN + ["sumber"])
    con.execute(f"INSERT INTO laporan_keuangan({','.join(kolom)}) VALUES({placeholders}) "
                f"ON CONFLICT(perusahaan_id, tahun) DO UPDATE SET {update}", nilai)
    con.commit()


def ambil_historis(con: sqlite3.Connection, nama_perusahaan: str) -> list[dict]:
    """Ambil semua tahun satu perusahaan, urut menaik."""
    pid = perusahaan_id(con, nama_perusahaan)
    rows = con.execute("SELECT * FROM laporan_keuangan WHERE perusahaan_id=? ORDER BY tahun",
                       (pid,)).fetchall()
    return [dict(r) for r in rows]


def daftar_perusahaan(con: sqlite3.Connection) -> list[str]:
    """Daftar nama perusahaan yang pernah disimpan."""
    rows = con.execute("SELECT nama FROM perusahaan ORDER BY nama").fetchall()
    return [r["nama"] for r in rows]


def tambah_pengguna(con: sqlite3.Connection, username: str, pwd_hash: str) -> bool:
    """Daftarkan username baru. False bila nama sudah dipakai."""
    nama = (username or "").strip()
    if not nama:
        return False
    try:
        con.execute("INSERT INTO pengguna(username, pwd_hash) VALUES(?, ?)", (nama, pwd_hash))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def ambil_hash_pengguna(con: sqlite3.Connection, username: str) -> str | None:
    """Ambil hash tersimpan satu pengguna (None bila tidak ada)."""
    row = con.execute("SELECT pwd_hash FROM pengguna WHERE username=?",
                      ((username or "").strip(),)).fetchone()
    return row["pwd_hash"] if row else None


def daftar_pengguna(con: sqlite3.Connection) -> list[dict]:
    """Daftar pendaftar (nama + waktu daftar saja, tanpa hash sandi)."""
    rows = con.execute("SELECT username, created_at FROM pengguna ORDER BY created_at").fetchall()
    return [{"nama": r["username"], "waktu_daftar": r["created_at"]} for r in rows]
