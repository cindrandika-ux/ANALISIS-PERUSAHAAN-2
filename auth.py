"""Gerbang login sederhana untuk demo (bukan pengganti SSO instansi).

Kredensial dibaca dari secrets Streamlit ([passwords] di
.streamlit/secrets.toml lokal atau Secrets pada Streamlit Cloud),
BUKAN hardcoded di kode. Perbandingan memakai hmac agar waktu
komparasi tidak bocor lewat timing.
"""
from __future__ import annotations

import hmac

import streamlit as st


def ambil_kredensial() -> dict:
    """Ambil dict username -> password dari secrets (kosong bila belum diisi)."""
    try:
        return dict(st.secrets.get("passwords", {}))
    except Exception:
        return {}


def verifikasi(username: str, password: str, kredensial: dict) -> bool:
    """Cek pasangan username/password (murni, bisa di-unit-test)."""
    if not username or password is None:
        return False
    tersimpan = kredensial.get((username or "").strip())
    if tersimpan is None:
        return False
    return hmac.compare_digest(str(password), str(tersimpan))


def wajib_login() -> str:
    """Tampilkan form login bila belum masuk; kembalikan username bila lolos.

    Harus dipanggil di awal sebelum konten lain agar tidak bocor.
    """
    if st.session_state.get("masuk"):
        with st.sidebar:
            st.caption(f"Masuk sebagai: {st.session_state.get('pengguna', '-')}")
            if st.button("Keluar"):
                st.session_state.clear()
                st.rerun()
        return str(st.session_state.get("pengguna", ""))

    st.markdown("### Masuk")
    st.write("Silakan masuk untuk memakai aplikasi ini.")
    with st.form("form_login"):
        username = st.text_input("Nama pengguna")
        password = st.text_input("Kata sandi", type="password")
        tombol = st.form_submit_button("Masuk")
    if tombol:
        if verifikasi(username, password, ambil_kredensial()):
            st.session_state["masuk"] = True
            st.session_state["pengguna"] = username.strip()
            st.rerun()
        else:
            st.error("Nama pengguna atau kata sandi salah.")
    st.stop()
    return ""
