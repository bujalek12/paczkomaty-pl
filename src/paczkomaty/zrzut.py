"""Codzienny zrzut sieci InPost: stan dnia, zmiany wzgledem poprzedniego zrzutu, agregaty.

Uruchomienie: uv run python -m paczkomaty.zrzut  (dane w data/zrzuty i data/agregaty)
"""

import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from paczkomaty.historia import (
    PodejrzanyZrzut, dopisz, porownaj, sprawdz_kompletnosc, stan_dzienny, zmiany_dzienne,
)
from paczkomaty.inpost import do_ramki, pobierz_paczkomaty


def _czytaj(sciezka: Path) -> pd.DataFrame | None:
    return pd.read_parquet(sciezka) if sciezka.exists() else None


def _poprzedni_zrzut(katalog: Path, data: str) -> Path | None:
    """Najnowszy zrzut sprzed danego dnia (nazwy plikow inpost_RRRR-MM-DD.parquet sortuja sie jak daty)."""
    starsze = sorted(p for p in katalog.glob("inpost_????-??-??.parquet") if p.stem.removeprefix("inpost_") < data)
    return starsze[-1] if starsze else None


def uruchom(katalog: Path, data: str, pobierz: Callable[[], list[dict]] = pobierz_paczkomaty) -> str:
    """Pobiera siec, zapisuje zrzut i dopisuje historie. Zwraca podsumowanie w markdown."""
    zrzuty, agregaty = katalog / "zrzuty", katalog / "agregaty"
    biezacy, jakosc = do_ramki(pobierz())
    poprzedni_plik = _poprzedni_zrzut(zrzuty, data)
    poprzedni = _czytaj(poprzedni_plik) if poprzedni_plik else None
    sprawdz_kompletnosc(None if poprzedni is None else len(poprzedni), len(biezacy))  # przed jakimkolwiek zapisem
    zmiany = porownaj(poprzedni, biezacy, data)

    zrzuty.mkdir(parents=True, exist_ok=True)
    agregaty.mkdir(parents=True, exist_ok=True)
    biezacy.to_parquet(zrzuty / f"inpost_{data}.parquet", index=False)
    (zrzuty / f"inpost_{data}_jakosc.json").write_text(json.dumps(jakosc))
    dopisz(_czytaj(zrzuty / "zmiany.parquet"), zmiany).to_parquet(zrzuty / "zmiany.parquet", index=False)
    for nazwa, nowe in [("stan_dzienny", stan_dzienny(biezacy, data)), ("zmiany_dzienne", zmiany_dzienne(zmiany))]:
        dopisz(_czytaj(agregaty / f"{nazwa}.parquet"), nowe).to_parquet(agregaty / f"{nazwa}.parquet", index=False)

    statusy = biezacy["status"].value_counts()
    rodzaje = zmiany["zmiana"].value_counts()
    porownanie = f"z {poprzedni_plik.stem.removeprefix('inpost_')}" if poprzedni_plik else "brak, to punkt startowy"
    return "\n".join([
        f"## Zrzut sieci {data}",
        f"- paczkomatów: {len(biezacy)} (działające {statusy.get('Operating', 0)}, "
        f"w budowie {statusy.get('Created', 0)})",
        f"- porównanie {porownanie}: nowe: {rodzaje.get('nowy', 0)}, usunięte: {rodzaje.get('usuniety', 0)}, "
        f"zmiana statusu: {rodzaje.get('status', 0)}",
        f"- odrzucone punkty: bez współrzędnych {jakosc['bez_wspolrzednych']}, poza Polską {jakosc['poza_polska']}, "
        f"duplikaty {jakosc['duplikaty']}",
    ])


def main() -> None:
    data = datetime.now(timezone.utc).date().isoformat()
    try:
        podsumowanie = uruchom(Path("data"), data)
    except PodejrzanyZrzut as blad:
        print(f"Zrzut pominiety: {blad}", file=sys.stderr)
        sys.exit(1)
    print(podsumowanie)
    if plik := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(plik, "a", encoding="utf-8") as f:
            f.write(podsumowanie + "\n")


if __name__ == "__main__":
    main()
