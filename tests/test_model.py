"""Testy walidacji modelu zapotrzebowania (sztuczne dane, bez internetu)."""

import numpy as np
import pandas as pd

from paczkomaty.model import podzial, waliduj


def dane_sztuczne(n=4000, ziarno=0):
    los = np.random.default_rng(ziarno)
    X = pd.DataFrame({"ludnosc": los.gamma(1.0, 800.0, n), "sklep": los.poisson(0.6, n)})
    y = los.poisson(0.0006 * X["ludnosc"] + 0.8 * X["sklep"])
    grupy = np.repeat(np.arange(40), n // 40)  # 40 "powiatow"
    return X, y, grupy


def test_foldy_przestrzenne_nie_dziela_powiatow():
    _, _, grupy = dane_sztuczne()
    for trening, test in podzial(grupy, losowo=False):
        assert not set(grupy[trening]) & set(grupy[test])


def test_model_lepszy_od_samej_ludnosci():
    X, y, grupy = dane_sztuczne()

    oof, metryki = waliduj(X, y, grupy, ludnosc=X["ludnosc"].to_numpy(), losowo=False)

    assert len(oof) == len(y) and (oof > 0).all()
    assert metryki["model"]["wyjasnione_odchylenie"] > metryki["sama_ludnosc"]["wyjasnione_odchylenie"] + 0.1
    assert set(metryki["model"]) == {"wyjasnione_odchylenie", "mae", "odchylenie_poissona"}
