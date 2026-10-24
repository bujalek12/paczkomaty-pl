"""Skladanie danych: odleglosci do paczkomatow (res 9) i agregaty na szesciokatach res 8.

Agregaty to jedyne dane, ktore trafiaja publicznie (aplikacja, wydanie). Nie ma w nich
pojedynczych punktow z API InPost, tylko liczby na szesciokat.
"""

from pathlib import Path

import h3
import pandas as pd

from paczkomaty.pokrycie import odleglosc_do_najblizszego

KOLUMNY_OPERATOROW = {
    "Allegro One Box": "allegro_one_box",
    "Orlen Paczka": "orlen_paczka",
    "DPD": "dpd",
    "DHL": "dhl",
    "Pocztex": "pocztex",
}


def zbuduj_heksagony(paczkomaty: pd.DataFrame, ludnosc_res9: pd.DataFrame) -> pd.DataFrame:
    """Do szesciokatow res 9 dodaje odl_m: odleglosc do najblizszego DZIALAJACEGO paczkomatu InPost."""
    dzialajace = paczkomaty[paczkomaty["status"] == "Operating"]
    wynik = ludnosc_res9.copy()
    wynik["odl_m"] = odleglosc_do_najblizszego(
        wynik["lat"].to_numpy(), wynik["lon"].to_numpy(), dzialajace["lat"].to_numpy(), dzialajace["lon"].to_numpy()
    )
    return wynik


def _res8(df: pd.DataFrame) -> pd.Series:
    return pd.Series([h3.latlng_to_cell(a, b, 8) for a, b in zip(df["lat"], df["lon"])], index=df.index)


def agreguj_res8(heksagony_res9: pd.DataFrame, paczkomaty: pd.DataFrame, konkurencja: pd.DataFrame) -> pd.DataFrame:
    """Jeden wiersz na szesciokat res 8: ludnosc, ludnosc w zasiegu 500 m / 1 km, liczby automatow."""
    res9 = heksagony_res9.assign(rodzic=[h3.cell_to_parent(c, 8) for c in heksagony_res9["h3"]])
    ludnosc = res9.groupby("rodzic").agg(
        ludnosc=("ludnosc", "sum"),
        ludnosc_500m=("ludnosc", lambda s: s[res9.loc[s.index, "odl_m"] <= 500].sum()),
        ludnosc_1km=("ludnosc", lambda s: s[res9.loc[s.index, "odl_m"] <= 1000].sum()),
    )

    p = paczkomaty.assign(h3=_res8(paczkomaty))
    inpost = pd.DataFrame({
        "inpost": p[p["status"] == "Operating"].groupby("h3").size(),
        "inpost_w_budowie": p[p["status"] == "Created"].groupby("h3").size(),
    })
    k = konkurencja.assign(h3=_res8(konkurencja))
    konk = k[k["operator"].isin(KOLUMNY_OPERATOROW)].pivot_table(index="h3", columns="operator", aggfunc="size")
    konk = konk.rename(columns=KOLUMNY_OPERATOROW).reindex(columns=list(KOLUMNY_OPERATOROW.values()))

    wynik = ludnosc.join([inpost, konk], how="outer").fillna(0)
    for kolumna in ["inpost", "inpost_w_budowie", *KOLUMNY_OPERATOROW.values()]:
        wynik[kolumna] = wynik[kolumna].astype(int)
    wynik.index.name = "h3"
    wynik = wynik.reset_index()
    srodki = [h3.cell_to_latlng(c) for c in wynik["h3"]]
    wynik["lat"], wynik["lon"] = [s[0] for s in srodki], [s[1] for s in srodki]
    return wynik


def zapisz_agregaty(agregaty: pd.DataFrame, katalog: Path) -> Path:
    katalog.mkdir(parents=True, exist_ok=True)
    plik = katalog / "heksagony_res8.parquet"
    agregaty.to_parquet(plik, index=False)
    return plik
