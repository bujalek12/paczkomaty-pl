"""Testy pobierania ludnosci powiatow z Banku Danych Lokalnych GUS."""

import httpx
import pytest

from paczkomaty.granice import nazwa_powiatu
from paczkomaty.gus import klucz_powiatu, pobierz_ludnosc_powiatow


@pytest.mark.parametrize("nazwa, oczekiwane", [
    ("Powiat bocheński", "powiat bocheński"),
    ("Powiat m. Kraków", "Kraków"),
    ("Powiat m. st. Warszawa", "Warszawa"),
    ("Powiat m. Wałbrzych od 2013", "Wałbrzych"),
])
def test_klucz_powiatu_zgodny_z_nazwami_granic(nazwa, oczekiwane):
    assert klucz_powiatu(nazwa) == oczekiwane


def test_stara_nazwa_powiatu_w_granicach():
    assert nazwa_powiatu("powiat jeleniogórski") == "powiat karkonoski"  # zmiana nazwy w 2021 r.


def test_przechodzi_przez_strony_i_pomija_jednostki_bez_danych():
    strony = {
        "0": {"totalRecords": 3, "results": [
            {"id": "011212001000", "name": "Powiat bocheński", "values": [{"year": "2025", "val": 106926}]},
            {"id": "010214000000", "name": "Powiat m. Wałbrzych do 2002", "values": []}]},
        "1": {"totalRecords": 3, "results": [
            {"id": "071430865000", "name": "Powiat m. st. Warszawa", "values": [{"year": "2025", "val": 1862345}]}]},
    }

    def odpowiedz(zapytanie):
        assert zapytanie.url.params["year"] == "2025" and zapytanie.url.params["unit-level"] == "5"
        return httpx.Response(200, json=strony[zapytanie.url.params["page"]])

    wynik = pobierz_ludnosc_powiatow(2025, klient=httpx.Client(transport=httpx.MockTransport(odpowiedz)),
                                     na_strone=2, czekaj=lambda s: None)

    assert wynik.to_dict("records") == [
        {"wojewodztwo": "małopolskie", "powiat": "powiat bocheński", "ludnosc_gus": 106926},
        {"wojewodztwo": "mazowieckie", "powiat": "Warszawa", "ludnosc_gus": 1862345},
    ]
