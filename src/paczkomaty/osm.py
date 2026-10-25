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
out;
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
         for e in dane["elements"] if e.get("type") == "node" and "lat" in e and "lon" in e],
        columns=["lat", "lon", "operator"],
    )


# Punkty otoczenia do modelu zapotrzebowania: tam, gdzie ludzie robia zakupy, tankuja, czekaja na autobus.
# nwr = wezly, linie i relacje (sklep bywa zaznaczony jako obrys budynku); "out tags center" daje srodek obrysu.
ZAPYTANIE_PUNKTY = """
[out:json][timeout:900];
area["ISO3166-1"="PL"][admin_level=2]->.pl;
(
  nwr["shop"~"^(supermarket|convenience)$"](area.pl);
  node["highway"="bus_stop"](area.pl);
  nwr["amenity"~"^(fuel|school)$"](area.pl);
);
out tags center qt;
"""
RODZAJE = [("shop", "convenience", "sklep"), ("shop", "supermarket", "supermarket"),
           ("highway", "bus_stop", "przystanek"), ("amenity", "fuel", "stacja_paliw"), ("amenity", "school", "szkola")]


def _rodzaj(tagi: dict) -> str | None:
    return next((rodzaj for klucz, wartosc, rodzaj in RODZAJE if tagi.get(klucz) == wartosc), None)


def pobierz_punkty_osm(klient: httpx.Client | None = None) -> pd.DataFrame:
    """Sklepy, supermarkety, przystanki, stacje paliw i szkoly w Polsce: kolumny lat, lon, rodzaj."""
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=960, headers={"User-Agent": "paczkomaty-pl (analiza danych publicznych)"})
    try:
        dane = pobierz(klient, OVERPASS, metoda="POST", dane={"data": ZAPYTANIE_PUNKTY}).json()
    finally:
        if wlasny:
            klient.close()
    wiersze = []
    for e in dane["elements"]:
        polozenie = e if "lat" in e else e.get("center")
        rodzaj = _rodzaj(e.get("tags", {}))
        if polozenie and rodzaj:
            wiersze.append({"lat": polozenie["lat"], "lon": polozenie["lon"], "rodzaj": rodzaj})
    return pd.DataFrame(wiersze, columns=["lat", "lon", "rodzaj"])
