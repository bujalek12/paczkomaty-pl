"""Strona Lokalizacje: gdzie postawic kolejne paczkomaty i czy InPost buduje w tych samych miejscach."""

import pydeck as pdk
import streamlit as st

from wspolne import dziesietna, legenda, liczba, motyw, procent, rekomendacje, rgb, walidacja_lokalizacji

m = motyw()
w = walidacja_lokalizacji()
kontekst, rankingi = w["kontekst"], w["rankingi"]
b500 = rankingi["b_optymalizacja_ludnosc"]["500"]["nowi_mieszkancy_500m"]
c2000 = rankingi["c_braki_z_modelu"]["2000"]["trafienia_w_budowie"]
d2000 = rankingi["d_losowo"]["2000"]["trafienia_w_budowie"]


def mln(x: float) -> str:
    return f"{dziesietna(x / 1e6, 2)} mln"


st.markdown(
    f'<h1 class="teza">500 dobrze wybranych paczkomatów dałoby paczkomat w 500 m kolejnym {mln(b500)} '
    f"mieszkańców. Ale InPost buduje głównie tam, gdzie sieć już jest.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="porownanie">Wybieram miejsca po kolei: zawsze to, które obejmie najwięcej mieszkańców jeszcze '
    "bez paczkomatu w 500 m (algorytm zachłanny). Potem sprawdzam, czy te miejsca pokrywają się z "
    f"{liczba(kontekst['w_budowie'])} paczkomatami, które InPost właśnie buduje "
    f"(stan z {'.'.join(reversed(kontekst['zrzut'].split('-')))}). "
    "Paczkomaty w budowie nie były używane ani w modelu, ani w optymalizacji.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="kafle">'
    f"<div><b>{mln(kontekst['niepokryci_mieszkancy'])}</b>mieszkańców nie ma paczkomatu w 500 m</div>"
    f"<div><b>{mln(b500)}</b>zyskałoby go dzięki 500 nowym paczkomatom</div>"
    f"<div><b>{procent(kontekst['w_budowie_poza_zasiegiem_500m'])}</b>paczkomatów w budowie stoi tam, "
    "gdzie dziś nie ma paczkomatu w 500 m</div>"
    f"<div><b>{dziesietna(c2000 / d2000, 0)}×</b>częściej niż losowo budowy trafiają w miejsca, "
    "gdzie model widzi braki</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# --- Mapa rekomendacji ----------------------------------------------------------------------------
st.subheader("Proponowane miejsca")
WARIANTY = {"Najwięcej mieszkańców": "ludnosc", "Mieszkańcy ważeni modelem": "z_modelem"}
wariant = st.segmented_control("Wariant", list(WARIANTY), default="Najwięcej mieszkańców", key="wariant",
                               label_visibility="collapsed") or "Najwięcej mieszkańców"
ile = st.select_slider("Ile nowych paczkomatów", options=[100, 250, 500, 1000, 2000], value=500, key="ile")
punkty = rekomendacje().query("ranking == @WARIANTY[@wariant] and kolejnosc <= @ile").copy()
punkty["kolor"] = [rgb(m["daleko"], 230) if k <= 100 else rgb(m["daleko"], 140) for k in punkty["kolejnosc"]]
punkty["opis"] = [f"Miejsce {k} w kolejności" for k in punkty["kolejnosc"]]
st.markdown(
    '<p class="warstwa-opis"><b>Najwięcej mieszkańców</b>: liczy się tylko, ilu ludzi zyska paczkomat w 500 m. '
    "<b>Ważeni modelem</b>: mieszkańcy z okolic, gdzie model przewiduje większe zapotrzebowanie (więcej sklepów, "
    "przystanków, bliżej miasta), liczą się bardziej.</p>",
    unsafe_allow_html=True,
)
legenda([(m["daleko"], "pierwsze 100 miejsc"), (f"rgba({','.join(map(str, rgb(m['daleko'])[:3]))},0.55)",
          "kolejne")])
st.pydeck_chart(
    pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", punkty[["lat", "lon", "kolor", "opis"]], get_position=["lon", "lat"],
                          get_fill_color="kolor", get_radius=500, radius_min_pixels=3, pickable=True,
                          stroked=True, get_line_color=rgb(m["tlo"], 255), line_width_min_pixels=0.5)],
        initial_view_state=pdk.ViewState(latitude=52.0, longitude=19.3, zoom=5.45),
        views=[pdk.View("MapView", controller={"scrollZoom": False, "dragRotate": False})],
        map_provider="carto", map_style=m["mapa"],
        tooltip={"html": "{opis}", "style": {"backgroundColor": m["panel"], "color": m["tekst"],
                                             "fontFamily": "Barlow", "fontSize": "13px"}},
    ),
    height=600,
    key="mapa_lokalizacji",
)
st.markdown('<p class="przypis">Kółko ma promień 500 m: tyle obejmuje nowy paczkomat. Przybliż mapę przyciskiem +, '
            "żeby zobaczyć miejsca w swojej okolicy.</p>", unsafe_allow_html=True)

# --- Porownanie z decyzjami InPostu ---------------------------------------------------------------
st.subheader("Czy InPost buduje tam, gdzie wskazują dane?")
OPISY = {
    "a_optymalizacja_z_modelem": "Optymalizacja: mieszkańcy ważeni modelem",
    "b_optymalizacja_ludnosc": "Optymalizacja: najwięcej mieszkańców",
    "c_braki_z_modelu": "Największe braki według modelu",
    "d_losowo": "Losowe miejsca (punkt odniesienia)",
}
wiersze = "".join(
    f"<tr><td>{OPISY[n]}</td>" + "".join(f"<td class='prawo'>{procent(r[k]['trafienia_w_budowie'], 1)}</td>"
                                         for k in ("500", "1000", "2000"))
    + f"<td class='prawo'>{mln(r['2000']['nowi_mieszkancy_500m'])}</td></tr>"
    for n, r in rankingi.items()
)
st.markdown(
    "<table class='lista'><tr><th>Ranking miejsc</th><th class='prawo'>top 500</th><th class='prawo'>top 1000</th>"
    "<th class='prawo'>top 2000</th><th class='prawo'>nowi mieszkańcy (top 2000)</th></tr>" + wiersze + "</table>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="przypis">Procent: jaka część paczkomatów w budowie stoi w 500 m od któregoś z proponowanych miejsc. '
    f"Tylko {procent(kontekst['w_budowie_poza_zasiegiem_500m'])} budów jest poza zasięgiem obecnej sieci, więc "
    "rankingi szukające niepokrytych mieszkańców z założenia trafiają rzadko.</p>",
    unsafe_allow_html=True,
)
for tytul, tekst in [
    ("InPost zagęszcza, a nie rozszerza sieć",
     f"{procent(1 - kontekst['w_budowie_poza_zasiegiem_500m'])} budowanych paczkomatów powstaje tam, gdzie paczkomat "
     "w 500 m już jest. Najlepiej trafia więc ranking „największe braki według modelu”, który wskazuje miejsca "
     f"z mniejszą liczbą paczkomatów niż w podobnych okolicach: {procent(c2000, 1)} budów przy 2000 miejscach, "
     f"{dziesietna(c2000 / d2000, 0)} razy więcej niż losowo. Możliwe wyjaśnienie (niesprawdzone): obciążenie "
     "istniejących automatów w gęstych miejscach jest ważniejsze niż zasięg."),
    ("Zasięg i zapotrzebowanie to różne cele",
     "Optymalizacja samej liczby mieszkańców obejmuje prawie dwa razy więcej nowych osób, a ważenie modelem "
     "częściej trafia w miejsca, które wybiera InPost. Który wariant lepszy, zależy od celu biznesowego: "
     "nowi klienci na wsi czy obsługa większej liczby przesyłek tam, gdzie popyt jest już wysoki."),
]:
    st.markdown(f'<div class="notatka"><b>{tytul}.</b> {tekst}</div>', unsafe_allow_html=True)
