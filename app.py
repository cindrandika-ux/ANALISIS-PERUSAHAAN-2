"""Dashboard Streamlit Prediktor Kesehatan Keuangan (perusahaan dagang, Bahasa Indonesia).

Alur: unggah PDF -> validasi -> ekstrak -> tabel editable -> simpan SQLite
-> rasio/tren/common-size -> skor + Altman Z'' + proyeksi -> unduh PDF.
Angka dihitung Python; tidak ada LLM. Satuan Rupiah.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from analysis.commonsize import common_size_laba_rugi, common_size_neraca
from analysis.rasio import RASIO_INFO, hitung_rasio
from analysis.tren import hitung_perubahan
from db.sqlite import ambil_historis, daftar_perusahaan, init_db, konek, simpan_laporan
from extractors.akun_dagang import ekstrak_akun, ringkas_ke_tabel
from extractors.angka_parser import deteksi_satuan
from extractors.ocr_fallback import cek_tesseract_tersedia, ocr_pdf_scan
from extractors.pdf_text import ekstrak_teks
from prediction.altman import hitung_zpp
from prediction.narasi import DISCLAIMER, buat_narasi, kategori_final, pilih_pendukung_risiko
from prediction.proyeksi import proyeksi_regresi
from prediction.skor import BOBOT_DEFAULT, hitung_skor, kategori_dari_skor
from report.pdf_laporan import buat_pdf
from validators.file_check import validasi_pdf
from validators.konsistensi import cek_kas_akhir, cek_keseimbangan_neraca
from validators.opini_audit import deteksi_opini
from validators.psak1_check import cek_kelengkapan_psak1, deteksi_kerangka

st.set_page_config(page_title="Prediktor Kesehatan Keuangan", layout="wide",
                   initial_sidebar_state="expanded")

# Tema formal-simpel-modern: navy + putih, kartu bersih, tanpa emoji.
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1180px; }
.hero { background: #1F3A5F; color: #FFFFFF; border-radius: 12px; padding: 22px 26px; margin-bottom: 14px; }
.hero h1 { font-size: 1.5rem; margin: 0 0 4px 0; font-weight: 700; }
.hero p { margin: 0; opacity: 0.88; font-size: 0.95rem; }
.step { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        padding: 8px 12px; text-align: center; font-size: 0.82rem; color: #1F3A5F; font-weight: 600; }
.step small { display: block; font-weight: 400; color: #64748B; }
.card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px 18px; }
.stMetric { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 10px 14px; }
.stButton > button { background: #1F3A5F; color: #FFFFFF; border-radius: 8px; border: none; font-weight: 600; }
.stButton > button:hover { background: #2C4E7E; color: #FFFFFF; }
.stDownloadButton > button { border-radius: 8px; font-weight: 600; }
[data-testid="stFileUploader"] section { border: 1px dashed #94A3B8;
        border-radius: 12px; background: #FFFFFF; }
footer { visibility: hidden; }
.foot { color: #64748B; font-size: 0.8rem; border-top: 1px solid #E2E8F0; padding-top: 10px; margin-top: 18px; }
</style>
<div class="hero">
<h1>Prediktor Kesehatan Keuangan Perusahaan Dagang</h1>
<p>Unggah laporan teraudit (PDF) &mdash; validasi PSAK &mdash; ekstraksi terverifikasi &mdash; rasio &mdash; prediksi tahun depan. Bahasa Indonesia, Rupiah.</p>
</div>
""", unsafe_allow_html=True)


def rp(x) -> str:
    """Format Rupiah penuh atau 'tidak ditemukan'."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "tidak ditemukan"
    try:
        return f"Rp{float(x):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "tidak ditemukan"


# ---------- Sidebar ----------
st.sidebar.header("Pengaturan")
nama_perusahaan = st.sidebar.text_input("Nama perusahaan", "PT Dagang Sejahtera Fiktif")
max_mb = st.sidebar.number_input("Batas PDF (MB)", 1, 100, int(os.getenv("MAX_PDF_MB", "20")))
st.sidebar.subheader("Bobot skor (%)")
b_lik = st.sidebar.slider("Likuiditas", 0, 60, int(BOBOT_DEFAULT["likuiditas"] * 100))
b_sol = st.sidebar.slider("Solvabilitas", 0, 60, int(BOBOT_DEFAULT["solvabilitas"] * 100))
b_prof = st.sidebar.slider("Profitabilitas", 0, 60, int(BOBOT_DEFAULT["profitabilitas"] * 100))
b_akt = st.sidebar.slider("Aktivitas+Kas", 0, 60, int(BOBOT_DEFAULT["aktivitas_kas"] * 100))
tess = cek_tesseract_tersedia()
st.sidebar.caption(f"OCR Tesseract: {'OK' if tess['tersedia'] else 'belum ada — ' + (tess['pesan'][:80])}")

con = konek()
init_db(con)
with st.sidebar.expander("Database lokal"):
    st.write("Perusahaan tersimpan:", daftar_perusahaan(con) or ["(kosong)"])
    if st.button("Muat data fiktif 2022-2024 (demo)"):
        csv_path = Path(__file__).parent / "data_contoh" / "seed_historis_2022_2024.csv"
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    data = {k: (float(row[k]) if row.get(k) else None)
                            for k in ["kas", "piutang", "persediaan", "aset_lancar", "total_aset",
                                      "liab_pendek", "liab_panjang", "total_liab", "ekuitas",
                                      "laba_ditahan", "pendapatan", "laba_kotor", "laba_usaha",
                                      "beban_bunga", "laba_sebelum_pajak", "laba_bersih",
                                      "cfo", "cfi", "cff"]}
                    simpan_laporan(con, nama_perusahaan, int(row["tahun"]), data, sumber="csv-fiktif")
            st.success("Data fiktif dimuat. Bukan data riil.")
        except FileNotFoundError:
            st.error("File data_contoh/seed_historis_2022_2024.csv tidak ditemukan.")

# ---------- Main ----------
c1, c2, c3, c4, c5 = st.columns(5)
for col, (n, d) in zip([c1, c2, c3, c4, c5],
                        [("1. Unggah", "PDF teraudit"), ("2. Validasi", "Opini + PSAK 1"),
                         ("3. Ekstraksi", "Tabel editable"), ("4. Analisis", "Rasio + tren"),
                         ("5. Prediksi", "Skor + Z'' + PDF")]):
    col.markdown(f'<div class="step">{n}<small>{d}</small></div>', unsafe_allow_html=True)
st.write("")

st.subheader("1. Unggah laporan")
kol_thn, _kosong = st.columns([1, 3])
with kol_thn:
    tahun_terbaru = st.number_input("Tahun laporan", min_value=2000, max_value=2100,
                                    value=2024, step=1,
                                    help="Tahun buku laporan terbaru (mis. 2024). Untuk >1 file, tahun berikutnya terisi mundur otomatis dan bisa diubah per file.")
berkas_list = st.file_uploader("Dropzone PDF teraudit — bisa lebih dari satu file",
                               type=["pdf"], accept_multiple_files=True,
                               help="Seret satu atau beberapa PDF laporan teraudit, maksimal sesuai batas di sidebar.")
if not berkas_list:
    st.info("Silakan unggah PDF untuk mulai. Contoh demo: gunakan data fiktif via sidebar + unggah PDF apa pun bertipe PDF.")
    st.stop()

st.write("Tahun per file (sesuaikan bila perlu):")
kolom_tahun = st.columns(len(berkas_list))
tahun_per_file: list[int] = []
for i, (kol, f) in enumerate(zip(kolom_tahun, berkas_list)):
    with kol:
        t = st.number_input(f"{f.name[:30]}", min_value=2000, max_value=2100,
                            value=int(tahun_terbaru) - i, step=1, key=f"thn_file_{i}")
        tahun_per_file.append(int(t))

# Validasi + ekstraksi per file dalam tab (mendukung >1 PDF)
data_per_file: dict[int, dict] = {}
edited_per_file = {}
tab_semua = st.tabs([f"{thn} — {f.name[:24]}" for f, thn in zip(berkas_list, tahun_per_file)])
for idx, tab in enumerate(tab_semua):
    f = berkas_list[idx]
    thn = tahun_per_file[idx]
    with tab:
        data_bytes = f.getvalue()
        hasil_file = validasi_pdf(f.name, data_bytes, max_mb=float(max_mb))
        if not hasil_file["ok"]:
            for e in hasil_file["errors"]:
                st.error(f"{f.name}: {e}")
            continue
        st.success(f"{f.name} OK: {hasil_file['ukuran_mb']} MB.")

        ek = ekstrak_teks(data_bytes)
        teks = ek["teks"]
        st.caption(f"Ekstraksi: {ek['metode']} | {ek['jumlah_halaman']} halaman | {ek['jumlah_karakter']} karakter.")
        if ek["perlu_ocr"]:
            st.warning("Teks minim — diduga PDF scan. Menjalankan OCR (pytesseract)...")
            ocr = ocr_pdf_scan(data_bytes)
            if ocr["ok"]:
                teks = ocr["teks"]
                st.success(f"OCR berhasil ({ocr['halaman']} halaman). Selalu verifikasi di tabel edit.")
            else:
                st.error(ocr["pesan"])
                continue

        # Validasi isi
        opini = deteksi_opini(teks)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Opini auditor")
            st.write(f"Ada laporan auditor: {'Ya' if opini['ada_laporan_auditor'] else 'Tidak'}")
            st.write(f"Opini: **{opini['opini']}**")
            if opini["peringatan"]:
                st.warning(opini["peringatan"])
        with col2:
            st.subheader("Kelengkapan PSAK 1 & kerangka")
            psak = cek_kelengkapan_psak1(teks)
            st.write({k: ("ada" if v else "HILANG") for k, v in psak["komponen"].items()})
            if not psak["lengkap"]:
                st.warning(f"Komponen hilang: {', '.join(psak['hilang'])}. Tetap bisa lanjut, tetapi validasi kurang.")
            kerangka = deteksi_kerangka(teks)
            st.write(f"Kerangka: **{kerangka['kerangka']}**")
            if not kerangka["ditemukan"]:
                st.info("Kerangka tidak ditemukan di teks — ditandai apa adanya (tidak menebak).")

        # Ekstraksi + human-in-the-loop
        satuan = deteksi_satuan(teks)
        st.info(f"Satuan terdeteksi: {satuan['satuan']} (x{satuan['pengali']:,}). Nilai di bawah sudah dinormalisasi ke Rupiah penuh.")
        hasil_ek = ekstrak_akun(teks, pengali=float(satuan["pengali"]))
        df = pd.DataFrame(ringkas_ke_tabel(hasil_ek))
        st.subheader("Hasil ekstraksi (periksa & edit sebelum analisis)")
        edited_f = st.data_editor(df, num_rows="fixed", use_container_width=True,
                                  key=f"editor_{idx}",
                                  column_config={"tahun_berjalan": st.column_config.NumberColumn("Tahun berjalan (Rp)"),
                                                 "komparatif": st.column_config.NumberColumn("Komparatif t-1 (Rp)")})
        if st.button(f"Simpan {thn} ke database", key=f"simpan_{idx}"):
            data_simpan = {}
            for _, r in edited_f.iterrows():
                v = r["tahun_berjalan"]
                data_simpan[r["akun"]] = None if pd.isna(v) else float(v)
            simpan_laporan(con, nama_perusahaan, thn, data_simpan, sumber="pdf-edit")
            st.success(f"Tersimpan: {nama_perusahaan} {thn}.")

        cur_f = {}
        for _, r in edited_f.iterrows():
            v = r["tahun_berjalan"]
            cur_f[r["akun"]] = None if pd.isna(v) else float(v)
        if thn in data_per_file:
            st.warning(f"Tahun {thn} ganda — file terakhir yang dipakai untuk tahun ini.")
        data_per_file[thn] = cur_f
        edited_per_file[thn] = edited_f

if not data_per_file:
    st.error("Tidak ada file valid untuk dianalisis.")
    st.stop()

# Analisis memakai file tahun terbesar sebagai tahun berjalan
tahun_laporan = max(data_per_file)
edited = edited_per_file[tahun_laporan]
st.subheader(f"Analisis tahun berjalan: {tahun_laporan}")

# Analisis tahun berjalan (dari file tahun terbesar)
cur = data_per_file[tahun_laporan]

st.subheader("Konsistensi dasar")
nrc = cek_keseimbangan_neraca(cur.get("total_aset"), cur.get("total_liab"), cur.get("ekuitas"))
kas_c = cek_kas_akhir(cur.get("kas"), cur.get("kas_akhir"))
for cek in (nrc, kas_c):
    (st.success("OK") if cek["ok"] else st.warning(cek["pesan"] or "tidak ditemukan"))

st.subheader("Rasio (dengan rumus edukatif)")
rasio = hitung_rasio(cur)
rtabel = pd.DataFrame([{"rasio": k, "nilai": v,
                        "rumus": RASIO_INFO.get(k, {}).get("rumus", ""),
                        "penjelasan": RASIO_INFO.get(k, {}).get("penjelasan", "")}
                       for k, v in rasio.items()])
st.dataframe(rtabel, use_container_width=True)

with st.expander("Common-size"):
    st.write("Neraca (% total aset):", common_size_neraca(cur))
    st.write("Laba rugi (% pendapatan):", common_size_laba_rugi(cur))

# Gabung historis DB + semua tahun yang diunggah + komparatif untuk tren/proyeksi
hist = {h["tahun"]: h for h in ambil_historis(con, nama_perusahaan)}
for thn, dat in data_per_file.items():
    hist[thn] = {**hist.get(thn, {}), **dat, "tahun": thn}
komp_tahun = int(tahun_laporan) - 1
if komp_tahun not in hist:
    komp = {}
    for _, r in edited.iterrows():
        v = r["komparatif"]
        komp[r["akun"]] = None if pd.isna(v) else float(v)
    if any(v is not None for v in komp.values()):
        hist[komp_tahun] = {**komp, "tahun": komp_tahun}
tahuns = sorted(hist)
if len(tahuns) >= 2:
    st.subheader("Tren")
    for kunci, label in [("pendapatan", "Pendapatan"), ("laba_bersih", "Laba bersih")]:
        seri = [(t, hist[t].get(kunci)) for t in tahuns]
        perubahan = hitung_perubahan(seri[-2][1], seri[-1][1])
        st.write(f"{label}: {rp(seri[-2][1])} -> {rp(seri[-1][1])} "
                 f"({perubahan['arah']}, {perubahan['persen']:.1f}% )" if perubahan["persen"] is not None
                 else f"{label}: {perubahan['arah']}")
    df_tren = pd.DataFrame([{"tahun": t, "pendapatan": hist[t].get("pendapatan"),
                             "laba_bersih": hist[t].get("laba_bersih")} for t in tahuns])
    fig1 = px.line(df_tren, x="tahun", y=["pendapatan", "laba_bersih"],
                   markers=True, title="Tren pendapatan & laba bersih (Rp)",
                   color_discrete_sequence=["#1F3A5F", "#2F9E8F"])
    fig1.update_layout(template="simple_white", font=dict(size=12))
    st.plotly_chart(fig1, use_container_width=True)
    r_hist = {t: hitung_rasio(hist[t]) for t in tahuns}
    df_r = pd.DataFrame([{"tahun": t, "current_ratio": r_hist[t].get("current_ratio"),
                          "der": r_hist[t].get("der")} for t in tahuns])
    fig2 = px.line(df_r, x="tahun", y=["current_ratio", "der"],
                   markers=True, title="Tren rasio lancar & DER",
                   color_discrete_sequence=["#1F3A5F", "#B7792B"])
    fig2.update_layout(template="simple_white", font=dict(size=12))
    st.plotly_chart(fig2, use_container_width=True)

# Prediksi
st.subheader("Prediksi kesehatan tahun depan")
bobot = {"likuiditas": b_lik / 100, "solvabilitas": b_sol / 100,
         "profitabilitas": b_prof / 100, "aktivitas_kas": b_akt / 100}
skor = hitung_skor(rasio, bobot=bobot)
zh = hitung_zpp(cur)
kat_skor = kategori_dari_skor(skor["skor_total"])
final = kategori_final(kat_skor, zh["kategori"])
pr = pilih_pendukung_risiko(skor["skor_detail"])
st.metric("Kategori", final)
st.write(f"Skor: **{skor['skor_total']:.1f}/100** ({kat_skor})" if skor["skor_total"] is not None else "Skor: tidak ditemukan")
st.write(f"Altman Z'': **{zh['z']:.2f} ({zh['kategori']})**" if zh["z"] is not None else "Z'': tidak ditemukan")
st.caption(zh["penjelasan"])
st.write("Pendukung:", ", ".join(f"{k} ({v:.0f})" for k, v in pr["pendukung"]) or "-")
st.write("Risiko:", ", ".join(f"{k} ({v:.0f})" for k, v in pr["risiko"]) or "-")

pend_series = [hist[t].get("pendapatan") for t in tahuns]
proj = proyeksi_regresi(tahuns, pend_series) if len(tahuns) >= 2 else {"bisa_dipakai": False, "pesan": "Belum ada historis."}
if proj["bisa_dipakai"]:
    st.success(f"Proyeksi pendapatan {proj['tahun_prediksi']}: {rp(proj['prediksi'])} (regresi linear, n={proj['n_data']}).")
else:
    st.info(proj.get("pesan", "Proyeksi tidak tersedia (<3 tahun). Menampilkan skor + Z-Score saja."))

narasi = buat_narasi(nama_perusahaan, int(tahun_laporan), skor["skor_total"], final,
                     zh["z"], zh["kategori"], pr["pendukung"], pr["risiko"], proj["bisa_dipakai"])
st.info(narasi)
st.warning(DISCLAIMER)

pdf_bytes = buat_pdf(nama_perusahaan, int(tahun_laporan), final, skor["skor_total"],
                     zh["z"], zh["kategori"], rasio, pr["pendukung"], pr["risiko"], narasi, DISCLAIMER)
st.download_button("Unduh hasil (PDF)", data=pdf_bytes, file_name=f"analisis_{tahun_laporan}.pdf",
                   mime="application/pdf")
st.markdown('<div class="foot">Formal &bull; simpel &bull; modern &mdash; data fiktif untuk tugas kuliah. Estimasi historis, bukan nasihat investasi.</div>',
            unsafe_allow_html=True)
