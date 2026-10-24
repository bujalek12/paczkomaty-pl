# Zasięg paczkomatów w Polsce

Ilu mieszkańców ma paczkomat w zasięgu krótkiego spaceru, gdzie są białe plamy i gdzie warto postawić kolejny automat.
Projekt łączy publiczną mapę punktów InPost, siatkę ludności Kontur (sześciokąty H3) i automaty innych operatorów
z OpenStreetMap.

Projekt niezależny, niezwiązany z InPost ani innymi operatorami.

## Najważniejsze liczby (stan sieci z 24.10.2026)

| | |
|---|---|
| Mieszkańcy z paczkomatem InPost w zasięgu 500 m | **44,7%** |
| w zasięgu 1 km | 67,8% |
| mediana odległości do najbliższego paczkomatu | 577 m |
| miasta (gęstość > 2000 os./km²) w zasięgu 500 m | 83,7% |
| wieś i przedmieścia (50–500 os./km², 36% ludności) w zasięgu 500 m | 13,2% |
| działające paczkomaty / w budowie | 32 702 / 920 |

- **Białe plamy to wieś i przedmieścia**: tam mieszka ponad jedna trzecia ludności, a tylko co ósma osoba ma paczkomat w 500 m.
- **InPost zagęszcza sieć**: 70,8% sześciokątów z paczkomatami w budowie ma już działający paczkomat.
- **Konkurencja stoi obok InPost**: tylko 7,3% automatów innych operatorów z OpenStreetMap (9 739 automatów) stoi
  w sześciokątach bez paczkomatu InPost.

Odległość liczona w linii prostej od środka sześciokąta H3 (rozdzielczość 9, bok ok. 175 m) do najbliższego
działającego paczkomatu. Ludność Kontur jest zawyżona względem GUS (41,1 mln wobec 37,6 mln), dlatego podaję udziały,
a nie liczby osób.

![Zasięg 500 m](docs/img/pokrycie_500m.png)

## Co jest w repo

| | |
|---|---|
| `src/paczkomaty/` | pobieranie danych (API InPost, Kontur, Overpass) z ponawianiem, pokrycie ludności, agregaty na sześciokąt |
| `notebooks/01_eksploracja` | jakość danych, kluczowe liczby, mapy statyczne |
| `app/` | aplikacja Streamlit z interaktywną mapą (pydeck, warstwa H3) |
| `src/paczkomaty/zrzut.py`, `historia.py` | codzienny zrzut sieci i historia zmian (nowe, usunięte, zmiana statusu) |
| `.github/workflows/` | testy przy każdym pushu, codzienny zrzut sieci |
| `tests/` | testy jednostkowe (pytest) |

## Uruchomienie

```bash
uv sync
uv run jupytext --to notebook --execute notebooks/01_eksploracja.py   # pobiera dane i zapisuje agregaty
uv run streamlit run app/app.py
uv run pytest
```

Surowe dane trafiają do `data/` (poza repozytorium). Aplikacja czyta tylko zagregowany plik
`data/agregaty/heksagony_res8.parquet`: liczbę paczkomatów i ludność na sześciokąt, bez pojedynczych punktów.

## Historia sieci

Od 24.10.2026 workflow `zrzut` codziennie zapisuje stan sieci i porównuje go z poprzednim dniem. Publiczne są tylko
agregaty (wydanie `dane`): `stan_dzienny.parquet` (liczba paczkomatów wg województwa i statusu) i
`zmiany_dzienne.parquet` (liczba nowych, usuniętych i zmian statusu wg województwa). Jeśli API zwróci wyraźnie mniej
punktów niż dzień wcześniej (poniżej 95%), zrzut jest odrzucany, żeby awaria nie wyglądała jak zamknięcie paczkomatów.

## Dalej

Model zapotrzebowania (LightGBM z walidacją przestrzenną), wybór nowych lokalizacji maksymalizujący pokrycie
i porównanie rekomendacji z paczkomatami, które są właśnie w budowie.

## Źródła danych

- Publiczna mapa punktów InPost (`api-pl-points.easypack24.net`), dane prezentowane wyłącznie w agregacji.
- [Kontur Population: Poland](https://data.humdata.org/dataset/kontur-population-poland), licencja CC BY 4.0.
- © współtwórcy [OpenStreetMap](https://www.openstreetmap.org/copyright), licencja ODbL. Dane o automatach
  innych operatorów są niepełne, więc liczby konkurencji to dolna granica.
