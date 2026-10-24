"""Budowa hurtowni: regiony szesciokatow + ludnosc GUS -> dbt build (DuckDB) -> eksport tabel dla aplikacji i Power BI.

Uruchomienie: uv run python -m paczkomaty.hurtownia
Wymaga data/agregaty/heksagony_res8.parquet (notebook 01) i stan_dzienny.parquet (paczkomaty.zrzut).
"""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from paczkomaty.eksport import eksportuj
from paczkomaty.granice import pobierz_granice, przypisz_regiony
from paczkomaty.gus import ROK, pobierz_ludnosc_powiatow

PROJEKT = Path(__file__).resolve().parents[2]
DANE = PROJEKT / "data"


def zbuduj_regiony(dane: Path = DANE) -> Path:
    """Powiat i wojewodztwo dla kazdego szesciokata z agregatow -> agregaty/regiony_heksagonow.parquet."""
    powiaty, wojewodztwa = pobierz_granice(dane / "granice")
    komorki = pd.read_parquet(dane / "agregaty" / "heksagony_res8.parquet", columns=["h3"])["h3"].tolist()
    regiony = przypisz_regiony(komorki, json.loads(powiaty.read_text()), json.loads(wojewodztwa.read_text()))
    plik = dane / "agregaty" / "regiony_heksagonow.parquet"
    regiony.to_parquet(plik, index=False)
    return plik


def zbuduj_ludnosc_gus(dane: Path = DANE, rok: int = ROK) -> Path:
    """Ludnosc powiatow z GUS (pobierana tylko, gdy pliku brak) -> agregaty/ludnosc_gus_powiaty.parquet."""
    plik = dane / "agregaty" / "ludnosc_gus_powiaty.parquet"
    if not plik.exists():
        pobierz_ludnosc_powiatow(rok).to_parquet(plik, index=False)
    return plik


def main() -> None:
    for wymagany in ["heksagony_res8", "stan_dzienny"]:
        if not (DANE / "agregaty" / f"{wymagany}.parquet").exists():
            sys.exit(f"Brak data/agregaty/{wymagany}.parquet: najpierw notebook 01 albo paczkomaty.zrzut")
    print(f"regiony: {zbuduj_regiony().relative_to(PROJEKT)}")
    print(f"ludnosc GUS: {zbuduj_ludnosc_gus().relative_to(PROJEKT)}")
    subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd=PROJEKT / "dbt", check=True)
    for plik in eksportuj():
        print(f"{plik.relative_to(PROJEKT)}  {plik.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
