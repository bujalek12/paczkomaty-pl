"""Caly przebieg od danych do aplikacji: zasieg -> hurtownia dbt -> model -> lokalizacje.

Zakada, ze dzisiejszy zrzut sieci juz jest (paczkomaty.zrzut). Zrodla, ktore zmieniaja sie rzadko, leza
w data/zrodla: ludnosc Kontur (stala) i dane OSM (odswiezane co tydzien, zeby nie obciazac Overpass).
Uruchomienie: uv run python -m paczkomaty.pipeline
"""

import time
from pathlib import Path

import pandas as pd

from paczkomaty import hurtownia, lokalizacje, model
from paczkomaty.dane import agreguj_res8, zapisz_agregaty, zbuduj_heksagony
from paczkomaty.ludnosc import pobierz_kontur, wczytaj_kontur
from paczkomaty.osm import pobierz_automaty_osm, pobierz_punkty_osm
from paczkomaty.pokrycie import na_res9

PROJEKT = Path(__file__).resolve().parents[2]
DANE = PROJEKT / "data"
ZRODLA = DANE / "zrodla"
OSM_DNI = 7


def czy_aktualny(plik: Path, dni: float | None) -> bool:
    """Plik istnieje i (jesli podano termin) nie jest starszy niz `dni`."""
    return plik.exists() and (dni is None or time.time() - plik.stat().st_mtime < dni * 86400)


def przygotuj_zrodla() -> None:
    ZRODLA.mkdir(parents=True, exist_ok=True)
    ludnosc = ZRODLA / "ludnosc_res8.parquet"
    if not czy_aktualny(ludnosc, None):
        wczytaj_kontur(pobierz_kontur(DANE / "surowe" / "kontur_population_PL_20231101.gpkg")).to_parquet(ludnosc)
    if not czy_aktualny(ZRODLA / "osm_automaty.parquet", OSM_DNI):
        pobierz_automaty_osm().to_parquet(ZRODLA / "osm_automaty.parquet", index=False)
    if not czy_aktualny(ZRODLA / "osm_punkty.parquet", OSM_DNI):
        pobierz_punkty_osm().to_parquet(ZRODLA / "osm_punkty.parquet", index=False)


def przelicz_zasieg() -> Path:
    """Odleglosc mieszkancow do paczkomatow z najnowszego zrzutu -> agregaty/heksagony_res8.parquet."""
    paczkomaty = pd.read_parquet(sorted((DANE / "zrzuty").glob("inpost_????-??-??.parquet"))[-1])
    ludnosc = pd.read_parquet(ZRODLA / "ludnosc_res8.parquet")
    konkurencja = pd.read_parquet(ZRODLA / "osm_automaty.parquet")
    res9 = zbuduj_heksagony(paczkomaty, na_res9(ludnosc))
    return zapisz_agregaty(agreguj_res8(res9, paczkomaty, konkurencja), DANE / "agregaty")


def main() -> None:
    przygotuj_zrodla()
    print(f"zasieg: {przelicz_zasieg().relative_to(PROJEKT)}")
    hurtownia.main()
    model.main()
    lokalizacje.main()


if __name__ == "__main__":
    main()
