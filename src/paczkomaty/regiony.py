"""Wojewodztwa: API InPost zapisuje je roznie ("Wielkopolskie", "malopolskie", "x")."""

import unicodedata

WOJEWODZTWA = [
    "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie", "łódzkie", "małopolskie", "mazowieckie",
    "opolskie", "podkarpackie", "podlaskie", "pomorskie", "śląskie", "świętokrzyskie", "warmińsko-mazurskie",
    "wielkopolskie", "zachodniopomorskie",
]


def _klucz(tekst: str) -> str:
    """Male litery bez polskich znakow (l z kreska nie rozklada sie w NFKD, wiec osobno)."""
    tekst = tekst.strip().lower().replace("ł", "l")
    return "".join(z for z in unicodedata.normalize("NFKD", tekst) if not unicodedata.combining(z))


_PO_KLUCZU = {_klucz(w): w for w in WOJEWODZTWA}


def normalizuj_wojewodztwo(nazwa: str | None) -> str:
    return _PO_KLUCZU.get(_klucz(nazwa), "nieznane") if nazwa else "nieznane"
