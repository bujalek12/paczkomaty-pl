"""Aplikacja: zasieg paczkomatow w Polsce.

Uruchomienie: uv run streamlit run app/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# kod projektu (src/paczkomaty) bez instalowania pakietu: tak dziala tez Streamlit Community Cloud
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wspolne import naglowek  # noqa: E402

st.set_page_config(page_title="Zasięg paczkomatów", layout="wide", initial_sidebar_state="collapsed")

strony = [
    st.Page("strony/mapa.py", title="Mapa", default=True),
    st.Page("strony/regiony.py", title="Regiony", url_path="regiony"),
    st.Page("strony/model.py", title="Model", url_path="model"),
]
nawigacja = st.navigation(strony, position="hidden")  # wlasny pasek u gory zamiast menu bocznego
naglowek(strony)
nawigacja.run()
