"""Ilu mieszkancow ma paczkomat w zasiegu: odleglosci i pokrycie ludnosci.

Kontur podaje ludnosc w szesciokatach res 8 (bok ok. 460 m, srodki sasiadow ok. 800 m od siebie).
Przy promieniu 500 m to za grubo, wiec ludnosc rozkladamy rowno na 7 dzieci res 9 (bok ok. 175 m)
i liczymy odleglosc od srodka kazdego z nich. Zalozenie rownomiernego rozkladu jest uproszczeniem.
"""

import h3
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

PROMIEN_ZIEMI_M = 6_371_008.8


def na_res9(df: pd.DataFrame) -> pd.DataFrame:
    """Kazdy szesciokat res 8 -> 7 dzieci res 9 z 1/7 ludnosci i wspolrzednymi srodka."""
    wiersze = []
    for rodzic, ludnosc in zip(df["h3"], df["ludnosc"]):
        dzieci = h3.cell_to_children(rodzic, 9)
        for dziecko in dzieci:
            lat, lon = h3.cell_to_latlng(dziecko)
            wiersze.append((dziecko, ludnosc / len(dzieci), lat, lon))
    return pd.DataFrame(wiersze, columns=["h3", "ludnosc", "lat", "lon"])


def odleglosc_do_najblizszego(lat: np.ndarray, lon: np.ndarray, cel_lat: np.ndarray, cel_lon: np.ndarray) -> np.ndarray:
    """Odleglosc w metrach (po kuli) od kazdego punktu do najblizszego celu; brak celow -> inf.

    BallTree z metryka haversine szuka najblizszego sasiada w czasie logarytmicznym, wiec dla
    kilkuset tysiecy szesciokatow i 34 tys. paczkomatow trwa to sekundy, a nie godziny.
    """
    if len(cel_lat) == 0:
        return np.full(len(lat), np.inf)
    drzewo = BallTree(np.radians(np.column_stack([cel_lat, cel_lon])), metric="haversine")
    odl, _ = drzewo.query(np.radians(np.column_stack([lat, lon])), k=1)
    return odl[:, 0] * PROMIEN_ZIEMI_M


def procent_w_zasiegu(ludnosc: np.ndarray, odleglosc: np.ndarray, prog_m: float) -> float:
    """Udzial ludnosci, ktora ma paczkomat nie dalej niz prog_m (0, gdy ludnosc sumuje sie do 0)."""
    suma = float(np.sum(ludnosc))
    return float(np.sum(ludnosc[odleglosc <= prog_m]) / suma) if suma > 0 else 0.0
