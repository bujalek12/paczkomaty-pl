"""Testy przygotowania danych do mapy."""

import h3
import pandas as pd
import pytest

from paczkomaty.widoki import (
    do_rozdzielczosci, klasa_zasiegu, konkurencja_wg_operatora, pokrycie_wg_typu, w_promieniu,
)

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


def test_klasa_zasiegu_wg_wiekszosci_mieszkancow():
    df = agregaty_testowe()
    df.loc[3] = df.loc[0]
    df.loc[3, ["ludnosc", "ludnosc_500m", "ludnosc_1km"]] = [80.0, 10.0, 20.0]

    assert list(klasa_zasiegu(df)) == ["do 500 m", "do 1 km", "do 500 m", "ponad 1 km"]


def test_klasa_zasiegu_bez_mieszkancow():
    df = agregaty_testowe().iloc[:1].assign(ludnosc=0.0, ludnosc_500m=0.0, ludnosc_1km=0.0)

    assert list(klasa_zasiegu(df)) == ["bez mieszkańców"]


def test_pokrycie_wg_typu_zabudowy():
    # gestosc = ludnosc / 0,737 km2: 2000 -> ok. 2700 os./km2 (miasto), 100 -> 136 (wies), 10 -> 14 (rozproszona)
    df = agregaty_testowe().assign(ludnosc=[2000.0, 100.0, 10.0], ludnosc_500m=[1800.0, 20.0, 0.0],
                                   ludnosc_1km=[2000.0, 50.0, 5.0])

    wynik = pokrycie_wg_typu(df).set_index("typ")

    assert list(wynik.index) == ["Miasta", "Małe miasta i osiedla", "Wieś i przedmieścia", "Zabudowa rozproszona"]
    assert wynik.loc["Miasta", "udzial_ludnosci"] == pytest.approx(2000 / 2110)
    assert wynik.loc["Miasta", "w_500m"] == pytest.approx(0.9)
    assert wynik.loc["Wieś i przedmieścia", "w_1km"] == pytest.approx(0.5)
    assert wynik.loc["Małe miasta i osiedla", "udzial_ludnosci"] == 0
    assert wynik.loc["Małe miasta i osiedla", "w_500m"] == 0


def test_konkurencja_wg_operatora():
    df = agregaty_testowe().assign(allegro_one_box=[1, 3, 0], dpd=[0, 0, 2])

    wynik = konkurencja_wg_operatora(df).set_index("operator")

    assert list(wynik.index)[:2] == ["Allegro One Box", "DPD"]
    assert wynik.loc["Allegro One Box", "automaty"] == 4
    assert wynik.loc["Allegro One Box", "bez_inpost"] == 3  # drugi szesciokat nie ma InPost
    assert wynik.loc["DPD", "udzial_bez_inpost"] == 0
    assert wynik.loc["Pocztex", "udzial_bez_inpost"] == 0  # 0 automatow: bez dzielenia przez zero
