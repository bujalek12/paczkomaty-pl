"""Strona Mapa: ilu mieszkancow ma paczkomat w zasiegu, gdzie powstaja nowe, gdzie stoi konkurencja.

Dane: tylko agregaty na szesciokat (data/agregaty/heksagony_res8.parquet), bez pojedynczych punktow.
"""

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from paczkomaty.widoki import SUMOWANE, do_rozdzielczosci, dodaj_udzial, w_promieniu
from wspolne import agregaty, liczba, motyw, procent

m = motyw()
dane = dodaj_udzial(agregaty())
KONKURENCJA = ["allegro_one_box", "orlen_paczka", "dpd", "dhl", "pocztex"]
MIASTA = {
    "Warszawa": (52.23, 21.01), "Kraków": (50.06, 19.94), "Łódź": (51.76, 19.46), "Wrocław": (51.11, 17.03),
    "Poznań": (52.41, 16.93), "Gdańsk": (54.37, 18.62), "Szczecin": (53.43, 14.55), "Lublin": (51.25, 22.57),
    "Katowice": (50.26, 19.02), "Białystok": (53.13, 23.16), "Rzeszów": (50.04, 22.00), "Olsztyn": (53.78, 20.48),
}


def rgb(hex_kolor: str) -> list[int]:
    return [int(hex_kolor[i : i + 2], 16) for i in (1, 3, 5)]


# --- Teza -------------------------------------------------------------------------------
suma = dane[SUMOWANE].sum()
gestosc = dane["ludnosc"] / 0.737  # os./km2, szesciokat res 8 ma ok. 0,737 km2
miasta = dane[gestosc > 2000]
wies = dane[(gestosc > 50) & (gestosc <= 500)]
st.markdown(
    f'<h1 class="teza">{procent(suma.ludnosc_500m / suma.ludnosc, 1)} mieszkańców ma paczkomat InPost '
    f"w zasięgu 500 m. W miastach {procent(miasta.ludnosc_500m.sum() / miasta.ludnosc.sum())}, "
    f"na wsi i przedmieściach {procent(wies.ludnosc_500m.sum() / wies.ludnosc.sum())}.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="porownanie">Odległość w linii prostej od miejsca zamieszkania do najbliższego działającego '
    f"paczkomatu, 500 m to ok. 5–7 minut pieszo. W zasięgu 1 km: {procent(suma.ludnosc_1km / suma.ludnosc, 1)}. "
    f"Działających paczkomatów: {liczba(suma.inpost)}, w budowie: {liczba(suma.inpost_w_budowie)}.</p>",
    unsafe_allow_html=True,
)

# --- Mapa --------------------------------------------------------------------------------
lewa, prawa = st.columns([1, 1])
with lewa:
    warstwa = st.segmented_control(
        "Co pokazać", ["Zasięg 500 m", "Paczkomaty w budowie", "Konkurencja"], default="Zasięg 500 m", key="warstwa"
    ) or "Zasięg 500 m"
with prawa:
    obszar = st.selectbox("Obszar", ["Cała Polska", *MIASTA], key="obszar", label_visibility="collapsed")

if obszar == "Cała Polska":
    # 320 tys. szesciokatow to za duzo dla przegladarki: dla calego kraju 7 razy wieksze (res 7)
    widok = do_rozdzielczosci(dane, 7)
    srodek, zoom = (52.0, 19.3), 5.4
else:
    srodek = MIASTA[obszar]
    widok = w_promieniu(dane, *srodek, km=25)
    zoom = 9.6

od, do = np.array(rgb(m["skala"][0])), np.array(rgb(m["skala"][1]))
if warstwa == "Zasięg 500 m":
    widok = widok[widok["ludnosc"] > 0].copy()
    t = widok["udzial_500"].to_numpy()[:, None]
    widok["kolor"] = [list(map(int, k)) + [200] for k in (od + (do - od) * t)]
    legenda = f"Kolor: odsetek mieszkańców sześciokąta z paczkomatem w 500 m, od 0% (ciemny) do 100% (jasny)."
elif warstwa == "Paczkomaty w budowie":
    widok = widok[(widok["inpost_w_budowie"] > 0) | (widok["inpost"] > 0)].copy()
    widok["kolor"] = [rgb(m["budowa"]) + [230] if b > 0 else rgb(m["linia"]) + [160] for b in widok["inpost_w_budowie"]]
    legenda = "Bursztynowy: sześciokąty z paczkomatem w budowie. Szary: z działającym paczkomatem."
else:
    widok = widok.assign(konkurencja=widok[KONKURENCJA].sum(axis=1))
    widok = widok[widok["konkurencja"] > 0].copy()
    widok["kolor"] = [rgb("#e8590c") + [230] if i == 0 else rgb(m["akcent"]) + [170] for i in widok["inpost"]]
    legenda = ("Pomarańczowy: automat konkurencji tam, gdzie nie ma InPost. Niebieski: konkurencja obok InPost. "
               "Dane OpenStreetMap, niepełne.")

widok = widok.assign(
    ludnosc_txt=widok["ludnosc"].round(-1).map(liczba),
    udzial_txt=(widok["udzial_500"] * 100).round().astype(int).astype(str) + "%",
)
st.pydeck_chart(
    pdk.Deck(
        layers=[pdk.Layer(
            "H3HexagonLayer", widok, get_hexagon="h3", get_fill_color="kolor", pickable=True,
            stroked=False, filled=True, extruded=False,
        )],
        initial_view_state=pdk.ViewState(latitude=srodek[0], longitude=srodek[1], zoom=zoom),
        map_provider="carto", map_style=m["mapa"],
        tooltip={"html": "Mieszkańcy: {ludnosc_txt}<br>W zasięgu 500 m: {udzial_txt}<br>"
                         "Paczkomaty InPost: {inpost}, w budowie: {inpost_w_budowie}",
                 "style": {"backgroundColor": m["panel"], "color": m["tekst"], "fontFamily": "Barlow"}},
    ),
    height=560,
)
st.markdown(f'<p class="przypis">{legenda}</p>', unsafe_allow_html=True)

st.divider()

# --- Wnioski (liczone z danych) ---------------------------------------------------------------
st.subheader("Co widać w danych")
budowa = dane[dane["inpost_w_budowie"] > 0]
z_inpost = (budowa["inpost"] > 0).mean()
konk = dane[KONKURENCJA].sum().sum()
konk_bez = dane.loc[dane["inpost"] == 0, KONKURENCJA].sum().sum()
for tytul, opis in [
    ("Białe plamy to wieś i przedmieścia",
     f"W sześciokątach o gęstości 50–500 os./km² mieszka {procent(wies.ludnosc.sum() / suma.ludnosc)} ludności, "
     f"a tylko {procent(wies.ludnosc_500m.sum() / wies.ludnosc.sum())} z nich ma paczkomat w 500 m."),
    ("InPost zagęszcza sieć",
     f"{procent(z_inpost)} sześciokątów z paczkomatami w budowie ma już działający paczkomat. Nowe punkty "
     "powstają głównie tam, gdzie sieć już jest, a nie w białych plamach."),
    ("Konkurencja walczy o te same miejsca",
     f"Tylko {procent(konk_bez / konk)} automatów innych operatorów (wg OpenStreetMap) stoi w sześciokątach "
     "bez paczkomatu InPost."),
]:
    st.markdown(f'<div class="notatka"><b>{tytul}.</b> {opis}</div>', unsafe_allow_html=True)

st.markdown(
    '<p class="przypis">Projekt niezależny, niezwiązany z InPost. Źródła: publiczna mapa punktów InPost '
    "(agregaty na sześciokąt), Kontur Population (CC BY 4.0), © współtwórcy OpenStreetMap (ODbL). "
    "Ludność wg Kontur jest zawyżona względem GUS, dlatego podajemy udziały procentowe.</p>",
    unsafe_allow_html=True,
)
