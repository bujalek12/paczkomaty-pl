"""Testy wczytywania siatki ludnosci Kontur (GeoPackage = baza SQLite)."""

import sqlite3

import httpx

from paczkomaty.ludnosc import pobierz_kontur, wczytaj_kontur


def maly_gpkg(sciezka):
    with sqlite3.connect(sciezka) as con:
        con.execute("create table gpkg_contents (table_name text, data_type text)")
        con.execute("insert into gpkg_contents values ('population', 'features')")
        con.execute("create table population (fid integer, geom blob, h3 text, population real)")
        con.executemany("insert into population values (?, ?, ?, ?)",
                        [(1, b"", "881f1d4815fffff", 120.0), (2, b"", "881f1d4817fffff", 35.5)])


def test_wczytuje_h3_i_ludnosc(tmp_path):
    plik = tmp_path / "kontur.gpkg"
    maly_gpkg(plik)

    df = wczytaj_kontur(plik)

    assert df.to_dict("records") == [
        {"h3": "881f1d4815fffff", "ludnosc": 120.0},
        {"h3": "881f1d4817fffff", "ludnosc": 35.5},
    ]


def test_nie_pobiera_drugi_raz(tmp_path):
    plik = tmp_path / "kontur.gpkg"
    plik.write_bytes(b"juz jest")
    zapytania = []

    def obsluga(zadanie):
        zapytania.append(1)
        return httpx.Response(200, content=b"nowy")

    wynik = pobierz_kontur(plik, klient=httpx.Client(transport=httpx.MockTransport(obsluga)))

    assert wynik == plik
    assert zapytania == []
    assert plik.read_bytes() == b"juz jest"


def test_pobiera_i_rozpakowuje_gzip(tmp_path):
    import gzip

    plik = tmp_path / "kontur.gpkg"

    def obsluga(zadanie):
        assert zadanie.url.path.endswith(".gpkg.gz")
        return httpx.Response(200, content=gzip.compress(b"zawartosc gpkg"))

    pobierz_kontur(plik, klient=httpx.Client(transport=httpx.MockTransport(obsluga)))

    assert plik.read_bytes() == b"zawartosc gpkg"
