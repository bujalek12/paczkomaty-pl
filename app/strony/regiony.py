"""Strona Regiony: dostep do paczkomatow w wojewodztwach i powiatach (tabele marts z hurtowni dbt)."""

import copy

import pydeck as pdk
import streamlit as st

from paczkomaty.widoki import ponizej_oczekiwan
from wspolne import dziesietna, legenda, liczba, mapa_powiatow, motyw, powiaty, procent, rgb, slupki, wojewodztwa

m = motyw()
pow_ = powiaty()
woj = wojewodztwa().sort_values("udzial_500m", ascending=False)
kraj_500 = (pow_["udzial_500m"] * pow_["ludnosc"]).sum() / pow_["ludnosc"].sum()


def miejscownik(wojewodztwo: str) -> str:
    """'śląskie' -> 'śląskim' (wszystkie nazwy wojewodztw koncza sie na -kie)."""
    return wojewodztwo[:-2] + "im"


def pp(x: float) -> str:
    """Roznica w punktach procentowych, ze znakiem."""
    return f"{x * 100:+.0f} pp".replace("-", "−")


najlepsze, najgorsze = woj.iloc[0], woj.iloc[-1]
najslabszy = pow_.sort_values("udzial_500m").iloc[0]
st.markdown(
    f'<h1 class="teza">W województwie {miejscownik(najlepsze.wojewodztwo)} paczkomat do 500 m ma '
    f"{procent(najlepsze.udzial_500m)} mieszkańców, w {miejscownik(najgorsze.wojewodztwo)} "
    f"{procent(najgorsze.udzial_500m)}. Najsłabiej: {najslabszy.nazwa}, {procent(najslabszy.udzial_500m)}.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="porownanie">Te same dane co na mapie, zsumowane w 380 powiatach i 16 województwach. '
    "Liczba mieszkańców każdego powiatu pochodzi z GUS (2025).</p>",
    unsafe_allow_html=True,
)
korelacja = pow_["udzial_500m"].corr(pow_["udzial_miejski"])
st.markdown(
    f'<div class="kafle">'
    f"<div><b>{procent(kraj_500, 1)}</b>mieszkańców Polski ma paczkomat do 500 m</div>"
    f"<div><b>{dziesietna(pow_['ludnosc_ponad_1km'].sum() / 1e6)} mln</b>ma do paczkomatu ponad 1 km</div>"
    f"<div><b>{(pow_['udzial_500m'] < 0.2).sum()}</b>z 380 powiatów: mniej niż 20% w zasięgu 500 m</div>"
    f"<div><b>{dziesietna(korelacja, 2)}</b>korelacja zasięgu z udziałem mieszkańców miast w powiecie</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# --- Mapa powiatow ------------------------------------------------------------------------------
st.subheader("Powiaty")
KLASY = [  # (do, kolor, krycie, opis); niebieski = lepiej niz srednia kraju, bursztynowy = gorzej
    (0.20, m["daleko"], 235, "poniżej 20%"),
    (0.35, m["daleko"], 120, "20–35%"),
    (0.55, m["srodek"], 200, "35–55% (średnia kraju {sr})"),
    (0.70, m["blisko"], 130, "55–70%"),
    (1.01, m["blisko"], 235, "powyżej 70%"),
]


def klasa(udzial: float) -> int:
    return next(i for i, (do, *_) in enumerate(KLASY) if udzial < do)


pow_["klasa"] = pow_["udzial_500m"].map(klasa)
pow_["nazwa"] = pow_["nazwa"] + pow_["dane_niepewne"].map({True: "*", False: ""})
liczebnosc = pow_["klasa"].value_counts()
st.markdown(
    '<p class="warstwa-opis"><b>Jaka część mieszkańców powiatu ma paczkomat do 500 m?</b> Bursztynowe powiaty '
    "są wyraźnie poniżej średniej kraju, niebieskie powyżej. Najedź na powiat, żeby zobaczyć szczegóły.</p>",
    unsafe_allow_html=True,
)
legenda([(f"rgba({','.join(map(str, rgb(kolor, alfa)[:3]))},{alfa / 255:.2f})",
          f"{opis.format(sr=procent(kraj_500))} · {liczebnosc.get(i, 0)} pow.")
         for i, (_, kolor, alfa, opis) in enumerate(KLASY)])

geo = copy.deepcopy(mapa_powiatow())
po_id = pow_.set_index("powiat_id")
for cecha in geo["features"]:
    p = po_id.loc[cecha["properties"]["id"]]
    _, kolor, alfa, _ = KLASY[p.klasa]
    cecha["properties"].update(  # zwykly tekst: GeoJsonLayer wstawia wartosci do podpowiedzi bez HTML
        kolor=rgb(kolor, alfa), nazwa=p.nazwa, wojewodztwo=p.wojewodztwo, u500=procent(p.udzial_500m),
        u1km=procent(p.udzial_1km), paczkomaty=liczba(p.paczkomaty), na10=dziesietna(p.paczkomaty_na_10_tys),
        miejsce=int(p.miejsce_w_kraju),
    )
st.pydeck_chart(
    pdk.Deck(
        layers=[pdk.Layer("GeoJsonLayer", geo, get_fill_color="properties.kolor", get_line_color=rgb(m["tlo"], 255),
                          line_width_min_pixels=0.6, pickable=True, stroked=True, filled=True)],
        initial_view_state=pdk.ViewState(latitude=52.0, longitude=19.3, zoom=5.45),
        views=[pdk.View("MapView", controller={"scrollZoom": False, "dragRotate": False})],
        map_provider="carto", map_style=m["mapa"],
        tooltip={"html": "<b>{nazwa}</b> ({wojewodztwo})<br>Paczkomat do 500 m: {u500} mieszkańców<br>"
                         "Do 1 km: {u1km}<br>Paczkomaty InPost: {paczkomaty} ({na10} na 10 tys. mieszkańców)<br>"
                         "Miejsce w kraju: {miejsce} z 380",
                 "style": {"backgroundColor": m["panel"], "color": m["tekst"], "fontFamily": "Barlow",
                           "fontSize": "13px", "border": f"1px solid {m['linia']}"}},
    ),
    height=640,
    key="mapa_powiatow",
)

# --- Wojewodztwa ----------------------------------------------------------------------------------
st.subheader("Województwa")
st.markdown('<p class="przypis">Odsetek mieszkańców z paczkomatem do 500 m. Pod nazwą: liczba paczkomatów '
            "na 10 tys. mieszkańców.</p>", unsafe_allow_html=True)
slupki([(w.wojewodztwo, f"{dziesietna(w.paczkomaty_na_10_tys)} paczkomatu na 10 tys.",
         w.udzial_500m, m["blisko"] if w.udzial_500m >= kraj_500 else m["daleko"], procent(w.udzial_500m))
        for w in woj.itertuples()])


# --- Ranking powiatow ------------------------------------------------------------------------------
def tabela(df, kolumny: list[tuple[str, str, callable]]) -> None:
    naglowki = "".join(f"<th class='{'prawo' if i else ''}'>{n}</th>" for i, (n, _, _) in enumerate(kolumny))
    wiersze = "".join(
        "<tr>" + "".join(f"<td class='{'prawo' if i else ''}'>{f(getattr(r, k))}</td>"
                         for i, (_, k, f) in enumerate(kolumny)) + "</tr>"
        for r in df.itertuples()
    )
    st.markdown(f"<table class='lista'><tr>{naglowki}</tr>{wiersze}</table>", unsafe_allow_html=True)


st.subheader("Najlepszy i najsłabszy dostęp")
strona = st.segmented_control("Ranking", ["Najsłabszy dostęp", "Najlepszy dostęp"], default="Najsłabszy dostęp",
                              key="ranking", label_visibility="collapsed") or "Najsłabszy dostęp"
ranking = pow_.sort_values("udzial_500m", ascending=strona == "Najsłabszy dostęp").head(12)
tabela(ranking, [
    ("Powiat", "nazwa", str),
    ("Do 500 m", "udzial_500m", procent),
    ("Do 1 km", "udzial_1km", procent),
    ("Mieszkańcy w miastach", "udzial_miejski", procent),
    ("Paczkomaty", "paczkomaty", liczba),
    ("Dalej niż 1 km", "ludnosc_ponad_1km", lambda x: liczba(round(x, -2))),
])
st.markdown('<p class="przypis">Na dole rankingu są powiaty wiejskie, na górze miasta. Dlatego ciekawsze jest '
            "porównanie z podobnymi powiatami, niżej.</p>", unsafe_allow_html=True)

st.subheader("Poniżej oczekiwań")
# bez powiatow z niepewnym rozkladem ludnosci: ich "udzial miejski" jest zawyzony przez blad Kontur
gorsze = ponizej_oczekiwan(pow_[~pow_["dane_niepewne"]], n=10)
st.markdown(
    f'<p class="warstwa-opis">Zasięg paczkomatów w powiecie prawie w całości wynika z tego, jaka część mieszkańców '
    f"żyje w miastach (korelacja {dziesietna(korelacja, 2)}). Dla każdego powiatu liczę, jakiego zasięgu można się spodziewać przy jego urbanizacji (prosta regresja), "
    "i pokazuję te, które wypadają najgorzej. To kandydaci do rozbudowy sieci: podobne powiaty mają więcej "
    "paczkomatów blisko domu. Pomijam powiaty oznaczone gwiazdką (niepewny rozkład ludności, opis na dole).</p>",
    unsafe_allow_html=True,
)
tabela(gorsze, [
    ("Powiat", "nazwa", str),
    ("Mieszkańcy w miastach", "udzial_miejski", procent),
    ("Do 500 m", "udzial_500m", procent),
    ("Oczekiwany", "oczekiwany_500m", procent),
    ("Różnica", "roznica", pp),
])

# --- Wybrany powiat ------------------------------------------------------------------------------
st.subheader("Twój powiat")
wybrany = st.selectbox("Powiat", sorted(pow_["nazwa"]), index=None, placeholder="Wpisz nazwę powiatu",
                       label_visibility="collapsed", key="powiat")
if wybrany:
    p = pow_.set_index("nazwa").loc[wybrany]
    sredni_woj = woj.set_index("wojewodztwo").loc[p.wojewodztwo, "udzial_500m"]
    st.markdown(
        f'<div class="kafle">'
        f"<div><b>{procent(p.udzial_500m)}</b>mieszkańców ma paczkomat do 500 m "
        f"(województwo {procent(sredni_woj)}, kraj {procent(kraj_500)})</div>"
        f"<div><b>{procent(p.udzial_1km)}</b>do 1 km</div>"
        f"<div><b>{p.miejsce_w_kraju}</b>miejsce w kraju z 380</div>"
        f"<div><b>{liczba(p.paczkomaty)}</b>paczkomatów InPost, {liczba(p.paczkomaty_w_budowie)} w budowie</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    '<p class="przypis">Projekt niezależny, niezwiązany z InPost. Granice powiatów: PRG GUGiK '
    "(przez github.com/ppatrzyk/polska-geojson). Ludność: Kontur Population (CC BY 4.0) skalibrowana do GUS "
    "(Bank Danych Lokalnych, 2025). Paczkomaty: publiczna mapa punktów InPost, agregaty.</p>"
    f'<p class="przypis">* Kalibracja: w kilku miastach (np. Elbląg, Włocławek, Suwałki) Kontur umieszcza część '
    "mieszkańców poza granicą miasta, w sąsiednim powiecie ziemskim. Liczbę mieszkańców każdego powiatu biorę "
    "więc z GUS, a Kontur tylko rozkłada ją w powiecie. Suma jest poprawna, ale w "
    f"{int(pow_['dane_niepewne'].sum())} powiatach z gwiazdką (takie miasta i powiaty ziemskie wokół nich) "
    "rozkład mieszkańców w powiecie, a więc i zasięg, jest mniej pewny.</p>",
    unsafe_allow_html=True,
)
