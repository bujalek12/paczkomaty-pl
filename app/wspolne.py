"""Elementy wspolne dla stron aplikacji: motyw, naglowek, formatowanie, odczyt agregatow."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

PROJEKT = Path(__file__).resolve().parents[1]
AGREGATY = PROJEKT / "data" / "agregaty"
MIASTA = {
    "Warszawa": (52.23, 21.01), "Kraków": (50.06, 19.94), "Łódź": (51.76, 19.46), "Wrocław": (51.11, 17.03),
    "Poznań": (52.41, 16.93), "Gdańsk": (54.37, 18.62), "Szczecin": (53.43, 14.55), "Lublin": (51.25, 22.57),
    "Katowice": (50.26, 19.02), "Białystok": (53.13, 23.16), "Rzeszów": (50.04, 22.00), "Olsztyn": (53.78, 20.48),
}
KOLUMNY_MAPY = ["h3", "ludnosc", "ludnosc_500m", "ludnosc_1km", "inpost", "inpost_w_budowie", "allegro_one_box",
                "orlen_paczka", "dpd", "dhl", "pocztex", "lat", "lon"]
REPO = "https://github.com/bujalek12/paczkomaty-pl"

# Te same motywy co w projekcie energii (palety sprawdzone pod daltonizm i kontrast z tlem).
MOTYWY = {
    "ciemny": {
        "tlo": "#0f1a24", "panel": "#162433", "linia": "#24384b",
        "tekst": "#e6edf2", "przygaszony": "#8ca0b3", "akcent": "#3987e5",
        # mapa: niebieski = blisko paczkomatu, szary = posrodku, bursztynowy = daleko / nowe
        # (para sprawdzona walidatorem: daltonizm i kontrast 3:1 z tlem)
        "blisko": "#3987e5", "srodek": "#4a5866", "daleko": "#c98500",
        "mapa": "dark",
    },
    "jasny": {
        "tlo": "#f2f5f7", "panel": "#ffffff", "linia": "#d5dee5",
        "tekst": "#14212b", "przygaszony": "#5b6b78", "akcent": "#2a78d6",
        "blisko": "#2a78d6", "srodek": "#b4bec7", "daleko": "#b06a00",
        "mapa": "light",
    },
}


def liczba(x: float) -> str:
    return f"{x:,.0f}".replace(",", "\u202f")


def dziesietna(x: float, miejsca: int = 1) -> str:
    return f"{x:.{miejsca}f}".replace(".", ",")


def procent(x: float, miejsca: int = 0) -> str:
    return f"{x:.{miejsca}%}".replace(".", ",")


def rgb(hex_kolor: str, alfa: int = 220) -> list[int]:
    return [int(hex_kolor[i : i + 2], 16) for i in (1, 3, 5)] + [alfa]


def legenda(pozycje: list[tuple[str, str]]) -> None:
    kafelki = "".join(f'<span><i class="pole" style="background:{k}"></i>{opis}</span>' for k, opis in pozycje)
    st.markdown(f'<div class="legenda">{kafelki}</div>', unsafe_allow_html=True)


def slupki(wiersze: list[tuple[str, str, float, str, str]]) -> None:
    """Poziome paski: (etykieta, podpis, dlugosc 0-1, kolor, wartosc)."""
    html = "".join(
        f'<div>{etykieta}<small>{podpis}</small></div>'
        f'<div class="tlo-paska"><div class="pasek" style="width:{dl * 100:.1f}%;background:{kolor}"></div></div>'
        f'<div class="wart">{wartosc}</div>'
        for etykieta, podpis, dl, kolor, wartosc in wiersze
    )
    st.markdown(f'<div class="slupki">{html}</div>', unsafe_allow_html=True)


def motyw() -> dict:
    return MOTYWY["ciemny" if st.session_state.get("ciemny", True) else "jasny"]


def naglowek(strony: list) -> dict:
    """Pasek u gory: nazwa, linki do stron, przelacznik motywu. Wstrzykuje CSS motywu."""
    # Wybor trzymany w adresie strony, zeby przetrwal odswiezenie (?motyw=jasny)
    if "ciemny" not in st.session_state:
        st.session_state.ciemny = st.query_params.get("motyw", "ciemny") != "jasny"

    kolumny = st.columns([2.2] + [1] * len(strony) + [2, 1.6], vertical_alignment="center")
    kolumny[0].markdown('<p class="marka">Zasięg paczkomatów</p>', unsafe_allow_html=True)
    for kolumna, strona in zip(kolumny[1:], strony):
        kolumna.page_link(strona)
    ciemny = kolumny[-1].toggle("Tryb ciemny", key="ciemny")
    st.query_params["motyw"] = "ciemny" if ciemny else "jasny"

    m = motyw()
    st.markdown(
        f"""
    <style>
      :root {{
        --tlo: {m["tlo"]}; --panel: {m["panel"]}; --linia: {m["linia"]};
        --tekst: {m["tekst"]}; --przygaszony: {m["przygaszony"]};
      }}
      .stApp {{ background: var(--tlo); color: var(--tekst); }}
      [data-testid="stHeader"] {{ display: none !important; }}
      .block-container {{ padding-top: 2rem; max-width: 1120px; }}
      .stApp p, .stApp li, .stApp label, .stApp summary, .stApp td {{ color: var(--tekst); }}
      .stApp a {{ color: {m["akcent"]}; }}

      .marka {{ font-family: "Barlow Semi Condensed"; font-weight: 600; font-size: 1.05rem;
                margin: 0; letter-spacing: .01em; }}
      .teza {{ font-family: "Barlow Semi Condensed"; font-weight: 500; color: var(--tekst);
               font-size: clamp(1.9rem, 4.2vw, 3.1rem); line-height: 1.08; letter-spacing: -.01em;
               margin: 1.6rem 0 1.4rem; max-width: 28ch; text-wrap: balance; font-variant-numeric: tabular-nums; }}

      .bilans {{ display: flex; gap: 2px; height: 46px; border-radius: 4px; overflow: hidden; }}
      .bilans div {{ height: 100%; }}
      .bilans-opis {{ display: flex; gap: 2px; margin-top: .45rem; }}
      .bilans-opis div {{ min-width: 5.5rem; font-size: .88rem; color: var(--przygaszony); line-height: 1.3;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
      .bilans-opis b {{ display: block; color: var(--tekst); font-weight: 600;
                        font-variant-numeric: tabular-nums; }}
      .porownanie {{ color: var(--przygaszony) !important; font-size: .92rem; margin: 1.1rem 0 2.2rem; }}

      h2, h3 {{ font-family: "Barlow Semi Condensed" !important; font-weight: 600 !important;
                color: var(--tekst) !important; }}
      .przypis {{ color: var(--przygaszony) !important; font-size: .85rem; }}
      .notatka {{ border-left: 2px solid var(--linia); padding: .1rem 0 .1rem .9rem; margin: 0 0 1.05rem; max-width: 62ch; }}
      .notatka b {{ font-weight: 600; }}
      code {{ background: var(--panel) !important; color: var(--tekst) !important; }}

      table.lista {{ border-collapse: collapse; width: 100%; font-size: .92rem; }}
      table.lista td, table.lista th {{ border: none; border-bottom: 1px solid var(--linia);
                                       padding: .42rem .35rem; text-align: left; }}
      table.lista th {{ color: var(--przygaszony); font-weight: 500; }}
      table.lista .nr {{ color: var(--przygaszony); width: 1.6rem; }}
      table.lista .prawo {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
      table.lista td.czeka {{ color: var(--przygaszony); }}
      .przewijana {{ max-height: 360px; overflow-y: auto; }}

      /* Kontrolki Streamlit dopasowane do motywu */
      [data-testid="stButtonGroup"] button {{ background: var(--panel); color: var(--tekst);
                                              border-color: var(--linia); }}
      [data-testid="stButtonGroup"] button[kind$="Active"] {{ border-color: {m["akcent"]}; color: {m["akcent"]}; }}
      [data-testid="stSelectbox"] [role="group"] {{ background: var(--panel); border-color: var(--linia); }}
      [data-testid="stSelectbox"] input, [data-testid="stSelectbox"] svg {{ color: var(--tekst); fill: var(--tekst); }}
      [role="listbox"], [role="option"] {{ background: var(--panel) !important; color: var(--tekst) !important; }}
      [role="option"][data-focused], [role="option"]:hover {{ background: var(--linia) !important; }}
      [data-testid="stExpander"] details {{ border-color: var(--linia); background: var(--panel); }}
      [data-testid="stExpander"] summary:hover {{ color: {m["akcent"]}; }}
      [data-testid="stWidgetLabel"] p {{ color: var(--tekst); }}
      #vg-tooltip-element {{ background: var(--panel); color: var(--tekst); border: 1px solid var(--linia);
                             font-family: Barlow, sans-serif; box-shadow: none; }}
      #vg-tooltip-element td.key {{ color: var(--przygaszony); }}
      hr {{ border-color: var(--linia) !important; }}
      .legenda {{ display: flex; flex-wrap: wrap; gap: .35rem 1.3rem; font-size: .9rem; margin: .2rem 0 -.4rem; }}
      .legenda span {{ display: inline-flex; align-items: center; gap: .45rem; }}
      .legenda i.kreska {{ width: 16px; height: 2px; border-radius: 1px; }}
      .legenda i.pole {{ width: 11px; height: 11px; border-radius: 2px; opacity: .8; }}
      .kafle {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1px;
                background: var(--linia); border: 1px solid var(--linia); border-radius: 6px; overflow: hidden;
                margin: 0 0 2rem; }}
      .kafle div {{ background: var(--tlo); padding: .8rem 1rem; font-size: .86rem; color: var(--przygaszony);
                    line-height: 1.35; }}
      .kafle b {{ display: block; font-family: "Barlow Semi Condensed"; font-weight: 600; font-size: 1.7rem;
                  color: var(--tekst); font-variant-numeric: tabular-nums; line-height: 1.1; }}
      .warstwa-opis {{ max-width: 70ch; margin: .2rem 0 .7rem; }}
      .warstwa-opis b {{ font-weight: 600; }}
      .legenda {{ margin: 0 0 .7rem; }}
      .legenda i.pole {{ opacity: 1; }}
      .slupki {{ display: grid; grid-template-columns: minmax(9rem, 13rem) 1fr 3.4rem; gap: .5rem .8rem;
                 align-items: center; font-size: .9rem; max-width: 760px; margin: .4rem 0 .6rem; }}
      .slupki-tabela {{ max-width: 760px; }}
      .slupki-tabela .tlo-paska, .slupki .tlo-paska {{ height: 12px; background: var(--panel); border-radius: 0 3px 3px 0; overflow: hidden; }}
      .slupki-tabela .pasek, .slupki .pasek {{ height: 100%; border-radius: 0 3px 3px 0; }}
      .slupki .wart {{ text-align: right; font-variant-numeric: tabular-nums; }}
      .slupki small {{ display: block; color: var(--przygaszony); font-size: .8rem; }}
      [data-testid="stPageLink"] a {{ padding: .2rem .5rem; border-radius: 4px; }}
      [data-testid="stPageLink"] a span {{ color: var(--przygaszony) !important; font-weight: 500; }}
      [data-testid="stPageLink"] a[aria-current="page"] span {{ color: var(--tekst) !important; }}
      [data-testid="stPageLink"] a[aria-current="page"] {{ box-shadow: inset 0 -2px 0 {m["akcent"]}; border-radius: 0; }}
      [data-testid="stPageLink"] a:hover {{ background: var(--panel); }}
      [data-testid="stCheckbox"] label:has(input:not(:checked)) > span + div {{ background: var(--linia); }}
      [data-testid="stCheckbox"] label > span + div > div {{ background: var(--panel);
                                                            box-shadow: 0 0 0 1px var(--linia); }}
    </style>
    """,
        unsafe_allow_html=True,
    )
    return m


def komunikat(tytul: str, tresc: str) -> None:
    st.markdown(f'<h1 class="teza">{tytul}</h1><p>{tresc}</p>', unsafe_allow_html=True)
    st.stop()


def _wymagany(nazwa: str) -> Path:
    plik = AGREGATY / nazwa
    if not plik.exists():
        komunikat("Brak danych.", f"Brak pliku <code>data/agregaty/{nazwa}</code>. Uruchom "
                  "<code>uv run python -m paczkomaty.hurtownia</code>.")
    return plik


@st.cache_data(show_spinner=False)
def agregaty() -> pd.DataFrame:
    """Szesciokaty res 8 z hurtowni (ludnosc skalibrowana do GUS), bez pojedynczych punktow z API."""
    return pd.read_parquet(_wymagany("heksagony.parquet"), columns=KOLUMNY_MAPY)


@st.cache_data(show_spinner=False)
def powiaty() -> pd.DataFrame:
    return pd.read_parquet(_wymagany("powiaty.parquet"))


@st.cache_data(show_spinner=False)
def wojewodztwa() -> pd.DataFrame:
    return pd.read_parquet(_wymagany("wojewodztwa.parquet"))


@st.cache_data(show_spinner=False)
def mapa_powiatow() -> dict:
    """Uproszczone granice powiatow (tylko do rysowania), klucz properties.id = powiat_id."""
    return json.loads(_wymagany("powiaty_mapa.geojson").read_text())


@st.cache_data(show_spinner=False)
def model_heksagony() -> pd.DataFrame:
    """Predykcje modelu zapotrzebowania na szesciokat (paczkomaty.model)."""
    return pd.read_parquet(_wymagany("model_heksagony.parquet"))


@st.cache_data(show_spinner=False)
def metryki_modelu() -> dict:
    return json.loads(_wymagany("metryki_modelu.json").read_text())


@st.cache_data(show_spinner=False)
def rekomendacje() -> pd.DataFrame:
    """Kolejne miejsca z optymalizacji (paczkomaty.lokalizacje), dwa warianty: z_modelem i ludnosc."""
    return pd.read_parquet(_wymagany("rekomendacje.parquet"))


@st.cache_data(show_spinner=False)
def walidacja_lokalizacji() -> dict:
    return json.loads(_wymagany("walidacja_lokalizacji.json").read_text())
