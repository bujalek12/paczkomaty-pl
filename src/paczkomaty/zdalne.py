"""Pobieranie agregatow z wydania "dane" na GitHubie: z tego korzysta aplikacja w chmurze.

Codzienny workflow liczy pipeline i zapisuje tam gotowe agregaty. Aplikacja na Streamlit Community Cloud
nie ma wlasnego pipeline'u, wiec przy starcie (i potem co kilka godzin) sciaga gotowe pliki.
"""

import os
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from paczkomaty.http import pobierz

URL = "https://github.com/maciej-bujalski/paczkomaty-pl/releases/download/dane"
PLIKI = [
    "heksagony.parquet", "powiaty.parquet", "wojewodztwa.parquet", "powiaty_mapa.geojson",
    "model_heksagony.parquet", "metryki_modelu.json", "rekomendacje.parquet", "walidacja_lokalizacji.json",
    "stan_dzienny.parquet", "zmiany_dzienne.parquet",
]


def czy_odswiezyc(plik: Path, max_wiek_h: float) -> bool:
    """True, gdy pliku nie ma albo jest starszy niz max_wiek_h godzin."""
    return not plik.exists() or time.time() - plik.stat().st_mtime > max_wiek_h * 3600


def pobierz_z_wydania(katalog: Path, klient: httpx.Client | None = None,
                      czekaj: Callable[[float], None] = time.sleep) -> None:
    """Sciaga PLIKI do katalogu. Kazdy plik najpierw do pliku tymczasowego, potem atomowo podmienia stary."""
    katalog.mkdir(parents=True, exist_ok=True)
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=120, follow_redirects=True)
    try:
        for nazwa in PLIKI:
            tymczasowy = katalog / f"{nazwa}.pobieranie"
            tymczasowy.write_bytes(pobierz(klient, f"{URL}/{nazwa}", czekaj=czekaj).content)
            os.replace(tymczasowy, katalog / nazwa)
    finally:
        if wlasny:
            klient.close()
