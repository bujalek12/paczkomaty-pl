"""Testy cech modelu zapotrzebowania."""

import h3
import numpy as np
import pandas as pd
import pytest

from paczkomaty.cechy import macierz_otoczenia, odleglosc_do_centrum, zbuduj_cechy, zlicz_w_heksagonach

SRODEK = h3.latlng_to_cell(52.0, 21.0, 8)
SASIAD = sorted(h3.grid_ring(SRODEK, 1))[0]
# 2 pierscienie od srodka, po przeciwnej stronie niz SASIAD (3 kroki od niego)
DALSZY = next(c for c in sorted(h3.grid_ring(SRODEK, 2)) if h3.grid_distance(SASIAD, c) == 3)


def test_macierz_otoczenia_sumuje_sasiadow_w_promieniu_k():
    komorki = [SRODEK, SASIAD, DALSZY]
    wartosci = np.array([100.0, 10.0, 1.0])

    assert macierz_otoczenia(komorki, 1) @ wartosci == pytest.approx([110, 110, 1])
    assert macierz_otoczenia(komorki, 2) @ wartosci == pytest.approx([111, 110, 101])


def test_zlicza_punkty_wg_rodzaju():
    lat, lon = h3.cell_to_latlng(SRODEK)
    punkty = pd.DataFrame({"lat": [lat, lat, lat], "lon": [lon, lon, lon], "rodzaj": ["sklep", "sklep", "szkola"]})

    wynik = zlicz_w_heksagonach(punkty, [SRODEK, SASIAD])

    assert wynik.loc[SRODEK].to_dict() == {"sklep": 2, "szkola": 1}
    assert wynik.loc[SASIAD].to_dict() == {"sklep": 0, "szkola": 0}


def test_odleglosc_do_centrum_zero_w_centrum():
    df = pd.DataFrame({"h3": [SRODEK, DALSZY], "gestosc_km2": [5000.0, 100.0]})
    df["lat"], df["lon"] = zip(*(h3.cell_to_latlng(c) for c in df["h3"]))

    km = odleglosc_do_centrum(df, prog=2000)

    assert km[0] == 0
    assert 1.0 < km[1] < 2.5  # dwa pierscienie res 8 to ok. 1,6 km


def test_zbuduj_cechy_bez_kolumn_zaleznych_od_inpost():
    df = pd.DataFrame({"h3": [SRODEK, SASIAD], "ludnosc": [1000.0, 500.0], "gestosc_km2": [2500.0, 700.0],
                       "allegro_one_box": [1, 0], "orlen_paczka": [0, 0], "dpd": [0, 1], "dhl": [0, 0], "pocztex": [0, 0],
                       "inpost": [3, 0], "ludnosc_500m": [1000.0, 500.0]})
    df["lat"], df["lon"] = zip(*(h3.cell_to_latlng(c) for c in df["h3"]))
    lat, lon = h3.cell_to_latlng(SASIAD)
    punkty = pd.DataFrame({"lat": [lat], "lon": [lon], "rodzaj": ["sklep"]})

    cechy = zbuduj_cechy(df, punkty)

    assert not any("inpost" in c or "500m" in c or c in ("lat", "lon") for c in cechy.columns)
    assert cechy.loc[0, "ludnosc_k1"] == 1500
    assert (cechy.loc[0, "sklep"], cechy.loc[0, "sklep_k1"]) == (0, 1)
    assert cechy.loc[1, "konkurencja_k1"] == 2
