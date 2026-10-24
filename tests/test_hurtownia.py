"""Testy budowy hurtowni: regiony szesciokatow, zgodnosc progow dbt z Pythonem, eksport."""

import json
from pathlib import Path

import duckdb
import h3
import pandas as pd
import yaml

from paczkomaty.eksport import eksportuj
from paczkomaty.hurtownia import zbuduj_regiony
from paczkomaty.widoki import POWIERZCHNIA_RES8_KM2, TYPY_ZABUDOWY

PROJEKT = Path(__file__).resolve().parents[1]


def test_progi_gestosci_w_dbt_zgodne_z_widokami():
    zmienne = yaml.safe_load((PROJEKT / "dbt" / "dbt_project.yml").read_text())["vars"]

    assert zmienne["progi_gestosci"] == sorted(od for _, od, _ in TYPY_ZABUDOWY if od > 0)
    assert zmienne["powierzchnia_res8_km2"] == POWIERZCHNIA_RES8_KM2


def test_zbuduj_regiony(tmp_path):
    kwadrat = [[[20.9, 52.0], [21.1, 52.0], [21.1, 52.1], [20.9, 52.1], [20.9, 52.0]]]
    cecha = {"type": "Feature", "properties": {"id": 7, "nazwa": "powiat testowy"},
             "geometry": {"type": "Polygon", "coordinates": kwadrat}}
    (tmp_path / "granice").mkdir()
    for plik, nazwa in [("powiaty", "powiat testowy"), ("wojewodztwa", "mazowieckie")]:
        cecha["properties"]["nazwa"] = nazwa
        (tmp_path / "granice" / f"{plik}.geojson").write_text(json.dumps({"features": [cecha]}))
    (tmp_path / "agregaty").mkdir()
    komorka = h3.latlng_to_cell(52.05, 21.0, 8)
    pd.DataFrame({"h3": [komorka], "ludnosc": [10.0]}).to_parquet(tmp_path / "agregaty" / "heksagony_res8.parquet")

    wynik = pd.read_parquet(zbuduj_regiony(tmp_path))

    assert wynik.to_dict("records") == [
        {"h3": komorka, "powiat_id": 7, "powiat": "powiat testowy", "wojewodztwo": "mazowieckie"}]


def test_eksport_tabel_marts(tmp_path):
    baza = tmp_path / "test.duckdb"
    with duckdb.connect(str(baza)) as con:
        con.execute("create schema marts")
        con.execute("create table marts.powiaty as select 1 as powiat_id, 0.5 as udzial_500m")
        con.execute("create table marts.wojewodztwa as select 'mazowieckie' as wojewodztwo")

    pliki = eksportuj(baza, {tmp_path / "a": ["powiaty", "wojewodztwa"], tmp_path / "b": ["powiaty"]})

    assert sorted(p.relative_to(tmp_path).as_posix() for p in pliki) == [
        "a/powiaty.parquet", "a/wojewodztwa.parquet", "b/powiaty.parquet"]
    assert pd.read_parquet(tmp_path / "b" / "powiaty.parquet").to_dict("records") == [
        {"powiat_id": 1, "udzial_500m": 0.5}]
