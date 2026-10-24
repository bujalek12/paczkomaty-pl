"""Testy automatow paczkowych z OpenStreetMap."""

import httpx
import pytest

from paczkomaty.osm import normalizuj_operatora, pobierz_automaty_osm


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
