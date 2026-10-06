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
    _migrasi_pengguna(con)
    con.commit()


def _migrasi_pengguna(con: sqlite3.Connection) -> None:
    """Tambahkan kolom akun baru bila database lama belum memilikinya."""
    kolom = {r[1] for r in con.execute("PRAGMA table_info(pengguna)").fetchall()}
    for nama, tipe in [("nama", "TEXT"), ("email", "TEXT"), ("token", "TEXT"),
                       ("token_exp", "TEXT"), ("terverifikasi", "INTEGER DEFAULT 0")]:
        if nama not in kolom:
            con.execute(f"ALTER TABLE pengguna ADD COLUMN {nama} {tipe}")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pengguna_email ON pengguna(email)")


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


def tambah_pengguna(con: sqlite3.Connection, nama: str, email: str,
                      pwd_hash: str, token: str, token_exp: str) -> tuple[bool, str]:
    """Daftarkan akun baru (belum terverifikasi). Kembalikan (ok, pesan)."""
    email_bersih = (email or "").strip().lower()
    nama_bersih = (nama or "").strip()
    if not nama_bersih:
        return False, "Nama wajib diisi."
    if not email_bersih:
        return False, "Email wajib diisi."
    ada = con.execute("SELECT 1 FROM pengguna WHERE lower(email)=?",
                      (email_bersih,)).fetchone()
    if ada:
        return False, "Email sudah terdaftar. Silakan masuk."
    con.execute("INSERT INTO pengguna(username, pwd_hash, nama, email, token, token_exp, terverifikasi)"
                " VALUES(?, ?, ?, ?, ?, ?, 0)",
                (email_bersih, pwd_hash, nama_bersih, email_bersih, token, token_exp))
    con.commit()
    return True, "Pendaftaran berhasil."


def ambil_hash_pengguna(con: sqlite3.Connection, username: str) -> str | None:
    """Ambil hash tersimpan satu pengguna (None bila tidak ada).

    Menerima email (pendaftaran baru) atau username (akun lama/demo).
    """
    kunci = (username or "").strip()
    row = con.execute("SELECT pwd_hash FROM pengguna WHERE lower(email)=lower(?) OR username=?",
                      (kunci, kunci)).fetchone()
    return row["pwd_hash"] if row else None


def ambil_pengguna(con: sqlite3.Connection, identitas: str) -> dict | None:
    """Ambil baris pengguna per email/username (None bila tidak ada)."""
    kunci = (identitas or "").strip()
    row = con.execute("SELECT * FROM pengguna WHERE lower(email)=lower(?) OR username=?",
                      (kunci, kunci)).fetchone()
    return dict(row) if row else None


def verifikasi_token(con: sqlite3.Connection, token: str) -> tuple[bool, str]:
    """Aktifkan akun dari token link email (cek kedaluwarsa 24 jam)."""
    from datetime import datetime, timezone
    if not token:
        return False, "Tautan tidak valid."
    row = con.execute("SELECT * FROM pengguna WHERE token=?", (token,)).fetchone()
    if not row:
        return False, "Tautan verifikasi tidak dikenal."
    if int(row["terverifikasi"] or 0) == 1:
        return True, "Email sudah terverifikasi sebelumnya. Silakan masuk."
    try:
        kedaluwarsa = datetime.fromisoformat(row["token_exp"])
    except (TypeError, ValueError):
        return False, "Tautan verifikasi rusak."
    if datetime.now(timezone.utc) > kedaluwarsa:
        return False, "Tautan kedaluwarsa. Silakan daftar ulang."
    con.execute("UPDATE pengguna SET terverifikasi=1, token=NULL WHERE id=?", (row["id"],))
    con.commit()
    return True, "Email terverifikasi. Silakan masuk dengan akun Anda."


def daftar_pengguna(con: sqlite3.Connection) -> list[dict]:
    """Daftar pendaftar (nama + email + status, tanpa hash sandi)."""
    rows = con.execute("SELECT nama, email, terverifikasi, created_at FROM pengguna"
                       " ORDER BY created_at").fetchall()
    return [{"nama": r["nama"] or r["email"], "email": r["email"],
             "terverifikasi": "Ya" if int(r["terverifikasi"] or 0) == 1 else "Belum",
             "waktu_daftar": r["created_at"]} for r in rows]
