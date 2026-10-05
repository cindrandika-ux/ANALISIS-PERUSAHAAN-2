# Prediktor Kesehatan Keuangan Perusahaan Dagang

Aplikasi Streamlit untuk tugas kuliah: unggah PDF laporan keuangan teraudit,
validasi SAK/PSAK, ekstraksi + tabel edit, rasio/tren/common-size,
skor + Altman Z'' + proyeksi, unduh PDF. Bahasa Indonesia, Rupiah.

## Instalasi (Windows)
1. `python -m venv venv` lalu `venv\\Scripts\\activate`
2. `pip install -r requirements.txt`
3. Instal Tesseract OCR (wajib untuk PDF scan), isi `.env` dari `.env.example`:
   `TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe`
4. `pytest -q` (35 tes, data fiktif)

## Menjalankan
- Demo cepat: `venv\\Scripts\\streamlit run app.py`
- Di sidebar klik "Muat data fiktif 2022-2024", lalu unggah PDF.
- Edit tabel ekstraksi sebelum analisis (human-in-the-loop), simpan ke SQLite (`keuangan.db`).

## Arsitektur
- `app.py` — dashboard + alur.
- `validators/` — file_check (magic bytes), opini_audit (WTP/WDP/TW/Disclaimer),
  psak1_check (5 komponen + SAK Umum/EP/EMKM), konsistensi (A=L+E, kas akhir).
- `extractors/` — pdf_text (pdfplumber+PyMuPDF), ocr_fallback (pytesseract),
  angka_parser (format ID + ribu/juta), akun_dagang (19 akun, komparatif).
- `analysis/` — rasio (16 + rumus edukatif), tren, commonsize.
- `prediction/` — skor bobot-atur, altman Z'', proyeksi regresi (min 3 thn), narasi rule-based + disclaimer.
- `db/` — SQLite multi-perusahaan (`schema.sql`).
- `report/` — unduh PDF (fpdf2).
- `tests/` + `data_contoh/` (FIKTIF PT Dagang Sejahtera 2022-2024, bukan data riil).

## Catatan
- Hilang → "tidak ditemukan", jangan menebak. Bukan WTP → peringatan.
- Proyeksi hanya bila ≥3 tahun, else pesan jujur. Bukan nasihat investasi.
