"""Testy pobierania paczkomatow z API InPost."""

import httpx

from paczkomaty.inpost import do_ramki, pobierz_paczkomaty


def punkt(nazwa="WAW01M", lat=52.23, lon=21.01, status="Operating", typ="Outdoor", funkcje=("parcel_collect",)):
    return {
        "name": nazwa, "status": status, "location": {"latitude": lat, "longitude": lon},
        "location_type": typ, "location_247": True, "functions": list(funkcje),
        "address_details": {"province": "mazowieckie", "city": "Warszawa"},
    }


def test_przechodzi_przez_wszystkie_strony():
    strony = []

    def obsluga(zadanie):
        nr = int(zadanie.url.params["page"])
        strony.append(nr)
        return httpx.Response(200, json={"items": [punkt(nazwa=f"P{nr}")], "total_pages": 2, "page": nr})

    punkty = pobierz_paczkomaty(klient=httpx.Client(transport=httpx.MockTransport(obsluga)), czekaj=lambda s: None)

    assert strony == [1, 2]
    assert [p["name"] for p in punkty] == ["P1", "P2"]


def test_mapuje_pola():
    df, _ = do_ramki([punkt(typ="Indoor", funkcje=("parcel_collect", "allegro_parcel_collect"))])

    wiersz = df.iloc[0].to_dict()
    assert wiersz == {
        "nazwa": "WAW01M", "lat": 52.23, "lon": 21.01, "status": "Operating", "wewnatrz": True,
        "calodobowy": True, "wojewodztwo": "mazowieckie", "miasto": "Warszawa", "allegro": True,
    }


def test_odrzuca_punkt_bez_wspolrzednych_i_poza_polska():
    bez = punkt(nazwa="BEZ01")
    bez["location"] = None
    df, jakosc = do_ramki([punkt(), bez, punkt(nazwa="BER01", lat=52.52, lon=13.40)])  # Berlin

    assert list(df["nazwa"]) == ["WAW01M"]
    assert jakosc["bez_wspolrzednych"] == 1
    assert jakosc["poza_polska"] == 1


def test_duplikat_nazwy_jeden_wiersz():
    # ten sam punkt potrafi pojawic sie na dwoch stronach, gdy lista zmienia sie w trakcie pobierania
    df, jakosc = do_ramki([punkt(), punkt()])

    assert len(df) == 1
    assert jakosc["duplikaty"] == 1
