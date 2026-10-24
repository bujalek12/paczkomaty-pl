"""Przygotowanie agregatow do mapy w aplikacji: zgrubienie siatki i wycinek wokol miasta."""

import h3
import numpy as np
import pandas as pd

from paczkomaty.pokrycie import PROMIEN_ZIEMI_M

SUMOWANE = ["ludnosc", "ludnosc_500m", "ludnosc_1km", "inpost", "inpost_w_budowie",
            "allegro_one_box", "orlen_paczka", "dpd", "dhl", "pocztex"]


def do_rozdzielczosci(agregaty: pd.DataFrame, res: int) -> pd.DataFrame:
    """Sumuje szesciokaty res 8 do rodzicow o nizszej rozdzielczosci (res 7 = 7 razy wieksze)."""
    rodzice = agregaty.assign(h3=[h3.cell_to_parent(c, res) for c in agregaty["h3"]])
    wynik = rodzice.groupby("h3", as_index=False)[SUMOWANE].sum()
    return dodaj_udzial(wynik)


def dodaj_udzial(df: pd.DataFrame) -> pd.DataFrame:
    """udzial_500: odsetek mieszkancow szesciokata z paczkomatem w 500 m (0, gdy brak ludnosci)."""
    return df.assign(udzial_500=np.where(df["ludnosc"] > 0, df["ludnosc_500m"] / df["ludnosc"].where(df["ludnosc"] > 0, 1), 0.0))


def w_promieniu(agregaty: pd.DataFrame, lat: float, lon: float, km: float) -> pd.DataFrame:
    """Szesciokaty, ktorych srodek lezy nie dalej niz km od punktu (odleglosc po kuli)."""
    f1, f2 = np.radians(agregaty["lat"].to_numpy()), np.radians(lat)
    dl = np.radians(agregaty["lon"].to_numpy() - lon)
    kat = 2 * np.arcsin(np.sqrt(np.sin((f1 - f2) / 2) ** 2 + np.cos(f1) * np.cos(f2) * np.sin(dl / 2) ** 2))
    return agregaty[kat * PROMIEN_ZIEMI_M <= km * 1000]
