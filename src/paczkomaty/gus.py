"""Ludnosc powiatow z Banku Danych Lokalnych GUS (zmienna 72305: ludnosc ogolem, stan na 31 XII).

Sluzy do kalibracji Kontur: w kilku miastach (np. Elblag, Wloclawek, Suwalki) Kontur przesuwa czesc
mieszkancow poza granice miasta. Liczbe mieszkancow powiatu bierzemy z GUS, a Kontur tylko rozklada
ich w obrebie powiatu.
"""

import time
from collections.abc import Callable

import httpx
import pandas as pd

from paczkomaty.http import pobierz

API = "https://bdl.stat.gov.pl/api/v1/data/by-variable/72305"
ROK = 2025
PRZERWA_S = 1.0  # limit anonimowy BDL jest hojny, ale nie ma po co sie spieszyc
# kod wojewodztwa TERYT siedzi na pozycjach 3-4 identyfikatora jednostki BDL (np. 011212001000 -> 12)
WOJEWODZTWA_TERYT = {
    "02": "dolnośląskie", "04": "kujawsko-pomorskie", "06": "lubelskie", "08": "lubuskie", "10": "łódzkie",
    "12": "małopolskie", "14": "mazowieckie", "16": "opolskie", "18": "podkarpackie", "20": "podlaskie",
    "22": "pomorskie", "24": "śląskie", "26": "świętokrzyskie", "28": "warmińsko-mazurskie",
    "30": "wielkopolskie", "32": "zachodniopomorskie",
}


def klucz_powiatu(nazwa: str) -> str:
    """Nazwa z BDL w tej samej postaci co z granic: 'Powiat m. Kraków' -> 'Kraków', 'Powiat bocheński' -> 'powiat bocheński'."""
    reszta = nazwa.removeprefix("Powiat ")
    for miasto in ("m. st. ", "m.st. ", "m. "):
        if reszta.startswith(miasto):
            return reszta.removeprefix(miasto).split(" od ")[0]
    return f"powiat {reszta}"


def pobierz_ludnosc_powiatow(rok: int = ROK, klient: httpx.Client | None = None, na_strone: int = 100,
                             czekaj: Callable[[float], None] = time.sleep) -> pd.DataFrame:
    """Ludnosc wszystkich powiatow w danym roku: wojewodztwo, powiat, ludnosc_gus."""
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=60)
    try:
        wiersze, strona, wszystkich = [], 0, 1
        while strona * na_strone < wszystkich:
            if strona:
                czekaj(PRZERWA_S)
            dane = pobierz(klient, API, params={"format": "json", "unit-level": 5, "year": rok, "lang": "pl",
                                                "page-size": na_strone, "page": strona}, czekaj=czekaj).json()
            wszystkich = dane["totalRecords"]
            for j in dane["results"]:
                if j["values"]:  # jednostki historyczne (np. "do 2002") nie maja danych z biezacego roku
                    wiersze.append({"wojewodztwo": WOJEWODZTWA_TERYT[j["id"][2:4]],
                                    "powiat": klucz_powiatu(j["name"]), "ludnosc_gus": j["values"][0]["val"]})
            strona += 1
        return pd.DataFrame(wiersze)
    finally:
        if wlasny:
            klient.close()
