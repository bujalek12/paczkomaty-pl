"""Zapytania HTTP z ponawianiem: uzywaja ich klienci API InPost, Overpass i pobieranie Kontur."""

import time
from collections.abc import Callable

import httpx

PROBY = 4


class BladPobierania(Exception):
    """Serwer nie zwrocil danych mimo ponowien albo odrzucil zapytanie."""


def pobierz(
    klient: httpx.Client,
    url: str,
    params: dict | None = None,
    czekaj: Callable[[float], None] = time.sleep,
    metoda: str = "GET",
    dane: dict | None = None,
) -> httpx.Response:
    """Zapytanie z ponawianiem bledow sieci i serwera: 4 proby, przerwy 1 s, 2 s, 4 s.

    Bledy 4xx (poza 429 "za duzo zapytan") nie sa ponawiane: zle zapytanie nie naprawi sie samo.
    """
    for proba in range(PROBY):
        try:
            odp = klient.request(metoda, url, params=params, data=dane)
        except httpx.TransportError as e:
            blad = f"blad polaczenia: {e}"
        else:
            if odp.is_success:
                return odp
            if odp.is_client_error and odp.status_code != 429:
                raise BladPobierania(f"{url}: HTTP {odp.status_code}")
            blad = f"HTTP {odp.status_code}"
        if proba < PROBY - 1:
            czekaj(2**proba)
    raise BladPobierania(f"{url}: {blad} (po {PROBY} probach)")
