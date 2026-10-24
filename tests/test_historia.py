"""Testy historii sieci: zmiany miedzy zrzutami i agregaty dzienne."""

import pandas as pd
import pytest

from paczkomaty.historia import (
    PodejrzanyZrzut, dopisz, porownaj, sprawdz_kompletnosc, stan_dzienny, zmiany_dzienne,
)


def zrzut(*punkty):
    """punkty: (nazwa, status, wojewodztwo)"""
    return pd.DataFrame({
        "nazwa": [p[0] for p in punkty], "lat": 52.0, "lon": 21.0, "status": [p[1] for p in punkty],
        "wewnatrz": False, "calodobowy": True, "wojewodztwo": [p[2] for p in punkty], "miasto": "Warszawa",
        "allegro": True,
    })


def test_rozpoznaje_nowy_usuniety_i_zmiane_statusu():
    wczoraj = zrzut(("WAW01", "Operating", "mazowieckie"), ("WAW02", "Created", "mazowieckie"),
                    ("KRA01", "Operating", "małopolskie"))
    dzis = zrzut(("WAW01", "Operating", "mazowieckie"), ("WAW02", "Operating", "mazowieckie"),
                 ("GDA01", "Created", "pomorskie"))

    zmiany = porownaj(wczoraj, dzis, "2026-10-25").set_index("nazwa")

    assert zmiany.loc["GDA01", "zmiana"] == "nowy"
    assert pd.isna(zmiany.loc["GDA01", "status_przed"]) and zmiany.loc["GDA01", "status_po"] == "Created"
    assert zmiany.loc["KRA01", "zmiana"] == "usuniety"
    assert zmiany.loc["KRA01", "status_przed"] == "Operating" and pd.isna(zmiany.loc["KRA01", "status_po"])
    assert zmiany.loc["WAW02", "zmiana"] == "status"
    assert (zmiany.loc["WAW02", "status_przed"], zmiany.loc["WAW02", "status_po"]) == ("Created", "Operating")
    assert "WAW01" not in zmiany.index
    assert set(zmiany["data"]) == {"2026-10-25"}


def test_bez_zmian_i_pierwszy_dzien():
    dzis = zrzut(("WAW01", "Operating", "mazowieckie"))

    assert porownaj(dzis, dzis, "2026-10-25").empty
    assert porownaj(None, dzis, "2026-10-25").empty  # pierwszy zrzut: punkt startowy, nie 30 tys. "nowych"


def test_duzy_spadek_liczby_punktow_to_blad():
    sprawdz_kompletnosc(1000, 960)  # normalne wahanie
    with pytest.raises(PodejrzanyZrzut):
        sprawdz_kompletnosc(1000, 900)  # awaria API nie moze wygladac jak zamkniecie 100 paczkomatow
    sprawdz_kompletnosc(None, 5)  # brak poprzedniego zrzutu


def test_ponowne_uruchomienie_tego_samego_dnia_zastepuje_wiersze():
    stare = pd.DataFrame({"data": ["2026-10-24", "2026-10-25"], "liczba": [1, 2]})
    nowe = pd.DataFrame({"data": ["2026-10-25"], "liczba": [3]})

    wynik = dopisz(stare, nowe)

    assert wynik.to_dict("list") == {"data": ["2026-10-24", "2026-10-25"], "liczba": [1, 3]}
    assert dopisz(None, nowe).equals(nowe)


def test_stan_dzienny_liczy_wg_wojewodztwa_i_statusu():
    dzis = zrzut(("A", "Operating", "Mazowieckie"), ("B", "Operating", "mazowieckie"), ("C", "Created", "x"))

    wynik = stan_dzienny(dzis, "2026-10-25")

    assert wynik.to_dict("records") == [
        {"data": "2026-10-25", "wojewodztwo": "mazowieckie", "status": "Operating", "paczkomaty": 2},
        {"data": "2026-10-25", "wojewodztwo": "nieznane", "status": "Created", "paczkomaty": 1},
    ]


def test_zmiany_dzienne_bez_nazw_punktow():
    wczoraj = zrzut(("A", "Created", "pomorskie"))
    dzis = zrzut(("A", "Operating", "pomorskie"), ("B", "Created", "pomorskie"), ("C", "Created", "pomorskie"))

    wynik = zmiany_dzienne(porownaj(wczoraj, dzis, "2026-10-25"))

    assert "nazwa" not in wynik.columns
    assert wynik.to_dict("records") == [
        {"data": "2026-10-25", "wojewodztwo": "pomorskie", "zmiana": "nowy", "liczba": 2},
        {"data": "2026-10-25", "wojewodztwo": "pomorskie", "zmiana": "status", "liczba": 1},
    ]
