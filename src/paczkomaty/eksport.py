"""Eksport tabel marts do plikow Parquet: dla aplikacji (data/agregaty) i dla Power BI (powerbi/dane).

Dlaczego Parquet: Power BI czyta go natywnie (Pobierz dane -> Parquet), zachowuje typy kolumn
i nie potrzebuje sterownika do DuckDB. W plikach sa tylko agregaty (szesciokaty, powiaty, wojewodztwa,
wyniki modelu na powiat, liczba paczkomatow dzien po dniu).
"""

from pathlib import Path

import duckdb
import pandas as pd

from paczkomaty.widoki import niedosycenie_powiatow

PROJEKT = Path(__file__).resolve().parents[2]
BAZA = PROJEKT / "data" / "paczkomaty.duckdb"
# aplikacja potrzebuje tez szesciokatow (mapa); do Power BI wystarcza regiony
CELE = {
    PROJEKT / "data" / "agregaty": ["heksagony", "powiaty", "wojewodztwa"],
    PROJEKT / "powerbi" / "dane": ["powiaty", "wojewodztwa"],
}


def eksportuj(baza: Path = BAZA, cele: dict[Path, list[str]] = CELE) -> list[Path]:
    """Zapisuje tabele jako <katalog>/<tabela>.parquet dla kazdego katalogu. Zwraca liste plikow."""
    pliki = []
    with duckdb.connect(str(baza), read_only=True) as con:
        for katalog, tabele in cele.items():
            katalog.mkdir(parents=True, exist_ok=True)
            for tabela in tabele:
                plik = katalog / f"{tabela}.parquet"
                con.execute(f"copy (select * from marts.{tabela}) to '{plik}' (format parquet)")
                pliki.append(plik)
    return pliki


if __name__ == "__main__":
    for plik in eksportuj():
        print(f"{plik.relative_to(PROJEKT)}  {plik.stat().st_size / 1e3:.0f} kB")


def eksportuj_wyniki(agregaty: Path = PROJEKT / "data" / "agregaty",
                     katalog: Path = PROJEKT / "powerbi" / "dane") -> list[Path]:
    """Dla Power BI: model zapotrzebowania zsumowany do powiatow i historia stanu sieci."""
    katalog.mkdir(parents=True, exist_ok=True)
    model = pd.read_parquet(agregaty / "model_heksagony.parquet")
    powiaty = pd.read_parquet(agregaty / "powiaty.parquet")[["powiat_id", "nazwa"]]
    pliki = [katalog / "powiaty_model.parquet", katalog / "stan_dzienny.parquet"]
    niedosycenie_powiatow(model, powiaty, min_oczekiwane=0).to_parquet(pliki[0], index=False)
    pd.read_parquet(agregaty / "stan_dzienny.parquet").to_parquet(pliki[1], index=False)
    return pliki
