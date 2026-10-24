"""Testy przygotowania danych do mapy."""

import h3
import pandas as pd
import pytest

from paczkomaty.widoki import do_rozdzielczosci, w_promieniu

RODZIC7 = h3.cell_to_parent("881f1d4815fffff", 7)


def agregaty_testowe():
    dzieci = list(h3.cell_to_children(RODZIC7, 8))[:3]
    srodki = [h3.cell_to_latlng(c) for c in dzieci]
    return pd.DataFrame({
        "h3": dzieci, "ludnosc": [100.0, 50.0, 50.0], "ludnosc_500m": [100.0, 0.0, 25.0], "ludnosc_1km": [100.0, 50.0, 50.0],
        "inpost": [2, 0, 1], "inpost_w_budowie": [0, 1, 0], "allegro_one_box": [1, 0, 0], "orlen_paczka": [0, 0, 0],
        "dpd": [0, 0, 0], "dhl": [0, 0, 0], "pocztex": [0, 0, 0],
        "lat": [s[0] for s in srodki], "lon": [s[1] for s in srodki],
    })


def test_zgrubienie_sumuje_ludnosc_i_automaty():
    wynik = do_rozdzielczosci(agregaty_testowe(), 7)

    assert list(wynik["h3"]) == [RODZIC7]
    w = wynik.iloc[0]
    assert (w["ludnosc"], w["ludnosc_500m"], w["inpost"], w["inpost_w_budowie"]) == (200.0, 125.0, 3, 1)
    assert w["udzial_500"] == pytest.approx(0.625)


def test_wycinek_wokol_punktu():
    df = agregaty_testowe()
    lat, lon = df["lat"].iloc[0], df["lon"].iloc[0]

    assert len(w_promieniu(df, lat, lon, km=5)) == 3
    assert len(w_promieniu(df, lat + 1.0, lon, km=5)) == 0
