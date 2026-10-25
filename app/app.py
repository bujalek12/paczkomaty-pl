"""Aplikacja: zasieg paczkomatow w Polsce.

Uruchomienie: uv run streamlit run app/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# kod projektu (src/paczkomaty) bez instalowania pakietu: tak dziala tez Streamlit Community Cloud
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402

from paczkomaty.http import BladPobierania  # noqa: E402
from paczkomaty.zdalne import czy_odswiezyc, pobierz_z_wydania  # noqa: E402
from wspolne import AGREGATY, naglowek  # noqa: E402

st.set_page_config(page_title="Zasięg paczkomatów", layout="wide", initial_sidebar_state="collapsed")



@st.cache_resource(ttl=6 * 3600, show_spinner="Pobieram najnowsze dane…")
def synchronizuj() -> None:
    """W chmurze: najnowsze agregaty z wydania "dane" (najwyzej raz na 6 godzin, jedno pobieranie naraz)."""
    if czy_odswiezyc(AGREGATY / "heksagony.parquet", max_wiek_h=12):
        try:
            pobierz_z_wydania(AGREGATY)
            st.cache_data.clear()
        except (BladPobierania, httpx.HTTPError, OSError):
            pass  # lokalnie albo bez dostepu do wydania zostaja pliki z dysku


synchronizuj()
strony = [
    st.Page("strony/mapa.py", title="Mapa", default=True),
    st.Page("strony/regiony.py", title="Regiony", url_path="regiony"),
    st.Page("strony/model.py", title="Model", url_path="model"),
    st.Page("strony/lokalizacje.py", title="Lokalizacje", url_path="lokalizacje"),
]
nawigacja = st.navigation(strony, position="hidden")  # wlasny pasek u gory zamiast menu bocznego
naglowek(strony)
nawigacja.run()
