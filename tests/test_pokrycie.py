"""Testy liczenia pokrycia ludnosci paczkomatami."""

import numpy as np
import pandas as pd
import pytest

from paczkomaty.pokrycie import na_res9, odleglosc_do_najblizszego, procent_w_zasiegu


def test_na_res9_zachowuje_sume_ludnosci():
    df = pd.DataFrame({"h3": ["881f1d4815fffff", "881f1d4817fffff"], "ludnosc": [70.0, 7.0]})

    wynik = na_res9(df)

    assert len(wynik) == 14  # kazdy szesciokat res 8 ma 7 dzieci res 9
    assert wynik["ludnosc"].sum() == pytest.approx(77.0)
    assert set(wynik.columns) == {"h3", "ludnosc", "lat", "lon"}


def test_odleglosc_jednego_stopnia_szerokosci():
    # 1 stopien szerokosci geograficznej = ok. 111 195 m (kula o promieniu 6 371 008,8 m)
    odl = odleglosc_do_najblizszego(np.array([52.0]), np.array([19.0]), np.array([53.0]), np.array([19.0]))

    assert odl[0] == pytest.approx(111_195, abs=10)


def test_odleglosc_do_najblizszego_z_wielu():
    odl = odleglosc_do_najblizszego(np.array([52.0]), np.array([19.0]), np.array([53.0, 52.001]), np.array([19.0, 19.0]))

    assert odl[0] == pytest.approx(111.2, abs=1)


def test_procent_w_zasiegu():
    # 100 osob blisko (200 m), 300 osob daleko (900 m): przy progu 500 m pokrycie 25%
    assert procent_w_zasiegu(np.array([100.0, 300.0]), np.array([200.0, 900.0]), 500) == pytest.approx(0.25)


def test_zero_ludnosci_i_brak_paczkomatow():
    assert procent_w_zasiegu(np.array([0.0, 0.0]), np.array([100.0, 100.0]), 500) == 0.0
    odl = odleglosc_do_najblizszego(np.array([52.0]), np.array([19.0]), np.array([]), np.array([]))
    assert np.isinf(odl[0])
