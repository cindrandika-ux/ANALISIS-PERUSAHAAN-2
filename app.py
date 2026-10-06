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
from prediction.narasi import (DISCLAIMER, LABEL_ID, buat_narasi, kategori_final,
                               pilih_pendukung_risiko)
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


# Nama tampilan berbahasa Indonesia (kode internal tetap dipakai untuk hitungan).
NAMA_AKUN = {
    "kas": "Kas dan setara kas", "piutang": "Piutang", "persediaan": "Persediaan",
    "aset_lancar": "Aset lancar", "total_aset": "Total aset",
    "liab_pendek": "Liabilitas jangka pendek", "liab_panjang": "Liabilitas jangka panjang",
    "total_liab": "Total liabilitas", "ekuitas": "Ekuitas", "laba_ditahan": "Laba ditahan",
    "pendapatan": "Pendapatan", "laba_kotor": "Laba kotor", "laba_usaha": "Laba usaha",
    "beban_bunga": "Beban bunga", "laba_sebelum_pajak": "Laba sebelum pajak",
    "laba_bersih": "Laba bersih", "cfo": "Arus kas operasi", "cfi": "Arus kas investasi",
    "cff": "Arus kas pendanaan", "kas_akhir": "Kas akhir tahun",
}
NAMA_KOMPONEN = {
    "posisi_keuangan": "Laporan posisi keuangan", "laba_rugi_komprehensif": "Laporan laba rugi",
    "perubahan_ekuitas": "Laporan perubahan ekuitas", "arus_kas": "Laporan arus kas",
    "calk": "Catatan atas laporan keuangan",
}


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
st.sidebar.caption(f"Fitur baca dokumen scan (OCR): {'Siap' if tess['tersedia'] else 'Belum tersedia di perangkat ini'}")

con = konek()
init_db(con)
with st.sidebar.expander("Data tersimpan"):
    st.write("Perusahaan tersimpan:", daftar_perusahaan(con) or ["(kosong)"])
    if st.button("Muat contoh perusahaan demo"):
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
        st.caption(f"Dokumen terbaca: {ek['jumlah_halaman']} halaman.")
        if ek["perlu_ocr"]:
            st.warning("Dokumen ini hasil scan. Membaca gambar dokumen...")
            ocr = ocr_pdf_scan(data_bytes)
            if ocr["ok"]:
                teks = ocr["teks"]
                st.success(f"Dokumen scan berhasil dibaca ({ocr['halaman']} halaman). Tetap periksa tabel di bawah.")
            else:
                st.error("Dokumen scan tidak terbaca. Coba unggah PDF yang teksnya bisa disalin.")
                continue

        # Validasi isi
        opini = deteksi_opini(teks)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Opini auditor")
            st.write(f"Laporan auditor: {'Ditemukan' if opini['ada_laporan_auditor'] else 'Tidak ditemukan'}")
            arti_opini = {"WTP": "Wajar Tanpa Pengecualian (baik)", "WDP": "Wajar Dengan Pengecualian",
                          "TW": "Tidak Wajar", "Disclaimer": "Auditor tidak memberi pendapat",
                          "TIDAK_DITEMUKAN": "tidak terbaca"}.get(opini["opini"], opini["opini"])
            st.write(f"Hasil audit: **{arti_opini}**")
            if opini["peringatan"]:
                st.warning(opini["peringatan"])
        with col2:
            st.subheader("Kelengkapan laporan & kerangka")
            psak = cek_kelengkapan_psak1(teks)
            for kode, ada in psak["komponen"].items():
                st.write(f"{'✓' if ada else '✗'} {NAMA_KOMPONEN.get(kode, kode)}")
            if not psak["lengkap"]:
                st.warning("Ada komponen tidak lengkap. Tetap bisa lanjut, tetapi hasil kurang maksimal.")
            kerangka = deteksi_kerangka(teks)
            st.write(f"Kerangka: **{kerangka['kerangka']}**")
            if not kerangka["ditemukan"]:
                st.info("Kerangka tidak ditemukan di teks — ditandai apa adanya (tidak menebak).")

        # Ekstraksi + human-in-the-loop
        satuan = deteksi_satuan(teks)
        satuan_teks = {"penuh": "Rupiah penuh", "ribu": "ribuan Rupiah (otomatis dikali 1.000)",
                       "juta": "jutaan Rupiah (otomatis dikali 1.000.000)"}.get(satuan["satuan"], "Rupiah")
        st.info(f"Satuan angka laporan: {satuan_teks}.")
        hasil_ek = ekstrak_akun(teks, pengali=float(satuan["pengali"]))
        df = pd.DataFrame(ringkas_ke_tabel(hasil_ek))
        df["Nama akun"] = df["akun"].map(lambda k: NAMA_AKUN.get(k, k))
        st.subheader("Hasil pembacaan (periksa & ubah bila perlu)")
        edited_f = st.data_editor(df, num_rows="fixed", use_container_width=True,
                                  key=f"editor_{idx}",
                                  column_order=["Nama akun", "tahun_berjalan", "komparatif"],
                                  column_config={"Nama akun": st.column_config.TextColumn("Nama akun", disabled=True),
                                                 "tahun_berjalan": st.column_config.NumberColumn("Tahun berjalan (Rp)"),
                                                 "komparatif": st.column_config.NumberColumn("Tahun lalu (Rp)")})
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

st.subheader("Pemeriksaan keseimbangan")
nrc = cek_keseimbangan_neraca(cur.get("total_aset"), cur.get("total_liab"), cur.get("ekuitas"))
kas_c = cek_kas_akhir(cur.get("kas"), cur.get("kas_akhir"))
if nrc["ok"]:
    st.success("Neraca seimbang: Aset = Liabilitas + Ekuitas.")
else:
    st.warning(nrc["pesan"] or "Data neraca belum lengkap.")
if kas_c["ok"]:
    st.success("Kas sesuai antara neraca dan laporan arus kas.")
else:
    st.warning(kas_c["pesan"] or "Data kas belum lengkap.")

st.subheader("Rasio keuangan (lengkap dengan rumus)")
rasio = hitung_rasio(cur)
rtabel = pd.DataFrame([{"Nama": LABEL_ID.get(k, k), "Nilai": v,
                        "Rumus": RASIO_INFO.get(k, {}).get("rumus", ""),
                        "Penjelasan": RASIO_INFO.get(k, {}).get("penjelasan", "")}
                       for k, v in rasio.items()])
st.dataframe(rtabel, use_container_width=True, hide_index=True)

with st.expander("Proporsi tiap pos laporan"):
    n_size = common_size_neraca(cur)
    st.write("Neraca (% dari total aset):")
    st.dataframe(pd.DataFrame(
        [{"Pos": NAMA_AKUN.get(k, k),
          "Proporsi": "tidak ditemukan" if v is None else f"{v:.1f}%"}
         for k, v in n_size.items()]), use_container_width=True, hide_index=True)
    l_size = common_size_laba_rugi(cur)
    st.write("Laba rugi (% dari pendapatan):")
    st.dataframe(pd.DataFrame(
        [{"Pos": NAMA_AKUN.get(k, k),
          "Proporsi": "tidak ditemukan" if v is None else f"{v:.1f}%"}
         for k, v in l_size.items()]), use_container_width=True, hide_index=True)

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
st.write("Kekuatan:", ", ".join(f"{LABEL_ID.get(k, k)}" for k, v in pr["pendukung"]) or "-")
st.write("Risiko:", ", ".join(f"{LABEL_ID.get(k, k)}" for k, v in pr["risiko"]) or "-")

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
