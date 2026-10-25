"""Strona Model: ile paczkomatow InPost "powinno" stac w kazdym miejscu i gdzie ich brakuje."""

import h3
import numpy as np
import pydeck as pdk
import streamlit as st

from paczkomaty.widoki import niedosycenie_powiatow, w_promieniu
from wspolne import (MIASTA, agregaty, dziesietna, legenda, liczba, metryki_modelu, model_heksagony, motyw,
                     powiaty, procent, rgb, slupki)

m = motyw()
metryki = metryki_modelu()
model = model_heksagony()
pow_ = powiaty()
ranking = niedosycenie_powiatow(model, pow_[["powiat_id", "nazwa"]])
ocena, bazowa = metryki["przestrzennie"]["model"], metryki["przestrzennie"]["sama_ludnosc"]
najgorsze = ranking.head(3)

st.markdown(
    f'<h1 class="teza">Model przewiduje, ile paczkomatów powinno stać w każdym miejscu. Największe braki: '
    f"{', '.join(najgorsze['nazwa'])}.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="porownanie">Model uczy się na całej Polsce, jak liczba działających paczkomatów InPost zależy '
    "od tego, ilu ludzi mieszka w okolicy, ile jest sklepów, przystanków i szkół i jak daleko jest do miasta. "
    "Potem dla każdego miejsca porównuje przewidywanie z rzeczywistością. Więcej niż przewiduje = sieć jest tu "
    "gęstsza niż w podobnych miejscach; mniej = brakuje paczkomatów.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="kafle">'
    f"<div><b>{procent(ocena['wyjasnione_odchylenie'])}</b>zmienności wyjaśnia model "
    f"(sama liczba mieszkańców: {procent(bazowa['wyjasnione_odchylenie'])})</div>"
    f"<div><b>{dziesietna(ocena['mae'], 3)}</b>średni błąd: paczkomatu na sześciokąt (ok. 0,7 km²)</div>"
    f"<div><b>{liczba((model['w_ocenie'] & (model['niedosycenie'] >= 1)).sum())}</b>"
    "sześciokątów, w których brakuje co najmniej jednego paczkomatu</div>"
    f"<div><b>{procent(metryki['losowo']['model']['wyjasnione_odchylenie'])}</b>"
    "wynik przy losowym podziale danych: prawie ten sam, więc model nie „podgląda” sąsiadów</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# --- Mapa brakow --------------------------------------------------------------------------------
st.subheader("Gdzie brakuje paczkomatów")
obszar = st.selectbox("Obszar", ["Cała Polska", *MIASTA], key="obszar_modelu")
dane = model[model["w_ocenie"]].merge(agregaty()[["h3", "lat", "lon"]], on="h3")
if obszar == "Cała Polska":
    # dla kraju sumujemy do sześciokątów 49 razy większych (res 6, ok. 36 km2): pojedyncze braki
    # rozrzucone po kraju są niewidoczne, a skupiska braków w większych polach już tak
    dane = (dane.assign(h3=[h3.cell_to_parent(c, 6) for c in dane["h3"]])
            .groupby("h3", as_index=False)[["inpost", "oczekiwane"]].sum())
    srodek, zoom, prog = (52.0, 19.3), 5.45, 2.0
else:
    srodek, zoom, prog = MIASTA[obszar], 9.9, 0.7
    dane = w_promieniu(dane, *srodek, km=25)
dane["brak"] = dane["oczekiwane"] - dane["inpost"]
dane = dane[dane["brak"].abs() >= prog].copy()
sila = np.clip(dane["brak"].abs() / (4 * prog), 0, 1)
dane["kolor"] = [rgb(m["daleko"] if b > 0 else m["blisko"], int(90 + 150 * s)) for b, s in zip(dane["brak"], sila)]
dane["jest"] = dane["inpost"].astype(int).astype(str)
dane["powinno"] = dane["oczekiwane"].map(lambda x: dziesietna(x))

st.markdown(
    f'<p class="warstwa-opis"><b>Bursztynowy</b>: model przewiduje tu więcej paczkomatów, niż stoi (co najmniej '
    f"{dziesietna(prog)} więcej). <b>Niebieski</b>: sieć jest gęstsza niż w podobnych miejscach. Im wyraźniejszy "
    "kolor, tym większa różnica. Pominięte są miejsca, gdzie model i rzeczywistość są zgodne.</p>",
    unsafe_allow_html=True,
)
legenda([(m["daleko"], f"brakuje · sześciokąty: {liczba((dane['brak'] > 0).sum())}"),
         (m["blisko"], f"więcej niż przewiduje model · sześciokąty: {liczba((dane['brak'] < 0).sum())}")])
st.pydeck_chart(
    pdk.Deck(
        layers=[pdk.Layer("H3HexagonLayer", dane[["h3", "kolor", "jest", "powinno"]], get_hexagon="h3",
                          get_fill_color="kolor", pickable=True, stroked=False, filled=True, extruded=False)],
        initial_view_state=pdk.ViewState(latitude=srodek[0], longitude=srodek[1], zoom=zoom),
        views=[pdk.View("MapView", controller={"scrollZoom": False, "dragRotate": False})],
        map_provider="carto", map_style=m["mapa"],
        tooltip={"html": "Paczkomaty InPost: {jest}<br>Według modelu: {powinno}",
                 "style": {"backgroundColor": m["panel"], "color": m["tekst"], "fontFamily": "Barlow",
                           "fontSize": "13px", "border": f"1px solid {m['linia']}"}},
    ),
    height=600,
    key=f"mapa_modelu_{obszar}",
)

# --- Powiaty ------------------------------------------------------------------------------------
st.subheader("Powiaty: jest a powinno być")
st.markdown('<p class="przypis">Suma przewidywań modelu w powiecie (powiaty, w których model przewiduje co '
            "najmniej 20 paczkomatów). Procent: jaka część przewidywanych paczkomatów nie stoi.</p>",
            unsafe_allow_html=True)
kolumny = st.columns(2)
for kolumna, tytul, roznica, czesc in [
    (kolumny[0], "Najwięcej brakuje", "Brakuje", ranking.head(10)),
    (kolumny[1], "Gęściej niż przewiduje model", "Nadwyżka", ranking.tail(10).iloc[::-1]),
]:
    wiersze = "".join(
        f"<tr><td>{r.nazwa}</td><td class='prawo'>{r.inpost}</td><td class='prawo'>{round(r.oczekiwane)}</td>"
        f"<td class='prawo'>{procent(abs(r.brakuje_proc))}</td></tr>"
        for r in czesc.itertuples()
    )
    kolumna.markdown(f"<p><b>{tytul}</b></p><table class='lista'><tr><th>Powiat</th><th class='prawo'>Jest</th>"
                     f"<th class='prawo'>Model</th><th class='prawo'>{roznica}</th></tr>"
                     f"{wiersze}</table>", unsafe_allow_html=True)

# --- Co jest wazne ------------------------------------------------------------------------------
st.subheader("Od czego zależy liczba paczkomatów")
NAZWY = {
    "ludnosc": "mieszkańcy sześciokąta", "ludnosc_k1": "mieszkańcy tuż obok (sąsiednie sześciokąty)",
    "ludnosc_k3": "mieszkańcy w promieniu ok. 2,5 km", "sklep": "małe sklepy", "sklep_k1": "małe sklepy obok",
    "supermarket": "supermarkety", "supermarket_k1": "supermarkety obok", "przystanek": "przystanki",
    "przystanek_k1": "przystanki obok", "szkola": "szkoły", "szkola_k1": "szkoły obok",
    "stacja_paliw": "stacje paliw", "stacja_paliw_k1": "stacje paliw obok",
    "odl_centrum_km": "odległość od zabudowy miejskiej", "konkurencja": "automaty innych firm",
    "konkurencja_k1": "automaty innych firm obok",
}
waznosc = metryki["waznosc_cech"]
najwieksza = max(waznosc.values())
st.markdown('<p class="przypis">Średni wpływ cechy na przewidywanie (SHAP). Automaty innych firm prawie nic '
            "nie wnoszą: stoją tam, gdzie i tak są ludzie i sklepy.</p>", unsafe_allow_html=True)
slupki([(NAZWY.get(k, k), "", v / najwieksza, m["blisko"], dziesietna(v, 2)) for k, v in list(waznosc.items())[:10]])

st.markdown(
    '<p class="przypis">Jak sprawdzam model: Polska jest dzielona na 5 części wg powiatów; model uczony na 4 '
    "przewiduje piątą, której nie widział (walidacja przestrzenna). Model: LightGBM z rozkładem Poissona "
    "(liczby paczkomatów to małe liczby całkowite, najczęściej 0). Cechy: mieszkańcy (GUS + Kontur), "
    "sklepy, przystanki, szkoły i stacje paliw z OpenStreetMap, odległość od miasta. Żadna cecha nie korzysta "
    "z położenia paczkomatów InPost. Model nie zna turystów, więc w kurortach (np. Świnoujście, Zakopane) część "
    "„braków” może wynikać z sezonowości. Powiaty z niepewną liczbą mieszkańców są pominięte.</p>",
    unsafe_allow_html=True,
)
