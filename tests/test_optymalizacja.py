"""Testy wyboru lokalizacji (zachlanne pokrycie) i miary trafien."""

import numpy as np
import pytest

from paczkomaty.optymalizacja import macierz_zasiegu, trafienia, zachlannie

# punkty na poludniku co ok. 400 m (0,0036 stopnia szerokosci): sasiedzi w 500 m, co drugi juz nie
LAT = 52.0 + 0.0036 * np.arange(5)
LON = np.full(5, 21.0)


def test_macierz_zasiegu_500_m():
    A = macierz_zasiegu(LAT, LON, 500).toarray()

    assert A[2].tolist() == [0, 1, 1, 1, 0]
    assert (A == A.T).all()


def test_zachlannie_wybiera_najwiecej_niepokrytych_i_nie_liczy_dwa_razy():
    A = macierz_zasiegu(LAT, LON, 500)
    wagi = np.array([10.0, 0.0, 0.0, 1.0, 8.0])

    wybrane, zyski = zachlannie(A, wagi, k=3)

    # 1. punkt 0 albo 1 (po 10), 2. punkt 3 albo 4 (9: obejmuje 3 i 4), 3. nic juz nie zostalo
    assert wybrane[0] in (0, 1) and wybrane[1] in (3, 4)
    assert zyski[:2] == pytest.approx([10, 9])
    assert len(wybrane) == 2  # dalsze miejsca nie dalyby nikogo nowego, wiec konczymy


def test_trafienia_odsetek_punktow_blisko_wybranych():
    assert trafienia(LAT[[0, 4]], LON[[0, 4]], LAT[[1]], LON[[1]], 500) == pytest.approx(0.5)


def test_objeci_mieszkancy_liczeni_raz():
    from paczkomaty.optymalizacja import objeci_mieszkancy
    ludnosc = np.array([100.0, 50.0, 0.0, 20.0, 5.0])

    # miejsca w punktach 0 i 1: obejmuja 0, 1, 2 (punkt 1 i 0 tylko raz)
    assert objeci_mieszkancy(LAT, LON, ludnosc, LAT[[0, 1]], LON[[0, 1]], 500) == 150
