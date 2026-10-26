# Raport Power BI: Zasięg paczkomatów

Ta sama historia co aplikacja, w formie raportu: przegląd, regiony, model, historia sieci.
Budowa w Power BI Desktop zajmuje ok. 1,5 godziny.

| plik | co to |
|---|---|
| `dane/powiaty.parquet` | 380 powiatów: ludność (GUS), zasięg 500 m / 1 km, paczkomaty, udział mieszkańców miast, `dane_niepewne` |
| `dane/wojewodztwa.parquet` | 16 województw: to samo + liczba paczkomatów według pola z API (kontrola) |
| `dane/zabudowa.parquet` | mieszkańcy i zasięg wg województwa i typu zabudowy (miasto, małe miasta, wieś, rozproszona) |
| `dane/powiaty_model.parquet` | model: paczkomaty faktyczne i przewidywane w powiecie (356 powiatów, bez niepewnych) |
| `dane/stan_dzienny.parquet` | liczba paczkomatów wg dnia, województwa i statusu (od 24.10.2026, rośnie codziennie) |
| `mapa/powiaty.topojson` | granice powiatów do wizualizacji **Mapa kształtów** (klucz: `nazwa`) |
| `miary.dax` | miary i kolumny obliczeniowe z komentarzami |
| `motyw_ciemny.json`, `motyw_jasny.json` | motywy zgodne z aplikacją |

Wszystkie tabele są z jednego dnia (stan sieci z 26.10.2026), więc liczby zgadzają się między stronami.

## 0. Ustawienia (raz)

1. **Plik → Opcje i ustawienia → Opcje → Ustawienia regionalne** (sekcja *Bieżący plik*): język **polski**.
   Dzięki temu liczby mają spację tysięcy i przecinek dziesiętny (46,4%, 32 703).
2. **Opcje → Funkcje w wersji zapoznawczej → Wizualizacja mapy kształtów** (zaznacz, uruchom Power BI ponownie).

## 1. Import

1. **Zarządzaj parametrami → Nowy parametr**: nazwa `Folder`, typ *Tekst*, wartość np.
   `C:\Users\macie\Desktop\portfolio\projekty\paczkomaty\powerbi\dane\` (z ukośnikiem na końcu).
2. **Pobierz dane → Więcej → Parquet**, kolejno pięć plików z `dane/`.
3. W Power Query, w każdym zapytaniu: **Edytor zaawansowany**, zamień ścieżkę na `Folder & "powiaty.parquet"` itd.
   Po przeniesieniu raportu zmieniasz jedno miejsce zamiast pięciu.
4. Typy kolumn (Power Query → kliknij ikonę typu w nagłówku kolumny):
   - `powiaty_model[powiat_id]`: **Liczba całkowita** (w pliku jest dziesiętna, a relacja wymaga tego samego typu
     co `powiaty[powiat_id]`);
   - `stan_dzienny[data]`: **Data** (w pliku jest tekst).
5. **Zamknij i zastosuj**.

## 2. Model

```
powiaty_model (*) ──── (1) powiaty (*) ──── (1) wojewodztwa (1) ──── (*) zabudowa
      [powiat_id]           [powiat_id]           [wojewodztwo]          [wojewodztwo]
                                                       (1)
                                                        │
                                                       (*) stan_dzienny [wojewodztwo]
```

- Widok **Model**: przeciągnij kolumnę klucza z tabeli „wiele” na tabelę „jeden”. Kardynalność **wiele do jednego**,
  kierunek filtrowania **pojedynczy**.
- `wojewodztwa` to wspólny wymiar: fragmentator województwa z tej tabeli filtruje powiaty, zabudowę i historię naraz.
- W `stan_dzienny` są 3 paczkomaty w budowie bez województwa (`nieznane`). Nie pasują do relacji, więc pod filtrem
  województwa znikają, a w sumie dla kraju są. To poprawne zachowanie.
- Ukryj w widoku raportu klucze w tabelach „wiele” (`powiaty[wojewodztwo]`, `zabudowa[wojewodztwo]`,
  `stan_dzienny[wojewodztwo]`, `powiaty_model[powiat_id]`, `powiaty_model[nazwa]`), żeby filtrować zawsze przez wymiar.

## 3. Miary i kolumny

1. **Wprowadź dane** → pusta tabela `_Miary` → **Załaduj**.
2. Z `miary.dax` wklej każdą miarę przez **Nowa miara** (w tabeli `_Miary`). Formaty są w komentarzach pod miarą.
3. Kolumny obliczeniowe z końca pliku dodaj przez **Nowa kolumna** w tabeli `powiaty` (3 kolumny)
   i `zabudowa` (`kolejnosc`).
4. Sortowanie: `zabudowa[typ_zabudowy]` → **Sortuj według kolumny** → `kolejnosc`.

**Sprawdzenie** (karta z miarą, bez filtrów): `Zasięg 500 m` = 46,4%, `Zasięg 1 km` = 69,6%,
`Paczkomaty` = 32 703, `Paczkomaty w budowie` = 917, `Powiaty poniżej 20%` = 58,
`Korelacja zasięgu z urbanizacją` = 0,96. Jeśli wychodzi co innego, zwykle winna jest relacja albo typ kolumny.

## 4. Motyw

**Widok → Motywy → Przeglądaj motywy** → `motyw_ciemny.json` (raport do portfolio) albo `motyw_jasny.json`.
Kolory: niebieski = dobry zasięg, bursztynowy = braki, szary = środek. Ten sam kolor zawsze znaczy to samo
na każdej stronie. Jeśli Power BI przypisze serii inny kolor, ustaw go w **Formatowanie → Kolory**.

Format stron: **16:9**, tło z motywu. U góry każdej strony tytuł-wniosek (pole tekstowe, ok. 20 pt),
pod nim jedna linijka opisu w kolorze przygaszonym.

## 5. Strony raportu

### Strona 1: „Przegląd”

Tytuł: miara `Tytuł przeglądu` (pole tekstowe → **Wartość** → fx) albo wpisany ręcznie:
*„Paczkomat do 500 m ma 46,4% mieszkańców. W miastach 85%, na wsi i przedmieściach 15%”*.

| wizualizacja | pola |
|---|---|
| 4 karty (nowa wizualizacja *Karta*) | `Zasięg 500 m`, `Zasięg 1 km`, `Mieszkańcy ponad 1 km (mln)` (etykieta „mln mieszkańców dalej niż 1 km”), `Paczkomaty` |
| Wykres słupkowy grupowany (poziomy) | oś Y: `zabudowa[typ_zabudowy]`, wartości: `Zasięg 500 m wg zabudowy`, `Zasięg 1 km wg zabudowy`; etykiety danych włączone; kolory: 500 m niebieski, 1 km szary |
| Wykres słupkowy (poziomy, wąski) obok | oś Y: `zabudowa[typ_zabudowy]`, wartość: `Udział ludności`, kolor szary |
| Fragmentator | `wojewodztwa[wojewodztwo]` (lista rozwijana) |
| Pole tekstowe (stopka) | „500 m to ok. 5–7 minut pieszo. Odległość w linii prostej od środka sześciokąta H3 do najbliższego działającego paczkomatu.” |

Wniosek do opowiedzenia: na wsi i przedmieściach mieszka ponad jedna trzecia ludności (35,5%), a paczkomat
do 500 m ma tam co siódma osoba.

### Strona 2: „Regiony”

Tytuł: *„Zasięg zależy prawie wyłącznie od urbanizacji: najlepiej śląskie (57%), najsłabiej świętokrzyskie (31%)”*.

| wizualizacja | pola |
|---|---|
| **Mapa kształtów** (lewa połowa strony) | Lokalizacja: `powiaty[nazwa]`, Nasycenie koloru: `Zasięg 500 m`, Etykietki: `Zasięg 1 km`, `Paczkomaty`, `Paczkomaty na 10 tys.` |
| Wykres słupkowy (poziomy) | oś Y: `wojewodztwa[wojewodztwo]`, wartość: `Zasięg 500 m`, sortowanie malejąco; linia stała (Analiza → Linia stała) = 0,464 z etykietą „średnia kraju” |
| Tabela „ranking” | `powiaty[nazwa]`, `Zasięg 500 m`, `Zasięg 1 km`, `powiaty[udzial_miejski]`, `Paczkomaty`; sortowanie po `Zasięg 500 m` rosnąco |
| Wykres punktowy | X: `powiaty[udzial_miejski]` (*Nie podsumowuj*), Y: `powiaty[udzial_500m]` (*Nie podsumowuj*), Szczegóły: `powiaty[nazwa]`; Analiza → **Linia trendu** |
| Karta | `Korelacja zasięgu z urbanizacją` |
| Tabela „poniżej oczekiwań” | `powiaty[nazwa]`, `udzial_miejski`, `udzial_500m`, `Oczekiwany zasięg 500 m`, `Różnica do oczekiwanego (pp)`; filtr wizualizacji: `dane_niepewne` = Fałsz, Pierwsze N = 10 według `Różnica do oczekiwanego (pp)` (od dołu) |
| Fragmentator | `wojewodztwa[wojewodztwo]` |

**Mapa kształtów krok po kroku:**
1. Wstaw mapę kształtów, przeciągnij pola jak w tabeli.
2. **Formatowanie → Ustawienia mapy → Typ mapy: Mapa niestandardowa → Dodaj mapę** → `mapa/powiaty.topojson`.
3. **Projekcja: Merkator**. W **Wyświetl klucze mapy** sprawdź, że klucz to `nazwa`: wtedy wszystkie 380 powiatów
   mają kolor. Szary powiat = nazwa się nie dopasowała.
4. **Kolory wypełnienia → Rozbieżne**: minimum bursztynowy `#c98500` (wartość 0,2), środek szary `#4a5866`
   (0,464 = średnia kraju), maksimum niebieski `#3987e5` (0,7). Wartości ustaw ręcznie, inaczej Power BI weźmie
   skrajne powiaty i prawie cała mapa będzie szara.
5. Obramowanie kształtów w kolorze tła (`#0f1a24`), żeby powiaty były oddzielone jak w aplikacji.

Dlaczego mapa kształtów: działa bez internetu i bez usług Bing/Azure (te dopasowują powiaty po nazwie z geokodera
i mylą powiaty o tej samej nazwie, np. dwa grodziskie). Granice są w pliku, klucz to nazwa z tabeli `powiaty`.

Wniosek: ranking pokazuje głównie, gdzie są miasta (korelacja 0,96). Ciekawsza jest tabela „poniżej oczekiwań”:
Zielona Góra, Świnoujście i Tarnobrzeg mają zasięg o 17–19 pp niższy niż powiaty o podobnej urbanizacji.

### Strona 3: „Model”

Tytuł: *„Model wskazuje braki: w Świnoujściu stoją 23 paczkomaty, model przewiduje 41”*.

| wizualizacja | pola |
|---|---|
| 3 karty | `Paczkomaty faktyczne (model)`, `Paczkomaty według modelu`, `Brakuje paczkomatów` |
| Wykres słupkowy (poziomy) | oś Y: `powiaty[nazwa]`, wartość: `Brakuje %`; filtry wizualizacji: `Paczkomaty według modelu` ≥ 20 i Pierwsze N = 15 według `Brakuje %`; kolor bursztynowy |
| Wykres punktowy | X: `Paczkomaty według modelu`, Y: `Paczkomaty faktyczne (model)`, Szczegóły: `powiaty[nazwa]`; skala logarytmiczna na obu osiach (od 1); opis pod wykresem: „punkty poniżej przekątnej = mniej paczkomatów, niż przewiduje model” |
| Tabela | `powiaty[nazwa]`, `Paczkomaty faktyczne (model)`, `Paczkomaty według modelu`, `Brakuje paczkomatów`, `Brakuje %`; formatowanie warunkowe `Brakuje %`: pasek danych bursztynowy |
| Pole tekstowe | „LightGBM (Poisson) przewiduje liczbę paczkomatów w sześciokącie z mieszkańców, sklepów, przystanków, szkół i odległości od miasta. Żadna cecha nie korzysta z położenia paczkomatów InPost. Walidacja przestrzenna: 78,7% wyjaśnionego odchylenia (sama ludność: 61,3%).” |

Uwaga: w tej tabeli jest 356 powiatów (bez 24 z niepewnym rozkładem ludności), dlatego `Paczkomaty faktyczne (model)`
jest mniejsze niż `Paczkomaty` ze strony 1. Napisz to w przypisie.

### Strona 4: „Historia sieci”

Tytuł: miara `Stan na` jako podtytuł; tytuł ręcznie, gdy będzie więcej dni (np. *„Od 24 października przybyło N paczkomatów”*).

| wizualizacja | pola |
|---|---|
| Wykres liniowy | oś X: `stan_dzienny[data]` (typ **Ciągła**), wartość: `Działające`; oś Y nie od zera (min. automatyczne), bo zmiany są małe względem 32 tys. |
| Wykres kolumnowy | oś X: `stan_dzienny[data]`, wartość: `W budowie (dzień)`, kolor bursztynowy |
| 2 karty | `Działające ostatniego dnia`, `Zmiana działających od początku` |
| Tabela | `wojewodztwa[wojewodztwo]`, `Działające ostatniego dnia`, `Zmiana działających od początku`, `W budowie (dzień)` (filtr: ostatni dzień) |

Na razie są 3 dni (24–26.10.2026), więc strona jest „szkieletem”: wykres zapełni się sam po kolejnych
odświeżeniach danych. W stopce: „Codzienny zrzut publicznej mapy punktów, od 24.10.2026.”

## 6. Zasady

- **Tytuł = wniosek** z liczbą, nie etykieta („Regiony”).
- **Jedna oś Y** na wykresie; procenty i sztuki na osobnych wykresach.
- **Kolor = znaczenie**: niebieski dobry zasięg, bursztynowy braki, szary środek. Bez dodatkowych kolorów „dla ozdoby”.
- **Średnie ważone ludnością**: zasięg województwa to nie średnia z powiatów, tylko suma mieszkańców w zasięgu
  przez sumę mieszkańców (miary to robią).
- **Stopka źródeł** na każdej stronie: „Projekt niezależny, niezwiązany z InPost. Dane: publiczna mapa punktów InPost
  (agregaty), Kontur Population (CC BY 4.0) skalibrowana do GUS BDL 2025, © OpenStreetMap (ODbL), granice PRG GUGiK.”

## 7. Odświeżanie i portfolio

- Świeże dane: na Macu `uv run python -m paczkomaty.pipeline`, commit `powerbi/dane/`, push; tu `git pull`
  i w Power BI **Odśwież**.
- Zapisz raport jako `powerbi/zasieg_paczkomatow.pbix` (z danymi ok. 1 MB).
- Zrzuty ekranu stron (**Plik → Eksportuj → PDF** albo Win+Shift+S) do `docs/img/powerbi_<strona>.png`.
- `.pbix` jest binarny: zmieniaj go tylko na jednym komputerze naraz (git nie połączy dwóch wersji).
