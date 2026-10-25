"""Strona Mapa: ilu mieszkancow ma paczkomat w zasiegu, gdzie powstaja nowe, gdzie stoi konkurencja.

Dane: tylko agregaty na szesciokat (data/agregaty/heksagony_res8.parquet), bez pojedynczych punktow.
"""

import numpy as np
import pydeck as pdk
import streamlit as st

from paczkomaty.widoki import (
    OPERATORZY, SUMOWANE, TYPY_ZABUDOWY, do_rozdzielczosci, dodaj_udzial, klasa_zasiegu, konkurencja_wg_operatora,
    pokrycie_wg_typu, w_promieniu,
)
from wspolne import MIASTA, agregaty, legenda, liczba, motyw, procent, rgb, slupki

m = motyw()
dane = dodaj_udzial(agregaty())
dane["klasa"] = klasa_zasiegu(dane)
INPOST_OSM = 21_439  # paczkomaty InPost zapisane w OpenStreetMap (notebook 01), do oceny kompletnosci OSM


def krycie(ludnosc, pelne_od: float) -> list[int]:
    """Przezroczystosc wg liczby mieszkancow (skala log): pusta wies blada, gesto zaludnione miejsca wyrazne."""
    t = np.clip((np.log10(np.maximum(ludnosc, 1)) - 1) / (np.log10(pelne_od) - 1), 0, 1)  # od 10 os.
    return list((30 + 210 * t).astype(int))


# --- Teza i liczby ------------------------------------------------------------------------
suma = dane[SUMOWANE].sum()
typy = pokrycie_wg_typu(dane).set_index("typ")
konk = konkurencja_wg_operatora(dane)
w500, w1km = suma.ludnosc_500m / suma.ludnosc, suma.ludnosc_1km / suma.ludnosc
wies = typy.loc["Wieś i przedmieścia"]

st.markdown(
    f'<h1 class="teza">{procent(w500, 1)} mieszkańców ma paczkomat InPost w zasięgu 500 m. '
    f'W miastach {procent(typy.loc["Miasta", "w_500m"])}, na wsi i przedmieściach {procent(wies.w_500m)}.</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="porownanie">500 m to ok. 5–7 minut pieszo. Liczę odległość w linii prostej od miejsca zamieszkania '
    "do najbliższego działającego paczkomatu, dla całej Polski.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="kafle">'
    f"<div><b>{procent(w500, 1)}</b>mieszkańców ma paczkomat do 500 m</div>"
    f"<div><b>{procent(w1km, 1)}</b>do 1 km</div>"
    f"<div><b>{liczba(suma.inpost)}</b>działających paczkomatów InPost, {liczba(suma.inpost_w_budowie)} w budowie</div>"
    f"<div><b>{liczba(konk.automaty.sum())}</b>automatów innych firm (OpenStreetMap)</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# --- Sterowanie --------------------------------------------------------------------------
WARSTWY = ["Zasięg 500 m", "Paczkomaty w budowie", "Konkurencja"]
lewa, prawa = st.columns([1.3, 1], vertical_alignment="bottom")
with lewa:
    warstwa = st.segmented_control("Co pokazać", WARSTWY, default=WARSTWY[0], key="warstwa") or WARSTWY[0]
with prawa:
    obszar = st.selectbox("Obszar", ["Cała Polska", *MIASTA], key="obszar")

if warstwa == "Konkurencja":
    operator = st.segmented_control(
        "Operator", ["Wszyscy", *OPERATORZY.values()], default="Wszyscy", key="operator"
    ) or "Wszyscy"
    kolumny_konk = list(OPERATORZY) if operator == "Wszyscy" else [k for k, v in OPERATORZY.items() if v == operator]

if obszar == "Cała Polska":
    # 320 tys. szesciokatow to za duzo dla przegladarki: dla calego kraju 7 razy wieksze (res 7)
    widok = do_rozdzielczosci(dane, 7)
    widok["klasa"] = klasa_zasiegu(widok)
    srodek, zoom, bok, pelne = (52.0, 19.3), 5.45, "ok. 5 km² (ok. 2,5 km średnicy)", 50000
else:
    srodek, zoom, bok, pelne = MIASTA[obszar], 9.9, "ok. 0,7 km² (kilka kwartałów, ok. 1 km średnicy)", 3000
    widok = w_promieniu(dane, *srodek, km=25)

# --- Warstwa: kolor, opis, legenda, podpowiedz --------------------------------------------
if warstwa == "Zasięg 500 m":
    widok = widok[widok["ludnosc"] >= 10].copy()
    kolory = {"do 500 m": m["blisko"], "do 1 km": m["srodek"], "ponad 1 km": m["daleko"]}
    widok["kolor"] = [rgb(kolory[k], a) for k, a in zip(widok["klasa"], krycie(widok["ludnosc"], pelne))]
    opis = ("<b>Gdzie paczkomat jest blisko domu, a gdzie są białe plamy?</b> Kolor pokazuje, jak daleko "
            "do najbliższego paczkomatu InPost ma większość mieszkańców danego sześciokąta. Im więcej "
            "mieszkańców, tym kolor wyraźniejszy; blade pola to rzadko zaludnione tereny.")
    pozycje = [(m["blisko"], f"do 500 m ({procent(w500)} ludności)"),
               (m["srodek"], f"500 m – 1 km ({procent(w1km - w500)})"),
               (m["daleko"], f"ponad 1 km, biała plama ({procent(1 - w1km)})")]
    widok["podpowiedz"] = [
        f"<b>Paczkomat {k}</b> dla większości mieszkańców<br>Mieszkańcy: {liczba(round(l, -1))}<br>"
        f"W zasięgu 500 m: {procent(u)}<br>Paczkomaty InPost tutaj: {i}"
        for k, l, u, i in zip(widok["klasa"], widok["ludnosc"], widok["udzial_500"], widok["inpost"])
    ]
elif warstwa == "Paczkomaty w budowie":
    widok = widok[(widok["inpost_w_budowie"] > 0) | (widok["inpost"] > 0)].copy()
    widok["kolor"] = [rgb(m["daleko"], 240) if b > 0 else rgb(m["srodek"], 150) for b in widok["inpost_w_budowie"]]
    opis = ("<b>Gdzie InPost stawia nowe paczkomaty?</b> W danych InPost część punktów ma status „w budowie”. "
            "Bursztynowe sześciokąty to miejsca, gdzie powstaje co najmniej jeden nowy paczkomat.")
    pozycje = [(m["daleko"], f"paczkomat w budowie ({liczba(suma.inpost_w_budowie)} w kraju)"),
               (m["srodek"], "tylko działające paczkomaty")]
    widok["podpowiedz"] = [f"Paczkomaty InPost: {i} działających, {b} w budowie"
                           for i, b in zip(widok["inpost"], widok["inpost_w_budowie"])]
else:
    widok = widok.assign(wybrane=widok[kolumny_konk].sum(axis=1))
    widok = widok[widok["wybrane"] > 0].copy()
    widok["kolor"] = [rgb(m["daleko"], 240) if i == 0 else rgb(m["blisko"], 170) for i in widok["inpost"]]
    nazwa = "innych firm" if operator == "Wszyscy" else operator
    opis = (f"<b>Czy automaty {nazwa} stoją tam, gdzie brakuje InPost?</b> Pokazuję tylko sześciokąty "
            "z automatem konkurencji. Bursztynowy oznacza, że w tym miejscu nie ma żadnego paczkomatu InPost, "
            "czyli konkurencja wypełnia lukę. Niebieski: konkurencja stoi obok InPost.")
    pozycje = [(m["daleko"], "konkurencja, brak InPost"), (m["blisko"], "konkurencja obok InPost")]
    widok["podpowiedz"] = [
        "<br>".join([f"Paczkomaty InPost: {r.inpost}"]
                    + [f"{nazwa_op}: {getattr(r, k)}" for k, nazwa_op in OPERATORZY.items() if getattr(r, k) > 0])
        for r in widok.itertuples()
    ]

st.markdown(f'<p class="warstwa-opis">{opis}</p>', unsafe_allow_html=True)
legenda(pozycje)

miasto = obszar != "Cała Polska"
st.pydeck_chart(
    pdk.Deck(
        layers=[pdk.Layer(
            "H3HexagonLayer", widok[["h3", "kolor", "podpowiedz"]], get_hexagon="h3", get_fill_color="kolor",
            pickable=True, filled=True, extruded=False, stroked=miasto,
            get_line_color=rgb(m["tlo"], 255), line_width_min_pixels=1,
        )],
        initial_view_state=pdk.ViewState(latitude=srodek[0], longitude=srodek[1], zoom=zoom),
        # kolko myszy przewija strone, a nie przybliza mape (przyblizanie: przyciski albo podwojne klikniecie)
        views=[pdk.View("MapView", controller={"scrollZoom": False, "dragRotate": False})],
        map_provider="carto", map_style=m["mapa"],
        tooltip={"html": "{podpowiedz}",
                 "style": {"backgroundColor": m["panel"], "color": m["tekst"], "fontFamily": "Barlow",
                           "fontSize": "13px", "border": f"1px solid {m['linia']}"}},
    ),
    height=640,
    key=f"mapa_{obszar}",  # nowy klucz = mapa ustawia sie od nowa na wybrany obszar
)
st.markdown(
    f'<p class="przypis">Jak czytać mapę: kraj jest podzielony na jednakowe sześciokąty, jak plaster miodu '
    f"(siatka H3). Każdy ma tę samą powierzchnię, więc łatwo porównać miasto ze wsią. Jeden sześciokąt na tej mapie "
    f"to {bok}. Puste miejsca to tereny bez mieszkańców: lasy, pola, jeziora. Najedź na sześciokąt, "
    f"żeby zobaczyć szczegóły; przybliżanie przyciskami + / − albo podwójnym kliknięciem.</p>",
    unsafe_allow_html=True,
)

# --- Szczegoly wybranej warstwy -----------------------------------------------------------
if warstwa == "Zasięg 500 m":
    st.subheader("Miasto a wieś")
    st.markdown('<p class="przypis">Odsetek mieszkańców z paczkomatem do 500 m wg typu zabudowy '
                "(gęstość zaludnienia sześciokąta). Pod nazwą: jaka część ludności tam mieszka.</p>",
                unsafe_allow_html=True)
    wiersze = []
    for typ, od, do in TYPY_ZABUDOWY:
        r = typy.loc[typ]
        gestosc = f"ponad {liczba(od)}" if do == float("inf") else f"{liczba(od)}–{liczba(do)}"
        wiersze.append((typ, f"{procent(r.udzial_ludnosci)} ludności, {gestosc} os./km²",
                        r.w_500m, m["blisko"], procent(r.w_500m)))
    slupki(wiersze)
elif warstwa == "Paczkomaty w budowie":
    budowa = dane["inpost_w_budowie"]
    st.subheader("Dokąd trafiają nowe paczkomaty")
    st.markdown('<p class="przypis">Paczkomaty w budowie wg tego, jak daleko do istniejącej sieci '
                "mieli dotąd mieszkańcy tego miejsca.</p>", unsafe_allow_html=True)
    udzialy = budowa.groupby(dane["klasa"]).sum() / budowa.sum()
    opisy = {"do 500 m": ("Tam, gdzie sieć już jest", "paczkomat był do 500 m"),
             "do 1 km": ("Na obrzeżach sieci", "do paczkomatu było 0,5–1 km"),
             "ponad 1 km": ("W białych plamach", "do paczkomatu było ponad 1 km")}
    slupki([(*opisy[k], udzialy.get(k, 0.0), m["daleko"], procent(udzialy.get(k, 0.0))) for k in opisy])
else:
    st.subheader("Ile automatów mają inne firmy")
    st.markdown(
        f'<p class="przypis">Automaty paczkowe innych firm zapisane w OpenStreetMap, mapie tworzonej przez '
        f"wolontariuszy. Nie ma tam wszystkich automatów: InPost ma w OSM {liczba(INPOST_OSM)} z "
        f"{liczba(suma.inpost)} paczkomatów, więc liczby konkurencji są zaniżone (dolna granica). "
        f"Pasek: liczba automatów na tle sieci InPost.</p>",
        unsafe_allow_html=True,
    )
    wiersze = "".join(
        f"<tr><td>{r.operator}</td><td class='prawo'>{liczba(r.automaty)}</td>"
        f"<td style='width:40%'><div class='tlo-paska'><div class='pasek' style='width:{r.automaty / suma.inpost * 100:.1f}%;"
        f"background:{m['blisko']}'></div></div></td>"
        f"<td class='prawo'>{liczba(r.bez_inpost)} ({procent(r.udzial_bez_inpost)})</td></tr>"
        for r in konk.itertuples()
    )
    st.markdown(
        f"<div class='slupki-tabela'><table class='lista'><tr><th>Firma</th><th class='prawo'>Automatów</th><th></th>"
        f"<th class='prawo'>Tam, gdzie nie ma InPost</th></tr>"
        f"<tr><td>InPost (dla porównania)</td><td class='prawo'>{liczba(suma.inpost)}</td>"
        f"<td><div class='tlo-paska'><div class='pasek' style='width:100%;background:{m['srodek']}'></div></div></td>"
        f"<td class='prawo'>–</td></tr>{wiersze}</table></div>",
        unsafe_allow_html=True,
    )

st.divider()

# --- Wnioski (liczone z danych) ---------------------------------------------------------------
st.subheader("Co widać w danych")
z_inpost = (dane.loc[dane["inpost_w_budowie"] > 0, "inpost"] > 0).mean()
konk_bez = konk["bez_inpost"].sum() / konk["automaty"].sum()
for tytul, tekst in [
    ("Białe plamy to wieś i przedmieścia",
     f"Mieszka tam {procent(wies.udzial_ludnosci)} ludności, a tylko {procent(wies.w_500m)} z nich "
     "ma paczkomat w 500 m. To tu jest największe pole do rozbudowy sieci."),
    ("InPost zagęszcza sieć",
     f"{procent(z_inpost)} miejsc z paczkomatem w budowie ma już działający paczkomat. Nowe punkty "
     "powstają głównie tam, gdzie sieć już jest, prawdopodobnie by odciążyć pełne automaty."),
    ("Konkurencja walczy o te same miejsca",
     f"Tylko {procent(konk_bez)} automatów innych firm stoi w miejscach bez paczkomatu InPost. "
     "Konkurenci stawiają automaty obok InPost, a nie w białych plamach."),
]:
    st.markdown(f'<div class="notatka"><b>{tytul}.</b> {tekst}</div>', unsafe_allow_html=True)

st.markdown(
    '<p class="przypis">Projekt niezależny, niezwiązany z InPost. Źródła: publiczna mapa punktów InPost '
    "(agregaty na sześciokąt), Kontur Population (CC BY 4.0) skalibrowana do liczby mieszkańców powiatów "
    "wg GUS (2025), © współtwórcy OpenStreetMap (ODbL).</p>",
    unsafe_allow_html=True,
)
