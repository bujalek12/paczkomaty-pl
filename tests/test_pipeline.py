"""Testy pipeline'u: kiedy odswiezac zrodla."""

import os
import time

from paczkomaty.pipeline import czy_aktualny


def test_czy_aktualny(tmp_path):
    plik = tmp_path / "osm.parquet"
    assert not czy_aktualny(plik, dni=7)  # brak pliku

    plik.write_text("x")
    assert czy_aktualny(plik, dni=7)

    osiem_dni_temu = time.time() - 8 * 86400
    os.utime(plik, (osiem_dni_temu, osiem_dni_temu))
    assert not czy_aktualny(plik, dni=7)
    assert czy_aktualny(plik, dni=None)  # zrodla bez terminu waznosci (Kontur): wystarczy, ze jest
