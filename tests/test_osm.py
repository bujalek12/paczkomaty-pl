"""Testy automatow paczkowych z OpenStreetMap."""

import httpx
import pytest

from paczkomaty.osm import normalizuj_operatora, pobierz_automaty_osm, pobierz_punkty_osm


@pytest.mark.parametrize(("tagi", "operator"), [
    ({"brand": "Paczkomat InPost"}, "InPost"),
    ({"brand": "Appkomat InPost"}, "InPost"),
    ({"brand": "Lodówkomat InPost"}, "InPost"),
    ({"brand": "Allegro One Box"}, "Allegro One Box"),
    ({"operator": "Allegro"}, "Allegro One Box"),
    ({"brand": "Orlen Paczka"}, "Orlen Paczka"),
    ({"operator": "Orlen"}, "Orlen Paczka"),
    ({"brand": "DPD Pickup Station"}, "DPD"),
    ({"operator": "dpd"}, "DPD"),
    ({"brand": "DHL BOX 24/7"}, "DHL"),
    ({"brand": "Pocztex"}, "Pocztex"),
    ({"brand": "Jakis Automat"}, "inny"),
    ({}, "inny"),
])
def test_normalizuje_warianty_marek(tagi, operator):
    assert normalizuj_operatora(tagi) == operator


def test_ramka_z_odpowiedzi_overpass():
    def obsluga(zadanie):
        assert zadanie.method == "POST"
        return httpx.Response(200, json={"elements": [
            {"type": "node", "lat": 52.2, "lon": 21.0, "tags": {"brand": "Orlen Paczka"}},
            {"type": "node", "lat": 50.1, "lon": 19.9, "tags": {"operator": "DPD"}},
        ]})

    df = pobierz_automaty_osm(klient=httpx.Client(transport=httpx.MockTransport(obsluga)))

    assert df.to_dict("records") == [
        {"lat": 52.2, "lon": 21.0, "operator": "Orlen Paczka"},
        {"lat": 50.1, "lon": 19.9, "operator": "DPD"},
    ]


def test_zapytanie_zwraca_wspolrzedne():
    # "out tags" zwraca same tagi, bez lat/lon: mapa bylaby pusta
    from paczkomaty.osm import ZAPYTANIE

    assert "out tags" not in ZAPYTANIE


def test_wezel_bez_wspolrzednych_jest_pomijany():
    def obsluga(zadanie):
        return httpx.Response(200, json={"elements": [
            {"type": "node", "tags": {"brand": "DPD"}},
            {"type": "node", "lat": 50.1, "lon": 19.9, "tags": {"brand": "DHL"}},
        ]})

    df = pobierz_automaty_osm(klient=httpx.Client(transport=httpx.MockTransport(obsluga)))

    assert list(df["operator"]) == ["DHL"]


def test_punkty_otoczenia_z_wezlow_i_obszarow():
    odpowiedz = {"elements": [
        {"type": "node", "lat": 52.1, "lon": 21.0, "tags": {"shop": "convenience", "brand": "Żabka"}},
        {"type": "way", "center": {"lat": 52.2, "lon": 21.1}, "tags": {"shop": "supermarket"}},
        {"type": "node", "lat": 52.3, "lon": 21.2, "tags": {"highway": "bus_stop"}},
        {"type": "way", "center": {"lat": 52.4, "lon": 21.3}, "tags": {"amenity": "fuel"}},
        {"type": "relation", "center": {"lat": 52.5, "lon": 21.4}, "tags": {"amenity": "school"}},
        {"type": "way", "tags": {"amenity": "school"}},  # bez srodka: pomijany
    ]}

    def obsluga(zapytanie):
        assert b"out+tags+center" in zapytanie.content  # obszary (way) potrzebuja srodka
        return httpx.Response(200, json=odpowiedz)

    df = pobierz_punkty_osm(klient=httpx.Client(transport=httpx.MockTransport(obsluga)))

    assert df.to_dict("list") == {
        "lat": [52.1, 52.2, 52.3, 52.4, 52.5], "lon": [21.0, 21.1, 21.2, 21.3, 21.4],
        "rodzaj": ["sklep", "supermarket", "przystanek", "stacja_paliw", "szkola"],
    }
