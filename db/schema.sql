-- Skema SQLite lokal untuk data historis.
-- Perusahaan dagang fiktif, multi-tahun.
CREATE TABLE IF NOT EXISTS perusahaan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS laporan_keuangan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perusahaan_id INTEGER NOT NULL REFERENCES perusahaan(id),
    tahun INTEGER NOT NULL,
    kas REAL, piutang REAL, persediaan REAL,
    aset_lancar REAL, total_aset REAL,
    liab_pendek REAL, liab_panjang REAL, total_liab REAL,
    ekuitas REAL, laba_ditahan REAL,
    pendapatan REAL, laba_kotor REAL, laba_usaha REAL,
    beban_bunga REAL, laba_sebelum_pajak REAL, laba_bersih REAL,
    cfo REAL, cfi REAL, cff REAL,
    sumber TEXT DEFAULT 'manual/csv/pdf',
    UNIQUE(perusahaan_id, tahun)
);

-- Akun pengguna (kata sandi tersimpan sebagai hash, bukan teks asli).
CREATE TABLE IF NOT EXISTS pengguna (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    pwd_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
