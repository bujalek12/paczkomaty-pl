"""Testy agregacji do szesciokatow res 8 (jedyne dane, ktore trafiaja publicznie)."""

import h3
import numpy as np
import pandas as pd
import pytest

from paczkomaty.dane import agreguj_res8, zbuduj_heksagony

RODZIC = "881f1d4815fffff"


def test_odleglosc_tylko_do_dzialajacych_paczkomatow():
    lat, lon = h3.cell_to_latlng(RODZIC)
    paczkomaty = pd.DataFrame({"lat": [lat, lat + 1.0], "lon": [lon, lon], "status": ["Created", "Operating"]})
    res9 = pd.DataFrame({"h3": [RODZIC], "ludnosc": [10.0], "lat": [lat], "lon": [lon]})

    wynik = zbuduj_heksagony(paczkomaty, res9)

    # paczkomat w budowie stoi w tym samym miejscu, ale sie nie liczy: najblizszy dzialajacy jest 1 stopien dalej
    assert wynik["odl_m"].iloc[0] == pytest.approx(111_195, abs=10)


def test_agregacja_sumuje_ludnosc_w_zasiegu_i_liczy_automaty():
    dzieci = list(h3.cell_to_children(RODZIC, 9))
    res9 = pd.DataFrame({"h3": dzieci, "ludnosc": [10.0] * 7, "odl_m": [100.0] * 3 + [700.0] * 2 + [2000.0] * 2})
    lat, lon = h3.cell_to_latlng(RODZIC)
    paczkomaty = pd.DataFrame({"lat": [lat, lat, lat], "lon": [lon, lon, lon], "status": ["Operating", "Operating", "Created"]})
    konkurencja = pd.DataFrame({"lat": [lat, lat], "lon": [lon, lon], "operator": ["Orlen Paczka", "Allegro One Box"]})

    wynik = agreguj_res8(res9, paczkomaty, konkurencja).set_index("h3").loc[RODZIC]

    assert wynik["ludnosc"] == pytest.approx(70.0)
    assert wynik["ludnosc_500m"] == pytest.approx(30.0)
    assert wynik["ludnosc_1km"] == pytest.approx(50.0)
    assert (wynik["inpost"], wynik["inpost_w_budowie"]) == (2, 1)
    assert (wynik["orlen_paczka"], wynik["allegro_one_box"], wynik["dpd"]) == (1, 1, 0)
