import json
from pathlib import Path

import pandas as pd

FLUKS_MIN = 0.35
FLUKS_MAX = 1.10
SUHU_MIN = 175
SUHU_MAX = 275

FILE_DATA = Path("data_nasa.xlsx")
FILE_BERSIH = Path("data_planet_bersih.csv")
FILE_PETA = Path("planet_per_sistem.json")

NAMA_KOLOM = {
    "planet_name": "pl_name",
    "host_star_name": "hostname",
    "num_planets_in_system": "sy_pnum",
    "planet_radius_earth_radius": "pl_rade",
    "orbit_semi_major_axis_au": "pl_orbsmax",
    "orbital_period_days": "pl_orbper",
    "insolation_flux_earth_flux": "pl_insol",
    "equilibrium_temperature_k": "pl_eqt",
    "stellar_effective_temp_k": "st_teff",
    "stellar_radius_solar_radius": "st_rad",
    "is_controversial": "kontroversial",
}
KOLOM = list(NAMA_KOLOM.values())


def muat_data():
    if not FILE_DATA.exists():
        raise SystemExit("File data_nasa.xlsx tidak ditemukan di folder ini")
    print("Membaca", FILE_DATA)
    mentah = pd.read_excel(FILE_DATA)
    print("Jumlah planet:", len(mentah))
    print("Jumlah kolom di file:", mentah.shape[1])
    df = mentah[list(NAMA_KOLOM)].rename(columns=NAMA_KOLOM)
    print("Persen nilai kosong di kolom yang dipakai:")
    print((df.isna().mean() * 100).round(1).to_string())
    return df


def bersihkan(df):
    df = df.copy()
    df["pl_name"] = df["pl_name"].astype(str).str.strip()
    df["hostname"] = df["hostname"].astype(str).str.strip()
    angka = [k for k in KOLOM if k not in ("pl_name", "hostname")]
    for k in angka:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    df = df.drop_duplicates(subset="pl_name")
    return df.reset_index(drop=True)


def cek_fluks(x):
    if pd.isna(x):
        return None, "fluks tidak tercatat"
    if x < FLUKS_MIN:
        return False, f"fluks {x:.2f} kali Bumi, terlalu dingin"
    if x > FLUKS_MAX:
        return False, f"fluks {x:.2f} kali Bumi, terlalu panas"
    return True, f"fluks {x:.2f} kali Bumi, masuk rentang"


def cek_suhu(x):
    if pd.isna(x):
        return None, "suhu setimbang tidak tercatat"
    if x < SUHU_MIN:
        return False, f"suhu setimbang {x:.0f} K, terlalu dingin"
    if x > SUHU_MAX:
        return False, f"suhu setimbang {x:.0f} K, terlalu panas"
    return True, f"suhu setimbang {x:.0f} K, masuk rentang"


def nilai_planet(baris):
    f, teks_f = cek_fluks(baris["pl_insol"])
    s, teks_s = cek_suhu(baris["pl_eqt"])
    hasil = [f, s]
    if False in hasil:
        status = "Tidak layak huni"
    elif None in hasil:
        status = "Data tidak lengkap"
    else:
        status = "Kandidat layak huni"
    return pd.Series({"status": status, "alasan": teks_f + "; " + teks_s})

def ringkas_hasil(df):
    print("Hasil seleksi:")
    print(df["status"].value_counts().to_string())
    kandidat = df[df["status"] == "Kandidat layak huni"]
    per_sistem = (
        df.groupby("hostname")
        .agg(jumlah_planet=("pl_name", "count"))
        .join(kandidat.groupby("hostname").size().rename("jumlah_kandidat"))
        .fillna({"jumlah_kandidat": 0})
        .astype(int)
    )
    pilihan = per_sistem[per_sistem["jumlah_kandidat"] > 0]
    pilihan = pilihan.sort_values(
        ["jumlah_kandidat", "jumlah_planet"], ascending=False
    )
    print("Jumlah sistem dengan minimal satu kandidat:", len(pilihan))
    print("Sistem dengan kandidat terbanyak, untuk dipilih jadi 2 sistem contoh:")
    print(pilihan.head(10).to_string())


def simpan_untuk_peta(df):
    data = df.astype(object).where(df.notna(), None)
    peta = {}
    for host, grup in data.groupby("hostname"):
        peta[host] = grup.to_dict("records")
    with open(FILE_PETA, "w", encoding="utf-8") as f:
        json.dump(peta, f, ensure_ascii=False, indent=1)
    print("Tersimpan:", FILE_BERSIH, "dan", FILE_PETA)


def main():
    mentah = muat_data()
    df = bersihkan(mentah)
    hasil = df.join(df.apply(nilai_planet, axis=1))
    ringkas_hasil(hasil)
    hasil.to_csv(FILE_BERSIH, index=False)
    simpan_untuk_peta(hasil)


main()
