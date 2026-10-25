"""Cechy modelu zapotrzebowania na paczkomaty (sześciokąt H3 res 8).

Zasada: zadna cecha nie moze zalezec od paczkomatow InPost (np. ludnosc_500m), inaczej model "podgladalby"
odpowiedz. Bez wspolrzednych: model ma uczyc sie zaleznosci (ludzie, sklepy, przystanki), a nie regionow.
"""

import h3
import numpy as np
import pandas as pd
from scipy import sparse

from paczkomaty.pokrycie import odleglosc_do_najblizszego

OPERATORZY_KONKURENCJI = ["allegro_one_box", "orlen_paczka", "dpd", "dhl", "pocztex"]


def macierz_otoczenia(komorki: list[str], k: int) -> sparse.csr_matrix:
    """Macierz A (n x n): A @ wartosci = suma wartosci w promieniu k pierscieni H3 (wlacznie z sama komorka).

    Uwzglednia tylko komorki z listy (pozostale traktujemy jak zera). Budowa raz, potem kazda cecha
    to jedno mnozenie macierzy zamiast petli po wszystkich szesciokatach.
    """
    pozycja = {c: i for i, c in enumerate(komorki)}
    wiersze, kolumny = [], []
    for i, c in enumerate(komorki):
        for s in h3.grid_disk(c, k):
            j = pozycja.get(s)
            if j is not None:
                wiersze.append(i)
                kolumny.append(j)
    return sparse.csr_matrix((np.ones(len(wiersze)), (wiersze, kolumny)), shape=(len(komorki), len(komorki)))


def zlicz_w_heksagonach(punkty: pd.DataFrame, komorki: list[str], res: int = 8) -> pd.DataFrame:
    """Liczba punktow kazdego rodzaju w kazdej komorce z listy (wiersze w kolejnosci listy)."""
    komorka = [h3.latlng_to_cell(la, lo, res) for la, lo in zip(punkty["lat"], punkty["lon"])]
    tabela = pd.crosstab(pd.Series(komorka, name="h3"), punkty["rodzaj"].to_numpy())
    tabela.columns.name = None
    return tabela.reindex(komorki, fill_value=0)


def odleglosc_do_centrum(heksagony: pd.DataFrame, prog: float = 2000) -> np.ndarray:
    """Km do najblizszego szesciokata o gestosci powyzej progu (zabudowa miejska); 0 w samym centrum."""
    centra = heksagony[heksagony["gestosc_km2"] > prog]
    metry = odleglosc_do_najblizszego(heksagony["lat"].to_numpy(), heksagony["lon"].to_numpy(),
                                      centra["lat"].to_numpy(), centra["lon"].to_numpy())
    return metry / 1000


def zbuduj_cechy(heksagony: pd.DataFrame, punkty: pd.DataFrame) -> pd.DataFrame:
    """Cechy dla kazdego wiersza `heksagony` (ta sama kolejnosc i indeks)."""
    komorki = heksagony["h3"].tolist()
    a1, a3 = macierz_otoczenia(komorki, 1), macierz_otoczenia(komorki, 3)
    ludnosc = heksagony["ludnosc"].to_numpy()
    konkurencja = heksagony[OPERATORZY_KONKURENCJI].sum(axis=1).to_numpy()
    cechy = pd.DataFrame({
        "ludnosc": ludnosc,
        "ludnosc_k1": a1 @ ludnosc,
        "ludnosc_k3": a3 @ ludnosc,
        "odl_centrum_km": odleglosc_do_centrum(heksagony),
        "konkurencja": konkurencja,
        "konkurencja_k1": a1 @ konkurencja,
    }, index=heksagony.index)
    zliczone = zlicz_w_heksagonach(punkty, komorki)
    for rodzaj in zliczone.columns:
        wartosci = zliczone[rodzaj].to_numpy()
        cechy[rodzaj] = wartosci
        cechy[f"{rodzaj}_k1"] = a1 @ wartosci
    return cechy
