"""Automaty paczkowe wszystkich operatorow z OpenStreetMap (dane (c) wspoltworcy OSM, licencja ODbL).

OSM jest niekompletny (InPost ma tam ok. 21 tys. z 34 tys. paczkomatow), wiec liczby konkurencji
traktujemy jako dolna granice. InPost bierzemy z jego API, z OSM tylko pozostalych operatorow.
"""

import httpx
import pandas as pd

from paczkomaty.http import pobierz

OVERPASS = "https://overpass-api.de/api/interpreter"
ZAPYTANIE = """
[out:json][timeout:180];
area["ISO3166-1"="PL"][admin_level=2]->.pl;
node["amenity"="parcel_locker"](area.pl);
out tags;
"""
# kolejnosc ma znaczenie: pierwsze dopasowanie wygrywa
OPERATORZY = [
    ("inpost", "InPost"),
    ("allegro", "Allegro One Box"),
    ("orlen", "Orlen Paczka"),
    ("dpd", "DPD"),
    ("dhl", "DHL"),
    ("pocztex", "Pocztex"),
    ("poczta polska", "Pocztex"),
]


def normalizuj_operatora(tagi: dict) -> str:
    """Wspolna nazwa operatora z tagow brand/operator (OSM zapisuje te sama firme na rozne sposoby)."""
    tekst = f"{tagi.get('brand', '')} {tagi.get('operator', '')}".lower()
    return next((nazwa for klucz, nazwa in OPERATORZY if klucz in tekst), "inny")


def pobierz_automaty_osm(klient: httpx.Client | None = None) -> pd.DataFrame:
    """Wszystkie automaty paczkowe w Polsce z OSM: kolumny lat, lon, operator."""
    wlasny = klient is None
    # Overpass odrzuca zapytania bez naglowka User-Agent (blad 406)
    klient = klient or httpx.Client(timeout=240, headers={"User-Agent": "paczkomaty-pl (analiza danych publicznych)"})
    try:
        dane = pobierz(klient, OVERPASS, metoda="POST", dane={"data": ZAPYTANIE}).json()
    finally:
        if wlasny:
            klient.close()
    return pd.DataFrame(
        [{"lat": e["lat"], "lon": e["lon"], "operator": normalizuj_operatora(e.get("tags", {}))}
         for e in dane["elements"] if e.get("type") == "node"],
        columns=["lat", "lon", "operator"],
    )
