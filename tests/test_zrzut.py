"""Test calego codziennego zrzutu na sztucznym API (bez internetu)."""

import pandas as pd
import pytest

from paczkomaty.historia import PodejrzanyZrzut
from paczkomaty.zrzut import uruchom


def punkt(nazwa, status, woj="mazowieckie"):
    return {"name": nazwa, "status": status, "location": {"latitude": 52.2, "longitude": 21.0},
            "location_type": "Outdoor", "location_247": True, "functions": ["allegro_send"],
            "address_details": {"province": woj, "city": "Warszawa"}}


def test_dwa_dni_zapisuja_zrzuty_zmiany_i_agregaty(tmp_path):
    dzien1 = [punkt("A", "Operating"), punkt("B", "Created")]
    dzien2 = [punkt("A", "Operating"), punkt("B", "Operating"), punkt("C", "Created", "pomorskie")]

    uruchom(tmp_path, "2026-10-24", pobierz=lambda: dzien1)
    podsumowanie = uruchom(tmp_path, "2026-10-25", pobierz=lambda: dzien2)

    assert (tmp_path / "zrzuty" / "inpost_2026-10-24.parquet").exists()
    assert len(pd.read_parquet(tmp_path / "zrzuty" / "inpost_2026-10-25.parquet")) == 3
    zmiany = pd.read_parquet(tmp_path / "zrzuty" / "zmiany.parquet")
    assert sorted(zip(zmiany["nazwa"], zmiany["zmiana"])) == [("B", "status"), ("C", "nowy")]
    stan = pd.read_parquet(tmp_path / "agregaty" / "stan_dzienny.parquet")
    assert sorted(stan["data"].unique()) == ["2026-10-24", "2026-10-25"]
    assert stan.loc[stan["data"] == "2026-10-25", "paczkomaty"].sum() == 3
    publiczne = pd.read_parquet(tmp_path / "agregaty" / "zmiany_dzienne.parquet")
    assert "nazwa" not in publiczne.columns and publiczne["liczba"].sum() == 2
    assert "nowe: 1" in podsumowanie and "zmiana statusu: 1" in podsumowanie


def test_ponowne_uruchomienie_dnia_nie_dubluje(tmp_path):
    dzien1 = [punkt("A", "Operating")]
    dzien2 = [punkt("A", "Operating"), punkt("B", "Created")]
    uruchom(tmp_path, "2026-10-24", pobierz=lambda: dzien1)
    uruchom(tmp_path, "2026-10-25", pobierz=lambda: dzien2)
    uruchom(tmp_path, "2026-10-25", pobierz=lambda: dzien2)

    assert len(pd.read_parquet(tmp_path / "zrzuty" / "zmiany.parquet")) == 1
    stan = pd.read_parquet(tmp_path / "agregaty" / "stan_dzienny.parquet")
    assert stan.loc[stan["data"] == "2026-10-25", "paczkomaty"].sum() == 2


def test_niepelny_zrzut_niczego_nie_zapisuje(tmp_path):
    uruchom(tmp_path, "2026-10-24", pobierz=lambda: [punkt(str(i), "Operating") for i in range(100)])

    with pytest.raises(PodejrzanyZrzut):
        uruchom(tmp_path, "2026-10-25", pobierz=lambda: [punkt(str(i), "Operating") for i in range(50)])

    assert not (tmp_path / "zrzuty" / "inpost_2026-10-25.parquet").exists()
