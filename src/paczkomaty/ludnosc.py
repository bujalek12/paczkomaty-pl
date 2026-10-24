"""Ludnosc Polski w szesciokatach H3 (rozdzielczosc 8) ze zbioru Kontur Population (CC BY 4.0).

GeoPackage to zwykla baza SQLite: wystarczy odczytac kolumny h3 i population, bez bibliotek GIS.
"""

import gzip
import sqlite3
from pathlib import Path

import httpx
import pandas as pd

from paczkomaty.http import pobierz

URL = "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/kontur_population_PL_20231101.gpkg.gz"


def pobierz_kontur(cel: Path, klient: httpx.Client | None = None) -> Path:
    """Pobiera spakowany GeoPackage (ok. 22 MB), rozpakowuje; nic nie robi, gdy plik juz jest."""
    if cel.exists():
        return cel
    cel.parent.mkdir(parents=True, exist_ok=True)
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=300, follow_redirects=True)
    try:
        tymczasowy = cel.with_suffix(".pobieranie")
        tymczasowy.write_bytes(gzip.decompress(pobierz(klient, URL).content))
        tymczasowy.replace(cel)  # podmiana dopiero po pelnym pobraniu
        return cel
    finally:
        if wlasny:
            klient.close()


def wczytaj_kontur(sciezka: Path) -> pd.DataFrame:
    """Kolumny: h3 (indeks szesciokata res 8), ludnosc (liczba mieszkancow)."""
    with sqlite3.connect(sciezka) as con:
        # nazwa tabeli z danymi jest zapisana w metadanych GeoPackage
        tabela = con.execute("select table_name from gpkg_contents where data_type = 'features'").fetchone()[0]
        return pd.read_sql(f'select h3, population as ludnosc from "{tabela}"', con)
