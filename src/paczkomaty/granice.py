"""Granice powiatow i wojewodztw oraz przypisanie do nich szesciokatow H3.

Zrodlo: github.com/ppatrzyk/polska-geojson (MIT), przekonwertowane z PRG GUGiK; wersja "medium".
Adres przypiety do commita, zeby granice nie zmienily sie po cichu miedzy uruchomieniami.
"""

from collections import Counter
from pathlib import Path

import h3
import httpx
import pandas as pd

from paczkomaty.http import pobierz

_BAZA = "https://raw.githubusercontent.com/ppatrzyk/polska-geojson/74a22f97cf822aa1cb49802c1700ccb8b6340eca"
URL_POWIATY = f"{_BAZA}/powiaty/powiaty-medium.geojson"
URL_WOJEWODZTWA = f"{_BAZA}/wojewodztwa/wojewodztwa-medium.geojson"
URL_POWIATY_MAPA = f"{_BAZA}/powiaty/powiaty-min.geojson"  # mocno uproszczone (0,4 MB), tylko do rysowania
ZMIANY_NAZW = {"powiat jeleniogórski": "powiat karkonoski"}  # granice sprzed zmiany nazwy w 2021 r.
MAX_PIERSCIEN = 3  # komorki przygraniczne: szukamy regionu u sasiadow do 3 pierscieni H3 (ok. 2 km przy res 8)


def pobierz_granice(katalog: Path, klient: httpx.Client | None = None) -> tuple[Path, Path]:
    """Pobiera pliki GeoJSON (tylko gdy ich brak). Zwraca (powiaty, wojewodztwa); obok lezy powiaty_mapa.geojson."""
    katalog.mkdir(parents=True, exist_ok=True)
    pliki = {URL_POWIATY: katalog / "powiaty.geojson", URL_WOJEWODZTWA: katalog / "wojewodztwa.geojson",
             URL_POWIATY_MAPA: katalog / "powiaty_mapa.geojson"}
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=120, follow_redirects=True)
    try:
        for url, plik in pliki.items():
            if not plik.exists():
                plik.write_bytes(pobierz(klient, url).content)
    finally:
        if wlasny:
            klient.close()
    return pliki[URL_POWIATY], pliki[URL_WOJEWODZTWA]


def nazwa_powiatu(nazwa: str) -> str:
    """'powiat Bytom' -> 'Bytom' (miasto na prawach powiatu); 'powiat oleski' zostaje bez zmian."""
    nazwa = ZMIANY_NAZW.get(nazwa, nazwa)
    reszta = nazwa.removeprefix("powiat ")
    return reszta if reszta[:1].isupper() else nazwa


def _komorki(geojson: dict, res: int) -> dict[str, int]:
    """Komorka H3 -> id obszaru (komorki, ktorych srodek lezy w wielokacie)."""
    return {c: f["properties"]["id"] for f in geojson["features"] for c in h3.geo_to_cells(f["geometry"], res)}


def _od_sasiadow(komorka: str, przypisane: dict[str, int]) -> int | None:
    for k in range(1, MAX_PIERSCIEN + 1):
        sasiedzi = [przypisane[s] for s in h3.grid_ring(komorka, k) if s in przypisane]
        if sasiedzi:
            return Counter(sasiedzi).most_common(1)[0][0]
    return None


def przypisz_regiony(komorki: list[str], powiaty_geo: dict, wojewodztwa_geo: dict, res: int = 8) -> pd.DataFrame:
    """Powiat i wojewodztwo dla kazdej komorki. Wojewodztwo bierzemy z powiatu, zeby hierarchia byla spojna."""
    w_powiecie = _komorki(powiaty_geo, res)
    w_wojewodztwie = _komorki(wojewodztwa_geo, res)
    nazwy_pow = {f["properties"]["id"]: nazwa_powiatu(f["properties"]["nazwa"]) for f in powiaty_geo["features"]}
    nazwy_woj = {f["properties"]["id"]: f["properties"]["nazwa"] for f in wojewodztwa_geo["features"]}

    glosy: dict[int, Counter] = {}
    for c, p in w_powiecie.items():
        if c in w_wojewodztwie:
            glosy.setdefault(p, Counter())[w_wojewodztwie[c]] += 1
    woj_powiatu = {p: nazwy_woj[g.most_common(1)[0][0]] for p, g in glosy.items()}

    ids = [w_powiecie[c] if c in w_powiecie else _od_sasiadow(c, w_powiecie) for c in komorki]
    return pd.DataFrame({
        "h3": komorki,
        "powiat_id": pd.array(ids, dtype="Int64"),
        "powiat": [nazwy_pow.get(i) for i in ids],
        "wojewodztwo": [woj_powiatu.get(i) for i in ids],
    })


def sasiedzi_powiatow(regiony: pd.DataFrame) -> pd.DataFrame:
    """Pary sasiadujacych powiatow (w obie strony): komorki H3 stykajace sie przez granice powiatu."""
    powiat = dict(zip(regiony["h3"], regiony["powiat_id"]))
    pary = {
        (p, powiat[s])
        for c, p in powiat.items() if pd.notna(p)
        for s in h3.grid_ring(c, 1)
        if s in powiat and pd.notna(powiat[s]) and powiat[s] != p
    }
    return pd.DataFrame(sorted(pary), columns=["powiat_id", "sasiad_id"]).astype("Int64")
