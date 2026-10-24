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
MAX_PIERSCIEN = 3  # komorki przygraniczne: szukamy regionu u sasiadow do 3 pierscieni H3 (ok. 2 km przy res 8)


def pobierz_granice(katalog: Path, klient: httpx.Client | None = None) -> tuple[Path, Path]:
    """Pobiera oba pliki GeoJSON (tylko gdy ich brak). Zwraca (powiaty, wojewodztwa)."""
    katalog.mkdir(parents=True, exist_ok=True)
    pliki = (katalog / "powiaty.geojson", katalog / "wojewodztwa.geojson")
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=120, follow_redirects=True)
    try:
        for url, plik in zip((URL_POWIATY, URL_WOJEWODZTWA), pliki):
            if not plik.exists():
                plik.write_bytes(pobierz(klient, url).content)
    finally:
        if wlasny:
            klient.close()
    return pliki


def nazwa_powiatu(nazwa: str) -> str:
    """'powiat Bytom' -> 'Bytom' (miasto na prawach powiatu); 'powiat oleski' zostaje bez zmian."""
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
