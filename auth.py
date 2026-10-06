"""Gerbang login + pendaftaran akun (kelas demo, bukan pengganti SSO instansi).

Dua sumber akun:
1. Secrets Streamlit ([passwords]) — akun demo bawaan, hanya-baca.
2. Database lokal (tabel pengguna) — akun yang dibuat lewat halaman
   "Daftar". Kata sandi disimpan sebagai hash PBKDF2, bukan teks asli.

Batas: database di Streamlit Cloud bersifat sementara (hilang saat reboot),
jadi akun daftar cocok untuk uji coba, bukan arsip resmi.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

import streamlit as st

ITERASI_HASH = 200_000


def ambil_kredensial() -> dict:
    """Ambil dict username -> password dari secrets (kosong bila belum diisi)."""
    try:
        return dict(st.secrets.get("passwords", {}))
    except Exception:
        return {}


def verifikasi(username: str, password: str, kredensial: dict) -> bool:
    """Cek pasangan username/password secrets (murni, bisa di-unit-test)."""
    if not username or password is None:
        return False
    tersimpan = kredensial.get((username or "").strip())
    if tersimpan is None:
        return False
    return hmac.compare_digest(str(password), str(tersimpan))


def buat_hash(password: str) -> str:
    """Buat hash 'garam$hash' (PBKDF2-SHA256) untuk disimpan di database."""
    garam = os.urandom(16)
    hash_bita = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), garam, ITERASI_HASH)
    return garam.hex() + "$" + hash_bita.hex()


def cek_hash(password: str, tersimpan: str) -> bool:
    """Cocokkan password dengan hash 'garam$hash'."""
    try:
        garam_hex, hash_hex = tersimpan.split("$", 1)
        hitung = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(garam_hex), ITERASI_HASH).hex()
        return hmac.compare_digest(hitung, hash_hex)
    except (ValueError, TypeError):
        return False


def nama_valid(username: str) -> bool:
    """Nama 3-20 karakter huruf/angka/garis bawah/titik."""
    return re.fullmatch(r"[A-Za-z0-9_.]{3,20}", (username or "").strip() or "") is not None


def apakah_admin(username: str) -> bool:
    """True bila username terdaftar sebagai admin di secrets ([admins] daftar)."""
    try:
        daftar = list(st.secrets.get("admins", {}).get("daftar", []))
    except Exception:
        return False
    return (username or "").strip() in daftar


def _db():
    """Koneksi database pengguna (buat tabel bila belum ada)."""
    from db.sqlite import init_db, konek
    con = konek()
    init_db(con)
    return con


def _masuk(username: str) -> None:
    st.session_state["masuk"] = True
    st.session_state["pengguna"] = username.strip()
    st.rerun()


def _form_masuk() -> None:
    with st.form("form_login"):
        username = st.text_input("Nama pengguna")
        password = st.text_input("Kata sandi", type="password")
        tombol = st.form_submit_button("Masuk")
    if tombol:
        con = _db()
        try:
            hash_db = None
            try:
                from db.sqlite import ambil_hash_pengguna
                hash_db = ambil_hash_pengguna(con, username)
            finally:
                con.close()
        except Exception:
            hash_db = None
        if verifikasi(username, password, ambil_kredensial()) or \
                (hash_db is not None and cek_hash(password or "", hash_db)):
            _masuk(username)
        else:
            st.error("Nama pengguna atau kata sandi salah.")
    st.caption("Akun demo: tamu / demo123")


def _form_daftar() -> None:
    with st.form("form_daftar"):
        username = st.text_input("Pilih nama pengguna (3-20 karakter)")
        password = st.text_input("Pilih kata sandi (min. 6 karakter)", type="password")
        ulangi = st.text_input("Ulangi kata sandi", type="password")
        tombol = st.form_submit_button("Buat akun")
    if tombol:
        nama = (username or "").strip()
        if not nama_valid(nama):
            st.error("Nama pengguna 3-20 karakter (huruf, angka, titik, garis bawah).")
        elif not password or len(password) < 6:
            st.error("Kata sandi minimal 6 karakter.")
        elif password != ulangi:
            st.error("Ulangi kata sandi tidak sama.")
        else:
            from db.sqlite import tambah_pengguna
            con = _db()
            try:
                ok = tambah_pengguna(con, nama, buat_hash(password))
            finally:
                con.close()
            if ok:
                st.success("Akun dibuat. Anda langsung masuk.")
                _masuk(nama)
            else:
                st.error("Nama pengguna sudah dipakai. Pilih nama lain.")


def wajib_login() -> str:
    """Tampilkan halaman Masuk/Daftar bila belum masuk; kembalikan username bila lolos.

    Harus dipanggil di awal sebelum konten lain agar tidak bocor.
    """
    if st.session_state.get("masuk"):
        with st.sidebar:
            st.caption(f"Masuk sebagai: {st.session_state.get('pengguna', '-')}")
            if st.button("Keluar"):
                st.session_state.clear()
                st.rerun()
        return str(st.session_state.get("pengguna", ""))

    st.markdown("### Selamat datang")
    st.write("Masuk untuk memakai aplikasi, atau buat akun baru untuk uji coba.")
    tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar akun baru"])
    with tab_masuk:
        _form_masuk()
    with tab_daftar:
        _form_daftar()
    st.stop()
    return ""
