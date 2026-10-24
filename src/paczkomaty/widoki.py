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


POWIERZCHNIA_RES8_KM2 = 0.737
# Typ zabudowy wg gestosci zaludnienia szesciokata (os./km2): (nazwa, od, do]
TYPY_ZABUDOWY = [("Miasta", 2000, np.inf), ("Małe miasta i osiedla", 500, 2000),
                 ("Wieś i przedmieścia", 50, 500), ("Zabudowa rozproszona", 0, 50)]
OPERATORZY = {"allegro_one_box": "Allegro One Box", "orlen_paczka": "Orlen Paczka", "dpd": "DPD",
              "dhl": "DHL", "pocztex": "Pocztex"}


def klasa_zasiegu(df: pd.DataFrame) -> pd.Series:
    """Jak daleko do paczkomatu ma wiekszosc (co najmniej polowa) mieszkancow szesciokata."""
    lud = df["ludnosc"].where(df["ludnosc"] > 0)
    klasa = np.select(
        [lud.isna(), df["ludnosc_500m"] / lud >= 0.5, df["ludnosc_1km"] / lud >= 0.5],
        ["bez mieszkańców", "do 500 m", "do 1 km"], default="ponad 1 km",
    )
    return pd.Series(klasa, index=df.index)


def _udzial(licznik: float, mianownik: float) -> float:
    return licznik / mianownik if mianownik > 0 else 0.0


def pokrycie_wg_typu(agregaty: pd.DataFrame) -> pd.DataFrame:
    """Udzial ludnosci i zasieg 500 m / 1 km w kazdym typie zabudowy (wiersze w stalej kolejnosci)."""
    gestosc = agregaty["ludnosc"] / POWIERZCHNIA_RES8_KM2
    razem = agregaty["ludnosc"].sum()
    wiersze = []
    for typ, od, do in TYPY_ZABUDOWY:
        czesc = agregaty[(gestosc > od) & (gestosc <= do)]
        lud = czesc["ludnosc"].sum()
        wiersze.append({"typ": typ, "udzial_ludnosci": _udzial(lud, razem),
                        "w_500m": _udzial(czesc["ludnosc_500m"].sum(), lud),
                        "w_1km": _udzial(czesc["ludnosc_1km"].sum(), lud)})
    return pd.DataFrame(wiersze)


def konkurencja_wg_operatora(agregaty: pd.DataFrame) -> pd.DataFrame:
    """Automaty innych operatorow: ile ich jest i ile stoi w szesciokatach bez paczkomatu InPost."""
    bez = agregaty["inpost"] == 0
    wynik = pd.DataFrame({
        "operator": list(OPERATORZY.values()),
        "automaty": [int(agregaty[k].sum()) for k in OPERATORZY],
        "bez_inpost": [int(agregaty.loc[bez, k].sum()) for k in OPERATORZY],
    })
    wynik["udzial_bez_inpost"] = [_udzial(b, a) for b, a in zip(wynik["bez_inpost"], wynik["automaty"])]
    return wynik.sort_values("automaty", ascending=False, kind="stable").reset_index(drop=True)
