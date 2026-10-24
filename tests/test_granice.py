"""Testy przypisania szesciokatow do powiatow i wojewodztw (sztuczne kwadraty zamiast prawdziwych granic)."""

import h3
import httpx

from paczkomaty.granice import nazwa_powiatu, pobierz_granice, przypisz_regiony


def kwadrat(lon0, lat0, lon1, lat1, **wlasciwosci):
    pierscien = [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]
    return {"type": "Feature", "properties": wlasciwosci, "geometry": {"type": "Polygon", "coordinates": [pierscien]}}


def kolekcja(*cechy):
    return {"type": "FeatureCollection", "features": list(cechy)}


# dwa powiaty obok siebie (granica na 21,0) i dwa wojewodztwa z ta sama granica
POWIATY = kolekcja(kwadrat(20.9, 52.0, 21.0, 52.1, id=1, nazwa="powiat zachodni"),
                   kwadrat(21.0, 52.0, 21.1, 52.1, id=2, nazwa="powiat Miasto"))
WOJEWODZTWA = kolekcja(kwadrat(20.8, 51.9, 21.0, 52.2, id=1, nazwa="mazowieckie"),
                       kwadrat(21.0, 51.9, 21.2, 52.2, id=2, nazwa="lubelskie"))


def test_nazwa_powiatu():
    assert nazwa_powiatu("powiat Bytom") == "Bytom"  # miasto na prawach powiatu
    assert nazwa_powiatu("powiat oleski") == "powiat oleski"


def test_komorka_dostaje_powiat_i_wojewodztwo_swojego_powiatu():
    zachod, wschod = h3.latlng_to_cell(52.05, 20.95, 8), h3.latlng_to_cell(52.05, 21.05, 8)

    wynik = przypisz_regiony([zachod, wschod], POWIATY, WOJEWODZTWA).set_index("h3")

    assert (wynik.loc[zachod, "powiat_id"], wynik.loc[zachod, "powiat"], wynik.loc[zachod, "wojewodztwo"]) == (
        1, "powiat zachodni", "mazowieckie")
    assert (wynik.loc[wschod, "powiat"], wynik.loc[wschod, "wojewodztwo"]) == ("Miasto", "lubelskie")


def test_komorka_tuz_za_granica_od_najblizszego_sasiada():
    za_granica = h3.latlng_to_cell(52.104, 20.95, 8)  # srodek kilkaset metrow na polnoc od kwadratu
    assert not any(za_granica in h3.geo_to_cells(f["geometry"], 8) for f in POWIATY["features"])

    wynik = przypisz_regiony([za_granica], POWIATY, WOJEWODZTWA)

    assert wynik["powiat_id"].tolist() == [1]


def test_daleko_od_granic_bez_regionu():
    daleko = h3.latlng_to_cell(54.0, 18.0, 8)

    wynik = przypisz_regiony([daleko], POWIATY, WOJEWODZTWA)

    assert wynik["powiat_id"].isna().all() and wynik["wojewodztwo"].isna().all()


def test_nie_pobiera_drugi_raz(tmp_path):
    zapytania = []
    klient = httpx.Client(transport=httpx.MockTransport(lambda r: zapytania.append(r) or httpx.Response(200, text="{}")))

    pobierz_granice(tmp_path, klient=klient)
    pobierz_granice(tmp_path, klient=klient)

    assert len(zapytania) == 2  # dwa pliki, tylko za pierwszym razem
