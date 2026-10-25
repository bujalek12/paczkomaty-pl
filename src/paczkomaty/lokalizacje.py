"""Rekomendacje nowych lokalizacji i ich sprawdzenie na paczkomatach, ktore InPost wlasnie buduje.

Cztery rankingi miejsc: (a) optymalizacja niepokrytych mieszkancow wazonych modelem zapotrzebowania,
(b) optymalizacja samej liczby niepokrytych mieszkancow, (c) najwieksze braki z modelu (przewidywane - faktyczne),
(d) losowe miejsca wsrod niepokrytych. Miara: jaki odsetek paczkomatow "w budowie" (status Created, ktory
nie wchodzil ani do modelu, ani do optymalizacji) lezy w 500 m od top-K miejsc z rankingu.
Uruchomienie: uv run python -m paczkomaty.lokalizacje
"""

import json
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from paczkomaty.optymalizacja import macierz_zasiegu, objeci_mieszkancy, trafienia, zachlannie
from paczkomaty.pokrycie import na_res9, odleglosc_do_najblizszego

PROJEKT = Path(__file__).resolve().parents[2]
AGREGATY = PROJEKT / "data" / "agregaty"
PROMIEN_M = 500
K = [500, 1000, 2000]
LOSOWAN = 20


def main() -> None:
    heksagony = pd.read_parquet(AGREGATY / "heksagony.parquet", columns=["h3", "ludnosc"]).query("ludnosc > 0")
    model = pd.read_parquet(AGREGATY / "model_heksagony.parquet", columns=["h3", "oczekiwane", "niedosycenie"])
    plik_zrzutu = sorted((PROJEKT / "data" / "zrzuty").glob("inpost_????-??-??.parquet"))[-1]
    zrzut = pd.read_parquet(plik_zrzutu)
    dzialajace, budowa = zrzut[zrzut["status"] == "Operating"], zrzut[zrzut["status"] == "Created"]

    # mieszkancy na res 9 i ich odleglosc do dzialajacego paczkomatu
    res9 = na_res9(heksagony)
    res9["rodzic"] = [h3.cell_to_parent(c, 8) for c in res9["h3"]]
    odl = odleglosc_do_najblizszego(res9["lat"].to_numpy(), res9["lon"].to_numpy(),
                                    dzialajace["lat"].to_numpy(), dzialajace["lon"].to_numpy())
    niepokryte = res9[(odl > PROMIEN_M) & (res9["ludnosc"] > 0)].reset_index(drop=True)
    # waga z modelu: przewidywane paczkomaty na mieszkanca w szesciokacie res 8, przeniesione na res 9
    intensywnosc = (model.set_index("h3")["oczekiwane"] / heksagony.set_index("h3")["ludnosc"]).fillna(0)
    niepokryte["waga_model"] = niepokryte["ludnosc"] * niepokryte["rodzic"].map(intensywnosc).fillna(0).to_numpy()

    A = macierz_zasiegu(niepokryte["lat"].to_numpy(), niepokryte["lon"].to_numpy(), PROMIEN_M)
    kmax = max(K)
    a, zysk_a = zachlannie(A, niepokryte["waga_model"].to_numpy(), kmax)
    b, zysk_b = zachlannie(A, niepokryte["ludnosc"].to_numpy(), kmax)
    braki = model.sort_values("niedosycenie", ascending=False).head(kmax)
    c_lat, c_lon = zip(*(h3.cell_to_latlng(x) for x in braki["h3"]))
    rankingi = {
        "a_optymalizacja_z_modelem": (niepokryte["lat"].to_numpy()[a], niepokryte["lon"].to_numpy()[a]),
        "b_optymalizacja_ludnosc": (niepokryte["lat"].to_numpy()[b], niepokryte["lon"].to_numpy()[b]),
        "c_braki_z_modelu": (np.array(c_lat), np.array(c_lon)),
    }

    los = np.random.default_rng(0)
    wyniki = {}
    for nazwa, (lat, lon) in rankingi.items():
        wyniki[nazwa] = {str(k): {
            "trafienia_w_budowie": trafienia(budowa["lat"], budowa["lon"], lat[:k], lon[:k], PROMIEN_M),
            "nowi_mieszkancy_500m": objeci_mieszkancy(niepokryte["lat"], niepokryte["lon"], niepokryte["ludnosc"],
                                                     lat[:k], lon[:k], PROMIEN_M),
        } for k in K}
    wyniki["d_losowo"] = {}
    for k in K:
        proby = [los.choice(len(niepokryte), k, replace=False) for _ in range(LOSOWAN)]
        wyniki["d_losowo"][str(k)] = {
            "trafienia_w_budowie": float(np.mean([trafienia(budowa["lat"], budowa["lon"], niepokryte["lat"].to_numpy()[p],
                                                            niepokryte["lon"].to_numpy()[p], PROMIEN_M) for p in proby])),
            "nowi_mieszkancy_500m": float(np.mean([niepokryte["ludnosc"].to_numpy()[np.unique(A[p].indices)].sum()
                                                   for p in proby])),
        }

    odl_budowa = odleglosc_do_najblizszego(budowa["lat"].to_numpy(), budowa["lon"].to_numpy(),
                                           dzialajace["lat"].to_numpy(), dzialajace["lon"].to_numpy())
    kontekst = {
        "zrzut": plik_zrzutu.stem.removeprefix("inpost_"), "w_budowie": len(budowa), "dzialajace": len(dzialajace),
        "w_budowie_poza_zasiegiem_500m": float((odl_budowa > PROMIEN_M).mean()),  # gorna granica trafien (a), (b), (d)
        "niepokryci_mieszkancy": float(niepokryte["ludnosc"].sum()), "kandydatow": len(niepokryte),
    }
    # kolejne miejsca obu optymalizacji; zysk = waga nowo objetych punktow (przewidywane paczkomaty albo mieszkancy)
    wybrane = pd.concat([
        niepokryte.iloc[idx][["h3", "rodzic", "lat", "lon"]].assign(ranking=nazwa, kolejnosc=np.arange(1, len(idx) + 1),
                                                                   zysk=zysk)
        for nazwa, idx, zysk in [("z_modelem", a, zysk_a), ("ludnosc", b, zysk_b)]
    ], ignore_index=True)
    wybrane.to_parquet(AGREGATY / "rekomendacje.parquet", index=False)
    wynik = {"kontekst": kontekst, "rankingi": wyniki}
    (AGREGATY / "walidacja_lokalizacji.json").write_text(json.dumps(wynik, indent=2, ensure_ascii=False))
    print(json.dumps(wynik, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
