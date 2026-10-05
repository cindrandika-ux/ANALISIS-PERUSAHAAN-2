"""Unit test Modul 5: SQLite roundtrip + PDF unduhan (fiktif)."""
import sqlite3

from db.sqlite import ambil_historis, daftar_perusahaan, init_db, konek, simpan_laporan
from report.pdf_laporan import buat_pdf


def _mem():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    init_db(con)
    return con


def test_sqlite_simpan_dan_ambil():
    con = _mem()
    data = {"kas": 1050000000.0, "laba_bersih": 1000000000.0, "pendapatan": 12000000000.0}
    simpan_laporan(con, "PT Dagang Fiktif", 2024, data, sumber="test")
    hist = ambil_historis(con, "PT Dagang Fiktif")
    assert len(hist) == 1 and hist[0]["tahun"] == 2024
    assert hist[0]["kas"] == 1050000000.0
    # Upsert tahun sama menimpa
    simpan_laporan(con, "PT Dagang Fiktif", 2024, {**data, "kas": 1.0}, sumber="test2")
    assert ambil_historis(con, "PT Dagang Fiktif")[0]["kas"] == 1.0
    assert "PT Dagang Fiktif" in daftar_perusahaan(con)


def test_konek_db_path_env(tmp_path, monkeypatch):
    p = tmp_path / "uji.db"
    monkeypatch.setenv("DB_PATH", str(p))
    con = konek()
    init_db(con)
    con.close()
    assert p.exists()


def test_pdf_dimulai_dengan_persen_pdf():
    pdf = buat_pdf("PT Dagang Fiktif", 2024, "Sehat", 85.0, 5.73, "Sehat",
                   {"current_ratio": 2.17, "der": 0.68},
                   [("current_ratio", 100.0)], [("der", 50.0)],
                   "Ringkasan fiktif.", "Disclaimer fiktif.")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
