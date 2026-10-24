"""Eksport tabel marts do plikow Parquet: dla aplikacji (data/agregaty) i dla Power BI (powerbi/dane).

Dlaczego Parquet: Power BI czyta go natywnie (Pobierz dane -> Parquet), zachowuje typy kolumn
i nie potrzebuje sterownika do DuckDB. W plikach sa tylko agregaty (szesciokaty, powiaty, wojewodztwa).
"""

from pathlib import Path

import duckdb

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
