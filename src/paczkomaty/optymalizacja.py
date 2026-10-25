"""Wybor nowych lokalizacji paczkomatow: zachlanne maksymalne pokrycie.

Problem pokrycia (max coverage) jest NP-trudny, ale algorytm zachlanny ma gwarancje: daje co najmniej
(1 - 1/e), czyli ok. 63% najlepszego mozliwego wyniku, a w praktyce zwykle duzo wiecej.
"""

import numpy as np
from scipy import sparse
from sklearn.neighbors import BallTree

from paczkomaty.pokrycie import PROMIEN_ZIEMI_M, odleglosc_do_najblizszego


def macierz_zasiegu(lat: np.ndarray, lon: np.ndarray, promien_m: float) -> sparse.csr_matrix:
    """A[i, j] = 1, gdy punkt j lezy nie dalej niz promien_m od punktu i (macierz symetryczna)."""
    punkty = np.radians(np.column_stack([lat, lon]))
    sasiedzi = BallTree(punkty, metric="haversine").query_radius(punkty, r=promien_m / PROMIEN_ZIEMI_M)
    wiersze = np.repeat(np.arange(len(sasiedzi)), [len(s) for s in sasiedzi])
    kolumny = np.concatenate(sasiedzi)
    return sparse.csr_matrix((np.ones(len(kolumny)), (wiersze, kolumny)), shape=(len(lat), len(lat)))


def zachlannie(A: sparse.csr_matrix, wagi: np.ndarray, k: int) -> tuple[list[int], list[float]]:
    """Kolejno wybiera miejsce, ktore obejmie najwieksza wage jeszcze nieobjetych punktow.

    Po kazdym wyborze zeruje wagi objetych punktow i przelicza zysk tylko kandydatom w ich zasiegu
    (reszty wybor nie zmienia), dzieki czemu 2000 krokow na milionie punktow trwa sekundy.
    """
    wagi = wagi.astype(float).copy()
    zyski = A @ wagi
    wybrane, zysk_kolejnych = [], []
    for _ in range(k):
        c = int(np.argmax(zyski))
        if zyski[c] <= 0:
            break
        wybrane.append(c)
        zysk_kolejnych.append(float(zyski[c]))
        objete = A.indices[A.indptr[c]:A.indptr[c + 1]]
        wagi[objete] = 0
        dotkniete = np.unique(A[objete].indices)  # kandydaci, ktorzy tez widzieli te punkty
        zyski[dotkniete] = A[dotkniete] @ wagi
    return wybrane, zysk_kolejnych


def trafienia(cel_lat, cel_lon, wybrane_lat, wybrane_lon, promien_m: float = 500) -> float:
    """Jaki odsetek punktow (np. paczkomatow w budowie) lezy w promieniu od ktoregos z wybranych miejsc."""
    odleglosci = odleglosc_do_najblizszego(np.asarray(cel_lat), np.asarray(cel_lon),
                                          np.asarray(wybrane_lat), np.asarray(wybrane_lon))
    return float((odleglosci <= promien_m).mean())
