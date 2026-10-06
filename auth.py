"""Gerbang login + pendaftaran akun dengan verifikasi email (kelas demo).

Alur: Daftar (Nama, Email, sandi) -> link verifikasi dikirim ke email ->
klik link kembali ke aplikasi -> akun aktif -> Masuk.

Dua sumber akun:
1. Secrets Streamlit ([passwords]) — akun demo bawaan, hanya-baca.
2. Database lokal (tabel pengguna) — akun pendaftar, wajib verifikasi email.
   Kata sandi disimpan sebagai hash PBKDF2, bukan teks asli.

Butuh pengaturan SMTP di secrets ([smtp] + [app] url_aplikasi) agar email
terkirim. Tanpa SMTP, link ditampilkan di layar (mode demo) dengan peringatan.
Batas: database di Streamlit Cloud bersifat sementara (hilang saat reboot).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets as secret_mod
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import streamlit as st

ITERASI_HASH = 200_000
MASA_TOKEN_JAM = 24


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


def email_valid(email: str) -> bool:
    """Validasi format email sederhana (murni, bisa di-unit-test)."""
    return re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                        (email or "").strip() or "") is not None


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
    """Nama pengguna gaya lama 3-20 karakter (kompatibilitas tes lama)."""
    return re.fullmatch(r"[A-Za-z0-9_.]{3,20}", (username or "").strip() or "") is not None


def buat_token() -> tuple[str, str]:
    """Buat (token, kedaluwarsa ISO 24 jam ke depan)."""
    token = secret_mod.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=MASA_TOKEN_JAM)).isoformat()
    return token, exp


def link_verifikasi(url_aplikasi: str, token: str) -> str:
    """Susun link kembali ke aplikasi pembawa token."""
    dasar = (url_aplikasi or "").rstrip("/")
    return f"{dasar}/?verifikasi={token}"


def ambil_smtp() -> dict | None:
    """Baca pengaturan [smtp] + [app] dari secrets (None bila belum diisi)."""
    try:
        smtp = dict(st.secrets.get("smtp", {}))
        app = dict(st.secrets.get("app", {}))
    except Exception:
        return None
    if not smtp.get("host") or not smtp.get("username") or not smtp.get("password"):
        return None
    return {"host": smtp["host"], "port": int(smtp.get("port", 587)),
            "username": smtp["username"], "password": smtp["password"],
            "pengirim": smtp.get("pengirim", smtp["username"]),
            "url_aplikasi": app.get("url_aplikasi", "")}


def kirim_email_verifikasi(pengaturan: dict, tujuan: str, nama: str, link: str) -> tuple[bool, str]:
    """Kirim email verifikasi via SMTP (murni IO, terpisah agar mudah diganti)."""
    try:
        pesan = EmailMessage()
        pesan["Subject"] = "Verifikasi email akun Anda"
        pesan["From"] = pengaturan["pengirim"]
        pesan["To"] = tujuan
        pesan.set_content(
            f"Halo {nama},\n\nTerima kasih telah mendaftar. "
            f"Tekan tautan berikut dalam 24 jam untuk mengaktifkan akun:\n{link}\n\n"
            "Abaikan email ini bila Anda tidak mendaftar.")
        with smtplib.SMTP(pengaturan["host"], pengaturan["port"], timeout=20) as server:
            server.starttls()
            server.login(pengaturan["username"], pengaturan["password"])
            server.send_message(pesan)
        return True, "Email verifikasi terkirim."
    except Exception as e:
        return False, f"Email gagal terkirim: {e}"


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


def _masuk(identitas: str) -> None:
    st.session_state["masuk"] = True
    st.session_state["pengguna"] = identitas.strip()
    st.rerun()


def _tangani_link_verifikasi() -> None:
    """Proses ?verifikasi=token dari link email, lalu kembali ke halaman masuk."""
    try:
        token = st.query_params.get("verifikasi", "")
    except Exception:
        return
    if not token:
        return
    from db.sqlite import verifikasi_token
    con = _db()
    try:
        ok, pesan = verifikasi_token(con, token)
    finally:
        con.close()
    try:
        st.query_params.clear()
    except Exception:
        pass
    if ok:
        st.success(pesan)
    else:
        st.error(pesan)


def _form_masuk() -> None:
    with st.form("form_login"):
        identitas = st.text_input("Email atau nama pengguna")
        password = st.text_input("Kata sandi", type="password")
        tombol = st.form_submit_button("Masuk")
    if tombol:
        from db.sqlite import ambil_pengguna
        con = _db()
        try:
            akun = ambil_pengguna(con, identitas)
        finally:
            con.close()
        if verifikasi(identitas, password, ambil_kredensial()):
            _masuk(identitas)
        elif akun is not None and cek_hash(password or "", akun.get("pwd_hash") or ""):
            if int(akun.get("terverifikasi") or 0) != 1:
                st.error("Email belum diverifikasi. Buka link di email Anda terlebih dahulu.")
            else:
                _masuk(akun.get("email") or identitas)
        else:
            st.error("Email/nama pengguna atau kata sandi salah.")
    st.caption("Akun demo: tamu / demo123")


def _form_daftar() -> None:
    with st.form("form_daftar"):
        nama = st.text_input("Nama")
        email = st.text_input("Email")
        password = st.text_input("Buat kata sandi (min. 6 karakter)", type="password")
        ulangi = st.text_input("Konfirmasi kata sandi", type="password")
        tombol = st.form_submit_button("Daftar")
    if not tombol:
        return
    nama_bersih = (nama or "").strip()
    email_bersih = (email or "").strip().lower()
    if not nama_bersih:
        st.error("Nama wajib diisi.")
    elif not email_valid(email_bersih):
        st.error("Format email tidak valid.")
    elif not password or len(password) < 6:
        st.error("Kata sandi minimal 6 karakter.")
    elif password != ulangi:
        st.error("Konfirmasi kata sandi tidak sama.")
    else:
        from db.sqlite import tambah_pengguna
        token, exp = buat_token()
        con = _db()
        try:
            ok, pesan = tambah_pengguna(con, nama_bersih, email_bersih, buat_hash(password), token, exp)
        finally:
            con.close()
        if not ok:
            st.error(pesan)
            return
        smtp = ambil_smtp()
        if smtp and smtp["url_aplikasi"]:
            terkirim, info = kirim_email_verifikasi(
                smtp, email_bersih, nama_bersih, link_verifikasi(smtp["url_aplikasi"], token))
            if terkirim:
                st.success("Pendaftaran berhasil. Buka email Anda dan tekan tautan verifikasi, "
                           "lalu kembali masuk di sini.")
            else:
                st.warning(f"{info} Salin tautan berikut ke browser dan tekan Enter: "
                           f"{link_verifikasi(smtp['url_aplikasi'], token)}")
        else:
            st.info("Pendaftaran berhasil. Email belum dikonfigurasi (mode demo), "
                    "buka tautan verifikasi berikut lalu kembali masuk:")
            st.code(link_verifikasi("http://localhost:8501", token))


def wajib_login() -> str:
    """Tampilkan halaman Masuk/Daftar bila belum masuk; kembalikan identitas bila lolos.

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
    _tangani_link_verifikasi()
    tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar akun baru"])
    with tab_masuk:
        _form_masuk()
    with tab_daftar:
        _form_daftar()
    st.stop()
    return ""
