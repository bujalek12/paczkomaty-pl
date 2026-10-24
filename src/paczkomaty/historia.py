"""Historia sieci: co zmienilo sie miedzy dwoma zrzutami i agregaty dzienne do publikacji.

Zmiany punkt po punkcie (z nazwa i wspolrzednymi) zostaja w prywatnym repo z danymi;
publicznie idzie tylko stan_dzienny i zmiany_dzienne (liczby na wojewodztwo).
"""

import pandas as pd

from paczkomaty.regiony import normalizuj_wojewodztwo

KOLUMNY_ZMIAN = ["data", "nazwa", "zmiana", "status_przed", "status_po", "lat", "lon", "wojewodztwo", "miasto"]
MIN_UDZIAL = 0.95  # dzis musi byc co najmniej 95% wczorajszych punktow


class PodejrzanyZrzut(Exception):
    """Zrzut wyglada na niepelny (np. API zwrocilo czesc stron)."""


def sprawdz_kompletnosc(poprzedni_n: int | None, biezacy_n: int) -> None:
    if poprzedni_n and biezacy_n < MIN_UDZIAL * poprzedni_n:
        raise PodejrzanyZrzut(f"dzis {biezacy_n} punktow, wczoraj {poprzedni_n}: za duzy spadek, zrzut pominiety")


def porownaj(poprzedni: pd.DataFrame | None, biezacy: pd.DataFrame, data: str) -> pd.DataFrame:
    """Nowe punkty, usuniete punkty i zmiany statusu. Bez poprzedniego zrzutu: brak zmian (punkt startowy)."""
    if poprzedni is None:
        return pd.DataFrame(columns=KOLUMNY_ZMIAN)
    opis = ["lat", "lon", "wojewodztwo", "miasto"]
    razem = poprzedni[["nazwa", "status", *opis]].merge(
        biezacy[["nazwa", "status", *opis]], on="nazwa", how="outer", suffixes=("_przed", "_po"), indicator=True
    )
    razem["zmiana"] = razem["_merge"].map({"right_only": "nowy", "left_only": "usuniety", "both": "status"})
    zmienione = razem[(razem["zmiana"] != "status") | (razem["status_przed"] != razem["status_po"])].copy()
    for k in opis:  # opis punktu z dzisiejszego zrzutu, a dla usunietych z wczorajszego
        zmienione[k] = zmienione[f"{k}_po"].combine_first(zmienione[f"{k}_przed"])
    zmienione["data"] = data
    return zmienione[KOLUMNY_ZMIAN].sort_values(["zmiana", "nazwa"]).reset_index(drop=True)


def dopisz(stare: pd.DataFrame | None, nowe: pd.DataFrame) -> pd.DataFrame:
    """Dokleja wiersze nowego dnia; ponowne uruchomienie tego samego dnia zastepuje jego wiersze."""
    if stare is None:
        return nowe
    zostaja = stare[~stare["data"].isin(nowe["data"].unique())]
    return pd.concat([zostaja, nowe], ignore_index=True).sort_values("data", kind="stable").reset_index(drop=True)


def stan_dzienny(zrzut: pd.DataFrame, data: str) -> pd.DataFrame:
    """Liczba paczkomatow wg wojewodztwa i statusu w danym dniu."""
    wynik = (zrzut.assign(wojewodztwo=zrzut["wojewodztwo"].map(normalizuj_wojewodztwo))
             .groupby(["wojewodztwo", "status"]).size().rename("paczkomaty").reset_index())
    wynik.insert(0, "data", data)
    return wynik


def zmiany_dzienne(zmiany: pd.DataFrame) -> pd.DataFrame:
    """Liczba zmian wg dnia, wojewodztwa i rodzaju (bez nazw i wspolrzednych punktow)."""
    return (zmiany.assign(wojewodztwo=zmiany["wojewodztwo"].map(normalizuj_wojewodztwo))
            .groupby(["data", "wojewodztwo", "zmiana"]).size().rename("liczba").reset_index())
