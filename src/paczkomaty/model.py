"""Model zapotrzebowania: ile dzialajacych paczkomatow InPost "powinno" stac w szesciokacie.

Walidacja przestrzenna: foldy wg powiatow (GroupKFold), bo sasiednie szesciokaty sa do siebie podobne;
losowy podzial zawyzylby wynik (model widzialby w treningu sasiadow szesciokata z testu).
Uruchomienie: uv run python -m paczkomaty.model
"""

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_poisson_deviance
from sklearn.model_selection import GroupKFold, KFold

FOLDY = 5
PARAMETRY = dict(objective="poisson", n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=50,
                 subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=0, verbose=-1)


def podzial(grupy: np.ndarray, losowo: bool) -> list[tuple[np.ndarray, np.ndarray]]:
    """Indeksy (trening, test) dla kazdego foldu: wg grup (powiatow) albo losowo (dla porownania)."""
    indeksy = np.zeros(len(grupy))
    if losowo:
        return list(KFold(FOLDY, shuffle=True, random_state=0).split(indeksy))
    return list(GroupKFold(FOLDY).split(indeksy, groups=grupy))


def _metryki(y: np.ndarray, przewidywane: np.ndarray) -> dict:
    przewidywane = np.clip(przewidywane, 1e-6, None)
    odchylenie = mean_poisson_deviance(y, przewidywane)
    zerowe = mean_poisson_deviance(y, np.full(len(y), y.mean()))  # model "srednia dla wszystkich"
    return {"wyjasnione_odchylenie": 1 - odchylenie / zerowe, "mae": mean_absolute_error(y, przewidywane),
            "odchylenie_poissona": odchylenie}


def waliduj(X: pd.DataFrame, y: np.ndarray, grupy: np.ndarray, ludnosc: np.ndarray,
            losowo: bool = False) -> tuple[np.ndarray, dict]:
    """Predykcje out-of-fold i metryki modelu oraz punktu odniesienia (paczkomaty proporcjonalnie do ludnosci)."""
    y = np.asarray(y)
    oof, bazowe = np.zeros(len(y)), np.zeros(len(y))
    for trening, test in podzial(grupy, losowo):
        model = lgb.LGBMRegressor(**PARAMETRY).fit(X.iloc[trening], y[trening])
        oof[test] = model.predict(X.iloc[test])
        bazowe[test] = ludnosc[test] * y[trening].sum() / ludnosc[trening].sum()
    return oof, {"model": _metryki(y, oof), "sama_ludnosc": _metryki(y, bazowe)}
