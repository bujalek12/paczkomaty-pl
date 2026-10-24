"""Paczkomaty z publicznego API mapy punktow InPost.

Raw dane z API zostaja lokalnie (data/ jest w .gitignore); publicznie pokazujemy tylko agregaty.
"""

import time
from collections.abc import Callable

import httpx
import pandas as pd

from paczkomaty.http import pobierz

API = "https://api-pl-points.easypack24.net/v1/points"
NA_STRONE = 500
PRZERWA_S = 0.5  # nie obciazamy API: krotka przerwa miedzy stronami
POLSKA = {"lat": (49.0, 54.9), "lon": (14.1, 24.2)}  # prostokat obejmujacy kraj


def pobierz_paczkomaty(klient: httpx.Client | None = None, czekaj: Callable[[float], None] = time.sleep) -> list[dict]:
    """Wszystkie paczkomaty (type=parcel_locker), strona po stronie."""
    wlasny = klient is None
    klient = klient or httpx.Client(timeout=60)
    try:
        punkty, strona, stron = [], 1, 1
        while strona <= stron:
            dane = pobierz(klient, API, params={"type": "parcel_locker", "per_page": NA_STRONE, "page": strona},
                           czekaj=czekaj).json()
            punkty.extend(dane["items"])
            stron = dane["total_pages"]
            strona += 1
            if strona <= stron:
                czekaj(PRZERWA_S)
        return punkty
    finally:
        if wlasny:
            klient.close()


def do_ramki(punkty: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Surowe punkty -> ramka z potrzebnymi kolumnami i raport jakosci danych."""
    wiersze, bez_wsp, poza = [], 0, 0
    for p in punkty:
        loc = p.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is None or lon is None:
            bez_wsp += 1
            continue
        if not (POLSKA["lat"][0] <= lat <= POLSKA["lat"][1] and POLSKA["lon"][0] <= lon <= POLSKA["lon"][1]):
            poza += 1
            continue
        adres = p.get("address_details") or {}
        wiersze.append({
            "nazwa": p["name"],
            "lat": lat,
            "lon": lon,
            "status": p.get("status"),
            "wewnatrz": p.get("location_type") == "Indoor",
            "calodobowy": bool(p.get("location_247")),
            "wojewodztwo": adres.get("province"),
            "miasto": adres.get("city"),
            "allegro": any(f.startswith("allegro_") for f in p.get("functions") or []),
        })
    df = pd.DataFrame(wiersze, columns=["nazwa", "lat", "lon", "status", "wewnatrz", "calodobowy",
                                        "wojewodztwo", "miasto", "allegro"])
    duplikaty = int(df["nazwa"].duplicated().sum())
    df = df.drop_duplicates("nazwa").reset_index(drop=True)
    return df, {"bez_wspolrzednych": bez_wsp, "poza_polska": poza, "duplikaty": duplikaty}
